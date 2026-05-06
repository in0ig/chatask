"""
SQL 方言守卫：在执行前做方言合法性检查。
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SQLDialectGuardResult:
    is_valid: bool
    error_code: str = ""
    error_message: str = ""
    retryable: bool = True
    details: Dict[str, List[str]] = field(default_factory=dict)


class SQLDialectGuard:
    def validate_sql(self, sql: str, db_type: Optional[str]) -> SQLDialectGuardResult:
        dialect = self._normalize_dialect(db_type)
        if not sql.strip():
            return SQLDialectGuardResult(
                is_valid=False,
                error_code="DIALECT_GUARD_EMPTY_SQL",
                error_message="SQL 为空，无法校验方言",
                retryable=True,
            )

        violations: List[str] = []
        if dialect == "sqlserver":
            violations.extend(self._check_sqlserver_violations(sql))
        elif dialect == "mysql":
            violations.extend(self._check_mysql_violations(sql))
        elif dialect == "postgresql":
            violations.extend(self._check_postgresql_violations(sql))

        if violations:
            return SQLDialectGuardResult(
                is_valid=False,
                error_code="DIALECT_GUARD_MISMATCH",
                error_message=f"SQL 与 {dialect} 方言不匹配",
                retryable=True,
                details={"violations": violations},
            )

        return SQLDialectGuardResult(is_valid=True)

    @staticmethod
    def _normalize_dialect(db_type: Optional[str]) -> str:
        raw = str(db_type or "").strip().lower().replace(" ", "").replace("_", "")
        if raw in {"sqlserver", "mssql"}:
            return "sqlserver"
        if raw in {"postgres", "postgresql", "pgsql"}:
            return "postgresql"
        return "mysql"

    @staticmethod
    def _contains(sql: str, pattern: str) -> bool:
        return re.search(pattern, sql, flags=re.IGNORECASE) is not None

    def _check_sqlserver_violations(self, sql: str) -> List[str]:
        violations: List[str] = []
        checks = [
            (r"\bLIMIT\s+\d+", "SQL Server 不支持 LIMIT"),
            (r"\bCURDATE\(", "SQL Server 不支持 CURDATE()"),
            (r"\bDATE_SUB\(", "SQL Server 不支持 DATE_SUB()"),
            (r"\bDATE_FORMAT\(", "SQL Server 不支持 DATE_FORMAT()"),
            (r"`[^`]+`", "SQL Server 不支持反引号标识符"),
        ]
        for pattern, message in checks:
            if self._contains(sql, pattern):
                violations.append(message)
        return violations

    def _check_mysql_violations(self, sql: str) -> List[str]:
        violations: List[str] = []
        checks = [
            (r"\bTOP\s+\d+", "MySQL 不支持 TOP N"),
            (r"\bOFFSET\s+\d+\s+ROWS\s+FETCH\s+NEXT\s+\d+\s+ROWS\s+ONLY", "MySQL 不支持 OFFSET..FETCH"),
            (r"\bGETDATE\(", "MySQL 不支持 GETDATE()"),
            (r"\bDATEADD\(", "MySQL 不支持 DATEADD()"),
            (r"\bISNULL\(", "MySQL 不支持 ISNULL(expr, repl) 的 SQL Server 语义"),
            (r"\[[^\]]+\]", "MySQL 不支持方括号标识符"),
        ]
        for pattern, message in checks:
            if self._contains(sql, pattern):
                violations.append(message)
        return violations

    def _check_postgresql_violations(self, sql: str) -> List[str]:
        violations: List[str] = []
        checks = [
            (r"\bTOP\s+\d+", "PostgreSQL 不支持 TOP N"),
            (r"\bGETDATE\(", "PostgreSQL 不支持 GETDATE()"),
            (r"\[[^\]]+\]", "PostgreSQL 不支持方括号标识符"),
        ]
        for pattern, message in checks:
            if self._contains(sql, pattern):
                violations.append(message)
        return violations
