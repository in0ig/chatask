"""
SQL安全校验服务

设计原则：
- ChatBI 场景下，SQL 由 AI 生成，不是用户直接输入，注入风险极低
- 核心目标：确保只执行 SELECT 查询，禁止任何写操作和 DDL
- 数据库方言无关：不依赖特定数据库的关键词（如 SQL Server 的 XP_、SP_）
- 宽松原则：合法的 SELECT 语法（UNION、CTE、子查询、注释）不应被拦截
"""

import re
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import sqlparse
from sqlparse import parse
from sqlparse.tokens import Keyword, DDL, DML

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全级别"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class SQLOperation(Enum):
    """SQL操作类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    TRUNCATE = "TRUNCATE"
    WITH = "WITH"       # CTE 以 WITH 开头，实际是 SELECT
    UNKNOWN = "UNKNOWN"


@dataclass
class SecurityViolation:
    """安全违规记录"""
    level: SecurityLevel
    type: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class TableReference:
    """表引用信息（仅用于日志分析）"""
    table_name: str
    alias: Optional[str] = None
    schema: Optional[str] = None


@dataclass
class FieldReference:
    """字段引用信息（仅用于日志分析）"""
    field_name: str
    table_name: Optional[str] = None
    table_alias: Optional[str] = None


@dataclass
class QueryComplexity:
    """查询复杂度（仅供参考，不用于拦截）"""
    table_count: int
    join_count: int
    subquery_count: int
    function_count: int
    condition_count: int
    complexity_score: float
    estimated_cost: str


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    security_level: SecurityLevel
    operation: SQLOperation
    violations: List[SecurityViolation]
    table_references: List[TableReference]
    field_references: List[FieldReference]
    complexity: QueryComplexity
    sanitized_sql: Optional[str] = None


# 写操作关键词（数据库方言无关的通用 SQL 标准）
# 只包含 SQL 标准中的 DML/DDL 写操作，不包含数据库专属函数
_WRITE_OPERATIONS = frozenset([
    'INSERT', 'UPDATE', 'DELETE', 'REPLACE',   # DML 写操作
    'CREATE', 'DROP', 'ALTER', 'TRUNCATE',      # DDL 操作
    'RENAME', 'COMMENT',                         # DDL 其他
    'MERGE', 'UPSERT',                           # 合并操作
    'GRANT', 'REVOKE',                           # DCL 权限操作
    'COMMIT', 'ROLLBACK', 'SAVEPOINT',           # TCL 事务操作（只读场景不需要）
    'CALL', 'EXEC', 'EXECUTE',                   # 存储过程调用
    'LOAD', 'IMPORT', 'EXPORT',                  # 数据导入导出
])

# 真正危险的注入模式（仅针对明确的攻击特征，不误杀合法 SQL）
# 注意：UNION SELECT、子查询、注释在合法 BI 查询中都可能出现，不应拦截
_INJECTION_PATTERNS = [
    # 堆叠注入：分号后跟写操作（如 '; DROP TABLE users'）
    (r';\s*(' + '|'.join(_WRITE_OPERATIONS) + r')\b', "堆叠注入：分号后跟写操作"),
    # 经典布尔注入：OR/AND 后跟恒真表达式（如 OR 1=1, OR 'a'='a'）
    # 注意：只匹配字面量相等，不匹配字段比较
    (r"\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\1['\"]?\b", "布尔注入：恒真条件"),
    (r"\b(OR|AND)\s+\d+\s*=\s*\d+\b", "布尔注入：数字恒真条件"),
]


class SQLSecurityValidator:
    """
    SQL 安全校验器

    核心设计：
    1. 白名单操作类型：只允许 SELECT（含 CTE WITH...SELECT）
    2. 黑名单写操作：拦截所有 DML/DDL 写操作
    3. 最小化注入检测：只检测明确的攻击特征，不误杀合法 SQL
    4. 数据库方言无关：不依赖 MySQL/SQL Server 专属语法
    """

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: 保留参数，当前版本不影响行为（未来可用于启用更严格的检查）
        """
        self.strict_mode = strict_mode

    def validate_sql(self, sql_query: str, available_tables: Dict[str, List[str]] = None) -> ValidationResult:
        """
        验证 SQL 查询安全性

        Args:
            sql_query: 待验证的 SQL 语句
            available_tables: 保留参数，不用于验证（由数据库执行时处理字段/表不存在的错误）

        Returns:
            ValidationResult
        """
        if not sql_query or not sql_query.strip():
            return self._make_blocked_result("SQL语句为空")

        try:
            # 清理 SQL（去除首尾空白，标准化换行）
            cleaned = sql_query.strip()

            # 检测操作类型
            operation = self._detect_operation(cleaned)

            violations: List[SecurityViolation] = []

            # 1. 操作类型检查（核心：只允许 SELECT / WITH...SELECT）
            violations.extend(self._check_operation(operation, cleaned))

            # 2. 注入特征检查（仅检测明确攻击模式）
            if not violations:  # 已经是写操作就不用再检查注入了
                violations.extend(self._check_injection(cleaned))

            # 解析引用信息（仅用于日志，不影响验证结果）
            table_refs = self._extract_table_references(cleaned)
            field_refs: List[FieldReference] = []

            # 复杂度分析（仅供参考，不拦截）
            complexity = self._analyze_complexity(cleaned)

            security_level = self._determine_level(violations)
            sanitized = self._sanitize(cleaned) if security_level in (SecurityLevel.SAFE, SecurityLevel.WARNING) else None

            return ValidationResult(
                is_valid=security_level != SecurityLevel.BLOCKED,
                security_level=security_level,
                operation=operation,
                violations=violations,
                table_references=table_refs,
                field_references=field_refs,
                complexity=complexity,
                sanitized_sql=sanitized,
            )

        except Exception as e:
            logger.error(f"SQL验证异常: {e}", exc_info=True)
            return self._make_blocked_result(f"SQL解析异常: {str(e)}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _detect_operation(self, sql_query: str) -> SQLOperation:
        """
        检测 SQL 操作类型

        策略：取第一个有意义的关键词（跳过注释和空白）
        CTE 以 WITH 开头，后续必须跟 SELECT，归类为 WITH
        """
        # 去掉注释后取第一个词
        no_comment = re.sub(r'/\*.*?\*/', ' ', sql_query, flags=re.DOTALL)
        no_comment = re.sub(r'--[^\n]*', ' ', no_comment)
        no_comment = re.sub(r'#[^\n]*', ' ', no_comment)  # MySQL 风格注释

        first_word = no_comment.strip().split()[0].upper() if no_comment.strip() else ''

        mapping = {op.value: op for op in SQLOperation}
        return mapping.get(first_word, SQLOperation.UNKNOWN)

    def _check_operation(self, operation: SQLOperation, sql_query: str) -> List[SecurityViolation]:
        """
        检查操作类型是否被允许

        允许：SELECT、WITH（CTE）
        拦截：所有写操作和 DDL
        """
        violations = []

        # 允许的操作
        allowed = {SQLOperation.SELECT, SQLOperation.WITH}

        if operation in allowed:
            # 对 WITH 开头的 CTE，额外验证最终是 SELECT 而非写操作
            if operation == SQLOperation.WITH:
                # CTE 后面必须是 SELECT，不能是 INSERT/UPDATE 等
                # 简单检查：去掉 WITH...AS(...) 块后第一个关键词
                cte_body = re.sub(r'\bWITH\b.*?\)\s*', '', sql_query, count=1, flags=re.DOTALL | re.IGNORECASE)
                cte_first = cte_body.strip().split()[0].upper() if cte_body.strip() else ''
                if cte_first in _WRITE_OPERATIONS:
                    violations.append(SecurityViolation(
                        level=SecurityLevel.BLOCKED,
                        type="WRITE_OPERATION_IN_CTE",
                        message=f"CTE 后跟写操作 {cte_first}，仅允许 SELECT",
                        suggestion="请确保 WITH...AS 后跟 SELECT 查询"
                    ))
            return violations

        if operation == SQLOperation.UNKNOWN:
            # 未知操作：扫描全文是否包含写操作关键词
            sql_upper = sql_query.upper()
            found_writes = []
            for kw in _WRITE_OPERATIONS:
                if re.search(r'\b' + re.escape(kw) + r'\b', sql_upper):
                    found_writes.append(kw)
            if found_writes:
                violations.append(SecurityViolation(
                    level=SecurityLevel.BLOCKED,
                    type="WRITE_OPERATION",
                    message=f"检测到写操作关键词: {', '.join(found_writes)}，仅允许 SELECT 查询",
                    suggestion="请重新生成仅包含 SELECT 的查询语句"
                ))
            else:
                # 未知操作但没有写关键词，放行（可能是数据库特殊语法）
                logger.warning(f"⚠️ 未识别的 SQL 操作类型，放行: {sql_query[:100]}")
            return violations

        # 明确的写操作
        violations.append(SecurityViolation(
            level=SecurityLevel.BLOCKED,
            type="WRITE_OPERATION",
            message=f"禁止执行 {operation.value} 操作，仅允许 SELECT 查询",
            suggestion="请重新生成仅包含 SELECT 的查询语句"
        ))
        logger.warning(f"🚫 SQL安全验证：拦截写操作 {operation.value}")
        return violations

    def _check_injection(self, sql_query: str) -> List[SecurityViolation]:
        """
        检测注入攻击特征

        只检测明确的攻击模式，不误杀合法 SQL：
        - 堆叠注入（分号后跟写操作）
        - 布尔注入（恒真条件）
        注意：UNION SELECT、子查询、-- 注释在合法 BI 查询中都可能出现，不拦截
        """
        violations = []
        for pattern, desc in _INJECTION_PATTERNS:
            match = re.search(pattern, sql_query, re.IGNORECASE)
            if match:
                violations.append(SecurityViolation(
                    level=SecurityLevel.BLOCKED,
                    type="SQL_INJECTION",
                    message=f"检测到注入特征（{desc}）: {match.group()[:80]}",
                    location=f"位置 {match.start()}-{match.end()}",
                    suggestion="SQL 包含可疑的注入模式"
                ))
        return violations

    def _extract_table_references(self, sql_query: str) -> List[TableReference]:
        """提取表引用（仅用于日志分析）"""
        tables = []
        sql_upper = sql_query.upper()

        from_matches = re.findall(r'\bFROM\s+([`"\[]?[\w.]+[`"\]]?)', sql_upper)
        join_matches = re.findall(r'\bJOIN\s+([`"\[]?[\w.]+[`"\]]?)', sql_upper)

        for name in from_matches + join_matches:
            # 去掉反引号、方括号、双引号
            clean = re.sub(r'[`"\[\]]', '', name).lower()
            if clean and clean not in ('select', 'with', 'where'):
                tables.append(TableReference(table_name=clean))

        return tables

    def _analyze_complexity(self, sql_query: str) -> QueryComplexity:
        """分析查询复杂度（仅供参考，不用于拦截）"""
        upper = sql_query.upper()

        join_count = len(re.findall(r'\bJOIN\b', upper))
        subquery_count = len(re.findall(r'\(\s*SELECT\b', upper))
        function_count = len(re.findall(r'\b(COUNT|SUM|AVG|MAX|MIN|GROUP_CONCAT|STRING_AGG|COALESCE|IFNULL|NVL)\s*\(', upper))
        table_count = len(re.findall(r'\bFROM\b', upper)) + join_count

        # 排除 BETWEEN...AND 后再统计条件数
        no_between = re.sub(r'\bBETWEEN\b.+?\bAND\b', 'BETWEEN_EXPR', upper)
        condition_count = (
            len(re.findall(r'\bWHERE\b', no_between)) +
            len(re.findall(r'\bAND\b', no_between)) +
            len(re.findall(r'\bOR\b', no_between))
        )

        score = table_count * 5 + join_count * 10 + subquery_count * 15 + function_count * 3 + condition_count * 2

        if score < 20:
            cost = "LOW"
        elif score < 50:
            cost = "MEDIUM"
        elif score < 100:
            cost = "HIGH"
        else:
            cost = "VERY_HIGH"

        return QueryComplexity(
            table_count=table_count,
            join_count=join_count,
            subquery_count=subquery_count,
            function_count=function_count,
            condition_count=condition_count,
            complexity_score=score,
            estimated_cost=cost,
        )

    def _determine_level(self, violations: List[SecurityViolation]) -> SecurityLevel:
        """根据违规列表确定安全级别"""
        if any(v.level == SecurityLevel.BLOCKED for v in violations):
            return SecurityLevel.BLOCKED
        if any(v.level == SecurityLevel.DANGEROUS for v in violations):
            return SecurityLevel.DANGEROUS
        if any(v.level == SecurityLevel.WARNING for v in violations):
            return SecurityLevel.WARNING
        return SecurityLevel.SAFE

    def _sanitize(self, sql_query: str) -> str:
        """标准化 SQL（去除多余空白）"""
        result = re.sub(r'\s+', ' ', sql_query).strip()
        return result

    def _make_blocked_result(self, message: str) -> ValidationResult:
        """快速构造一个 BLOCKED 结果"""
        return ValidationResult(
            is_valid=False,
            security_level=SecurityLevel.BLOCKED,
            operation=SQLOperation.UNKNOWN,
            violations=[SecurityViolation(
                level=SecurityLevel.BLOCKED,
                type="VALIDATION_ERROR",
                message=message,
            )],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(0, 0, 0, 0, 0, 0.0, "UNKNOWN"),
        )


class SQLSecurityService:
    """SQL 安全服务（对外接口）"""

    def __init__(self, strict_mode: bool = False):
        self.validator = SQLSecurityValidator(strict_mode=strict_mode)
        # 简单内存缓存，避免同一 SQL 重复验证
        self._cache: Dict[str, ValidationResult] = {}

    async def validate_and_secure_sql(self, sql_query: str, data_source_id: int = None) -> ValidationResult:
        """
        验证并保护 SQL 查询

        Args:
            sql_query: SQL 语句
            data_source_id: 数据源 ID（保留参数，当前不用于验证）

        Returns:
            ValidationResult
        """
        try:
            cache_key = f"{hash(sql_query)}_{data_source_id}"
            if cache_key in self._cache:
                logger.debug("使用缓存的SQL验证结果")
                return self._cache[cache_key]

            result = self.validator.validate_sql(sql_query)

            self._cache[cache_key] = result
            logger.info(
                f"SQL验证完成: level={result.security_level.value}, "
                f"op={result.operation.value}, violations={len(result.violations)}"
            )
            return result

        except Exception as e:
            logger.error(f"SQL安全验证失败: {e}", exc_info=True)
            return self.validator._make_blocked_result(f"验证过程出错: {str(e)}")

    def get_security_report(self, result: ValidationResult) -> Dict[str, Any]:
        """生成安全报告"""
        return {
            "summary": {
                "is_valid": result.is_valid,
                "security_level": result.security_level.value,
                "operation": result.operation.value,
                "violation_count": len(result.violations),
            },
            "violations": [
                {
                    "level": v.level.value,
                    "type": v.type,
                    "message": v.message,
                    "location": v.location,
                    "suggestion": v.suggestion,
                }
                for v in result.violations
            ],
            "references": {
                "tables": [{"name": t.table_name, "alias": t.alias} for t in result.table_references],
            },
            "complexity": {
                "score": result.complexity.complexity_score,
                "estimated_cost": result.complexity.estimated_cost,
                "table_count": result.complexity.table_count,
                "join_count": result.complexity.join_count,
                "subquery_count": result.complexity.subquery_count,
                "function_count": result.complexity.function_count,
                "condition_count": result.complexity.condition_count,
            },
            "sanitized_sql": result.sanitized_sql,
        }
