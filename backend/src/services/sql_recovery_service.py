# -*- coding: utf-8 -*-
"""
智能重试和自愈机制服务
基于Gemini错误反馈循环，实现SQL生成错误的自动分类和处理
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.services.ai_model_service import AIModelService, ModelRequest, TaskType
from src.services.prompt_manager import PromptManager, PromptType
from src.utils import logger


class SQLErrorType(Enum):
    """SQL错误类型枚举"""
    SYNTAX_ERROR = "syntax_error"
    FIELD_NOT_FOUND = "field_not_found"
    TABLE_NOT_FOUND = "table_not_found"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_DENIED = "permission_denied"
    CONSTRAINT_VIOLATION = "constraint_violation"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class SQLError:
    """SQL错误信息"""
    error_type: SQLErrorType
    original_sql: str
    error_message: str
    error_code: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    table_name: Optional[str] = None
    field_name: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    fixed_sql: Optional[str] = None
    error_analysis: Optional[str] = None
    changes_made: Optional[List[str]] = None
    confidence: float = 0.0
    retry_count: int = 0
    recovery_time: Optional[float] = None


class SQLErrorClassifier:
    """SQL错误分类器"""
    
    def __init__(self):
        # 错误模式匹配规则
        self.error_patterns = {
            SQLErrorType.SYNTAX_ERROR: [
                r"syntax error",
                r"unexpected token",
                r"missing",
                r"expected.*but found",
                r"invalid syntax"
            ],
            SQLErrorType.FIELD_NOT_FOUND: [
                r"unknown column",
                r"column.*doesn't exist",
                r"field.*not found",
                r"invalid column name"
            ],
            SQLErrorType.TABLE_NOT_FOUND: [
                r"table.*doesn't exist",
                r"unknown table",
                r"table.*not found",
                r"no such table"
            ],
            SQLErrorType.TYPE_MISMATCH: [
                r"data type mismatch",
                r"invalid data type",
                r"type conversion",
                r"cannot convert"
            ],
            SQLErrorType.PERMISSION_DENIED: [
                r"access denied",
                r"permission denied",
                r"insufficient privileges",
                r"not authorized"
            ],
            SQLErrorType.CONSTRAINT_VIOLATION: [
                r"constraint violation",
                r"foreign key constraint",
                r"unique constraint",
                r"check constraint"
            ],
            SQLErrorType.TIMEOUT_ERROR: [
                r"timeout",
                r"query timeout",
                r"execution timeout"
            ],
            SQLErrorType.CONNECTION_ERROR: [
                r"connection",
                r"network",
                r"host.*unreachable",
                r"connection refused"
            ]
        }
    
    def classify_error(self, error_message: str, sql: str) -> SQLError:
        """分类SQL错误"""
        error_message_lower = error_message.lower()
        
        # 尝试匹配错误类型
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message_lower):
                    return self._create_sql_error(error_type, sql, error_message)
        
        # 如果没有匹配到，返回未知错误
        return self._create_sql_error(SQLErrorType.UNKNOWN_ERROR, sql, error_message)
    
    def _create_sql_error(self, error_type: SQLErrorType, sql: str, error_message: str) -> SQLError:
        """创建SQL错误对象"""
        # 尝试提取更多错误信息
        table_name = self._extract_table_name(error_message)
        field_name = self._extract_field_name(error_message)
        line_number = self._extract_line_number(error_message)
        
        return SQLError(
            error_type=error_type,
            original_sql=sql,
            error_message=error_message,
            table_name=table_name,
            field_name=field_name,
            line_number=line_number
        )
    
    def _extract_table_name(self, error_message: str) -> Optional[str]:
        """从错误信息中提取表名"""
        patterns = [
            r"table\s+['\"]?(\w+)['\"]?",
            r"from\s+['\"]?(\w+)['\"]?",
            r"['\"]?(\w+)['\"]?\s+doesn't exist"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_field_name(self, error_message: str) -> Optional[str]:
        """从错误信息中提取字段名"""
        patterns = [
            r"column\s+['\"]?(\w+)['\"]?",
            r"field\s+['\"]?(\w+)['\"]?",
            r"['\"]?(\w+)['\"]?\s+doesn't exist"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_line_number(self, error_message: str) -> Optional[int]:
        """从错误信息中提取行号"""
        pattern = r"line\s+(\d+)"
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None


class SQLValidator:
    """SQL验证器"""
    
    def __init__(self):
        # 危险操作关键词
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
            'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL'
        ]
        
        # 允许的查询关键词
        self.allowed_keywords = [
            'SELECT', 'WITH', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 
            'ORDER BY', 'LIMIT', 'OFFSET', 'UNION', 'JOIN'
        ]
    
    def validate_sql_safety(self, sql: str) -> Tuple[bool, List[str]]:
        """验证SQL安全性"""
        issues = []
        sql_upper = sql.upper()
        
        # 检查危险操作
        for keyword in self.dangerous_keywords:
            if keyword in sql_upper:
                issues.append(f"包含危险操作: {keyword}")
        
        # 检查SQL注入模式
        injection_patterns = [
            r";\s*(DROP|DELETE|INSERT|UPDATE)",
            r"UNION\s+SELECT.*--",
            r"'\s*OR\s*'1'\s*=\s*'1",
            r"--\s*$",
            r"/\*.*\*/"
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(f"可能的SQL注入模式: {pattern}")
        
        return len(issues) == 0, issues
    
    def validate_sql_syntax(self, sql: str, db_type: str = "mysql") -> Tuple[bool, List[str]]:
        """验证SQL语法（基础检查）"""
        issues = []
        
        # 基础语法检查
        if not sql.strip():
            issues.append("SQL语句为空")
            return False, issues
        
        # 检查括号匹配
        if sql.count('(') != sql.count(')'):
            issues.append("括号不匹配")
        
        # 检查引号匹配
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            issues.append("单引号不匹配")
        
        double_quotes = sql.count('"') - sql.count('\\"')
        if double_quotes % 2 != 0:
            issues.append("双引号不匹配")
        
        # 检查基本SQL结构
        sql_upper = sql.upper().strip()
        if not any(sql_upper.startswith(keyword) for keyword in self.allowed_keywords):
            issues.append("SQL必须以SELECT、WITH等查询关键词开始")
        
        return len(issues) == 0, issues
    
    def validate_field_existence(self, sql: str, available_fields: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
        """验证字段存在性"""
        issues = []
        
        # 提取SQL中的字段引用
        field_references = self._extract_field_references(sql)
        
        for table_name, field_name in field_references:
            if table_name and table_name in available_fields:
                if field_name not in available_fields[table_name]:
                    issues.append(f"字段 {table_name}.{field_name} 不存在")
            elif not table_name:
                # 检查是否在任何表中存在
                found = False
                for table_fields in available_fields.values():
                    if field_name in table_fields:
                        found = True
                        break
                if not found:
                    issues.append(f"字段 {field_name} 在任何表中都不存在")
        
        return len(issues) == 0, issues
    
    def _extract_field_references(self, sql: str) -> List[Tuple[Optional[str], str]]:
        """提取SQL中的字段引用"""
        # 简化的字段提取逻辑
        field_references = []
        
        # 匹配 table.field 格式
        table_field_pattern = r'(\w+)\.(\w+)'
        matches = re.findall(table_field_pattern, sql)
        for table, field in matches:
            field_references.append((table, field))
        
        # 匹配单独的字段名（在SELECT、WHERE等子句中）
        # 这里需要更复杂的SQL解析，暂时简化处理
        
        return field_references


class SQLRecoveryService:
    """SQL恢复服务"""
    
    def __init__(self, ai_service: AIModelService, prompt_manager: PromptManager):
        self.ai_service = ai_service
        self.prompt_manager = prompt_manager
        self.classifier = SQLErrorClassifier()
        self.validator = SQLValidator()
        
        # 恢复策略配置
        self.max_retry_attempts = 3
        self.recovery_strategies = {
            SQLErrorType.FIELD_NOT_FOUND: self._recover_field_not_found,
            SQLErrorType.TABLE_NOT_FOUND: self._recover_table_not_found,
            SQLErrorType.SYNTAX_ERROR: self._recover_syntax_error,
            SQLErrorType.TYPE_MISMATCH: self._recover_type_mismatch
        }
        
        # 错误学习记录
        self.error_patterns: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("SQL recovery service initialized")
    
    async def recover_sql_error(
        self, 
        sql: str, 
        error_message: str,
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """恢复SQL错误"""
        start_time = datetime.now()
        
        # 分类错误
        sql_error = self.classifier.classify_error(error_message, sql)
        
        logger.info(f"Classified SQL error as: {sql_error.error_type.value}")
        
        # 记录错误模式
        self._record_error_pattern(sql_error)
        
        # 尝试恢复
        recovery_result = await self._attempt_recovery(sql_error, semantic_context, db_session)
        
        # 计算恢复时间
        recovery_time = (datetime.now() - start_time).total_seconds()
        recovery_result.recovery_time = recovery_time
        
        # 记录恢复结果
        if recovery_result.success:
            logger.info(f"SQL recovery successful in {recovery_time:.2f}s after {recovery_result.retry_count} attempts")
        else:
            logger.warning(f"SQL recovery failed after {recovery_result.retry_count} attempts")
        
        return recovery_result
    
    async def _attempt_recovery(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """尝试恢复SQL错误"""
        
        # 检查是否有特定的恢复策略
        if sql_error.error_type in self.recovery_strategies:
            strategy = self.recovery_strategies[sql_error.error_type]
            result = await strategy(sql_error, semantic_context, db_session)
            if result.success:
                return result
        
        # 使用AI模型进行通用恢复
        return await self._ai_based_recovery(sql_error, semantic_context)
    
    async def _ai_based_recovery(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """基于AI模型的SQL恢复"""
        
        for attempt in range(self.max_retry_attempts):
            try:
                # 构建恢复prompt
                variables = {
                    "original_sql": sql_error.original_sql,
                    "error_message": sql_error.error_message,
                    "semantic_context": self._format_semantic_context(semantic_context)
                }
                
                prompt = self.prompt_manager.render_prompt(PromptType.ERROR_RECOVERY, variables)
                
                # 调用AI模型
                request = ModelRequest(
                    prompt=prompt,
                    task_type=TaskType.SQL_GENERATION,
                    max_tokens=1000,
                    temperature=0.1
                )
                
                response = await self.ai_service.generate(request)
                
                # 解析AI响应
                recovery_data = self._parse_recovery_response(response.content)
                
                if recovery_data and recovery_data.get("fixedSQL"):
                    fixed_sql = recovery_data["fixedSQL"]
                    
                    # 验证修复后的SQL
                    is_safe, safety_issues = self.validator.validate_sql_safety(fixed_sql)
                    if not is_safe:
                        logger.warning(f"Fixed SQL has safety issues: {safety_issues}")
                        continue
                    
                    is_valid, syntax_issues = self.validator.validate_sql_syntax(fixed_sql)
                    if not is_valid:
                        logger.warning(f"Fixed SQL has syntax issues: {syntax_issues}")
                        continue
                    
                    return RecoveryResult(
                        success=True,
                        fixed_sql=fixed_sql,
                        error_analysis=recovery_data.get("errorAnalysis"),
                        changes_made=recovery_data.get("changes", []),
                        confidence=recovery_data.get("confidence", 0.5),
                        retry_count=attempt + 1
                    )
                
            except Exception as e:
                logger.error(f"AI recovery attempt {attempt + 1} failed: {str(e)}")
        
        return RecoveryResult(
            success=False,
            retry_count=self.max_retry_attempts,
            error_analysis=f"Failed to recover after {self.max_retry_attempts} attempts"
        )
    
    async def _recover_field_not_found(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """恢复字段不存在错误"""
        
        if not sql_error.field_name:
            return RecoveryResult(success=False, error_analysis="无法确定缺失的字段名")
        
        # 尝试从语义上下文中找到相似字段
        if semantic_context and "tables" in semantic_context:
            similar_fields = self._find_similar_fields(
                sql_error.field_name, 
                semantic_context["tables"]
            )
            
            if similar_fields:
                # 替换字段名
                fixed_sql = sql_error.original_sql.replace(
                    sql_error.field_name, 
                    similar_fields[0]["field_name"]
                )
                
                return RecoveryResult(
                    success=True,
                    fixed_sql=fixed_sql,
                    error_analysis=f"将字段 {sql_error.field_name} 替换为 {similar_fields[0]['field_name']}",
                    changes_made=[f"字段名修正: {sql_error.field_name} -> {similar_fields[0]['field_name']}"],
                    confidence=similar_fields[0]["similarity"],
                    retry_count=1
                )
        
        return RecoveryResult(success=False, error_analysis="未找到相似的字段名")
    
    async def _recover_table_not_found(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """恢复表不存在错误"""
        
        if not sql_error.table_name:
            return RecoveryResult(success=False, error_analysis="无法确定缺失的表名")
        
        # 尝试从语义上下文中找到相似表名
        if semantic_context and "tables" in semantic_context:
            similar_tables = self._find_similar_tables(
                sql_error.table_name, 
                semantic_context["tables"]
            )
            
            if similar_tables:
                # 替换表名
                fixed_sql = sql_error.original_sql.replace(
                    sql_error.table_name, 
                    similar_tables[0]["table_name"]
                )
                
                return RecoveryResult(
                    success=True,
                    fixed_sql=fixed_sql,
                    error_analysis=f"将表名 {sql_error.table_name} 替换为 {similar_tables[0]['table_name']}",
                    changes_made=[f"表名修正: {sql_error.table_name} -> {similar_tables[0]['table_name']}"],
                    confidence=similar_tables[0]["similarity"],
                    retry_count=1
                )
        
        return RecoveryResult(success=False, error_analysis="未找到相似的表名")
    
    async def _recover_syntax_error(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """恢复语法错误"""
        
        # 常见语法错误修复
        fixed_sql = sql_error.original_sql
        changes = []
        
        # 修复常见的语法问题
        # 1. 缺少分号
        if not fixed_sql.strip().endswith(';'):
            fixed_sql = fixed_sql.strip() + ';'
            changes.append("添加结尾分号")
        
        # 2. 修复引号问题
        # 简单的引号修复逻辑
        
        # 3. 修复关键词大小写
        # MySQL通常不区分大小写，但保持一致性
        
        if changes:
            return RecoveryResult(
                success=True,
                fixed_sql=fixed_sql,
                error_analysis="修复了基本语法错误",
                changes_made=changes,
                confidence=0.7,
                retry_count=1
            )
        
        return RecoveryResult(success=False, error_analysis="无法自动修复语法错误")
    
    async def _recover_type_mismatch(
        self, 
        sql_error: SQLError, 
        semantic_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> RecoveryResult:
        """恢复类型不匹配错误"""
        
        # 这里需要更复杂的类型推断和转换逻辑
        # 暂时返回失败，让AI模型处理
        return RecoveryResult(success=False, error_analysis="类型不匹配错误需要AI模型处理")
    
    def _find_similar_fields(self, target_field: str, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找相似字段"""
        similar_fields = []
        target_lower = target_field.lower()
        
        for table in tables:
            for field in table.get("fields", []):
                field_name = field.get("name", "")
                field_lower = field_name.lower()
                
                # 计算相似度（简单的字符串匹配）
                similarity = self._calculate_string_similarity(target_lower, field_lower)
                
                if similarity > 0.6:  # 相似度阈值
                    similar_fields.append({
                        "table_name": table.get("name"),
                        "field_name": field_name,
                        "similarity": similarity
                    })
        
        # 按相似度排序
        similar_fields.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_fields[:3]  # 返回前3个最相似的
    
    def _find_similar_tables(self, target_table: str, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找相似表名"""
        similar_tables = []
        target_lower = target_table.lower()
        
        for table in tables:
            table_name = table.get("name", "")
            table_lower = table_name.lower()
            
            # 计算相似度
            similarity = self._calculate_string_similarity(target_lower, table_lower)
            
            if similarity > 0.6:  # 相似度阈值
                similar_tables.append({
                    "table_name": table_name,
                    "similarity": similarity
                })
        
        # 按相似度排序
        similar_tables.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_tables[:3]  # 返回前3个最相似的
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简单的编辑距离）"""
        if str1 == str2:
            return 1.0
        
        if not str1 or not str2:
            return 0.0
        
        # 简单的相似度计算
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
        
        # 计算公共子串
        common_chars = set(str1) & set(str2)
        return len(common_chars) / max_len
    
    def _format_semantic_context(self, semantic_context: Optional[Dict[str, Any]]) -> str:
        """格式化语义上下文"""
        if not semantic_context:
            return "无可用的语义上下文"
        
        formatted_parts = []
        
        if "tables" in semantic_context:
            formatted_parts.append("可用表结构:")
            for table in semantic_context["tables"][:5]:  # 限制表数量
                table_info = f"- {table.get('name', 'unknown')}"
                if "fields" in table:
                    fields = [f.get('name', '') for f in table['fields'][:10]]  # 限制字段数量
                    table_info += f" (字段: {', '.join(fields)})"
                formatted_parts.append(table_info)
        
        return "\n".join(formatted_parts) if formatted_parts else "无可用的语义上下文"
    
    def _parse_recovery_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """解析AI恢复响应"""
        try:
            # 尝试解析JSON响应
            if response_content.strip().startswith('{'):
                return json.loads(response_content)
            
            # 尝试从文本中提取JSON
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response_content, re.DOTALL)
            if match:
                return json.loads(match.group())
            
            return None
        
        except json.JSONDecodeError:
            logger.error(f"Failed to parse recovery response: {response_content[:200]}...")
            return None
    
    def _record_error_pattern(self, sql_error: SQLError) -> None:
        """记录错误模式用于学习"""
        error_key = sql_error.error_type.value
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = []
        
        pattern_record = {
            "error_message": sql_error.error_message,
            "sql_snippet": sql_error.original_sql[:100],  # 只记录前100个字符
            "table_name": sql_error.table_name,
            "field_name": sql_error.field_name,
            "timestamp": sql_error.timestamp.isoformat()
        }
        
        self.error_patterns[error_key].append(pattern_record)
        
        # 限制记录数量，避免内存泄漏
        if len(self.error_patterns[error_key]) > 100:
            self.error_patterns[error_key] = self.error_patterns[error_key][-50:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        stats = {}
        
        for error_type, patterns in self.error_patterns.items():
            stats[error_type] = {
                "total_count": len(patterns),
                "recent_count": len([p for p in patterns if 
                    datetime.fromisoformat(p["timestamp"]) > datetime.now().replace(hour=0, minute=0, second=0)
                ])
            }
        
        return stats


# 导出主要类和函数
__all__ = [
    "SQLRecoveryService",
    "SQLErrorClassifier",
    "SQLValidator",
    "SQLErrorType",
    "SQLError",
    "RecoveryResult"
]