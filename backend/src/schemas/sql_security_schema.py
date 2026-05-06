"""
SQL安全校验相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class SecurityLevel(str, Enum):
    """安全级别枚举"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class SQLOperation(str, Enum):
    """SQL操作类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    TRUNCATE = "TRUNCATE"
    UNKNOWN = "UNKNOWN"


class SecurityViolationSchema(BaseModel):
    """安全违规记录"""
    level: SecurityLevel = Field(..., description="违规级别")
    type: str = Field(..., description="违规类型")
    message: str = Field(..., description="违规消息")
    location: Optional[str] = Field(None, description="违规位置")
    suggestion: Optional[str] = Field(None, description="修复建议")


class TableReferenceSchema(BaseModel):
    """表引用信息"""
    table_name: str = Field(..., description="表名")
    alias: Optional[str] = Field(None, description="表别名")
    schema: Optional[str] = Field(None, description="模式名")


class FieldReferenceSchema(BaseModel):
    """字段引用信息"""
    field_name: str = Field(..., description="字段名")
    table_name: Optional[str] = Field(None, description="表名")
    table_alias: Optional[str] = Field(None, description="表别名")


class QueryComplexitySchema(BaseModel):
    """查询复杂度分析"""
    table_count: int = Field(..., description="涉及表数量")
    join_count: int = Field(..., description="JOIN数量")
    subquery_count: int = Field(..., description="子查询数量")
    function_count: int = Field(..., description="函数数量")
    condition_count: int = Field(..., description="条件数量")
    complexity_score: float = Field(..., description="复杂度分数")
    estimated_cost: str = Field(..., description="估算成本")


class ValidationResultSchema(BaseModel):
    """验证结果"""
    is_valid: bool = Field(..., description="是否有效")
    security_level: SecurityLevel = Field(..., description="安全级别")
    operation: SQLOperation = Field(..., description="SQL操作类型")
    violations: List[SecurityViolationSchema] = Field(default=[], description="违规列表")
    table_references: List[TableReferenceSchema] = Field(default=[], description="表引用列表")
    field_references: List[FieldReferenceSchema] = Field(default=[], description="字段引用列表")
    complexity: QueryComplexitySchema = Field(..., description="复杂度分析")
    sanitized_sql: Optional[str] = Field(None, description="清理后的SQL")


class SQLValidationRequest(BaseModel):
    """SQL验证请求"""
    sql_query: str = Field(..., description="SQL查询语句", min_length=1)
    data_source_id: Optional[int] = Field(None, description="数据源ID")
    check_existence: bool = Field(True, description="是否检查表和字段存在性")
    check_injection: bool = Field(True, description="是否检查SQL注入")
    check_complexity: bool = Field(True, description="是否检查复杂度")


class ComplexityAnalysisRequest(BaseModel):
    """复杂度分析请求"""
    sql_query: str = Field(..., description="SQL查询语句", min_length=1)


class InjectionCheckRequest(BaseModel):
    """注入检查请求"""
    sql_query: str = Field(..., description="SQL查询语句", min_length=1)


class FieldValidationRequest(BaseModel):
    """字段验证请求"""
    sql_query: str = Field(..., description="SQL查询语句", min_length=1)
    data_source_id: int = Field(..., description="数据源ID")


class SQLSanitizeRequest(BaseModel):
    """SQL清理请求"""
    sql_query: str = Field(..., description="SQL查询语句", min_length=1)


class SecurityConfigSchema(BaseModel):
    """安全配置"""
    limits: Dict[str, Any] = Field(..., description="限制配置")
    dangerous_keywords: List[str] = Field(..., description="危险关键词列表")
    allowed_operations: List[str] = Field(..., description="允许的操作")
    blocked_operations: List[str] = Field(..., description="禁止的操作")
    warning_operations: List[str] = Field(..., description="警告的操作")


class SecurityReportSchema(BaseModel):
    """安全报告"""
    summary: Dict[str, Any] = Field(..., description="摘要信息")
    violations: List[SecurityViolationSchema] = Field(..., description="违规列表")
    references: Dict[str, Any] = Field(..., description="引用信息")
    complexity: QueryComplexitySchema = Field(..., description="复杂度信息")
    sanitized_sql: Optional[str] = Field(None, description="清理后的SQL")


class ValidationResponse(BaseModel):
    """验证响应"""
    validation_result: ValidationResultSchema = Field(..., description="验证结果")
    security_report: SecurityReportSchema = Field(..., description="安全报告")


class ComplexityAnalysisResponse(BaseModel):
    """复杂度分析响应"""
    complexity: QueryComplexitySchema = Field(..., description="复杂度信息")
    recommendations: List[str] = Field(..., description="优化建议")


class InjectionCheckResponse(BaseModel):
    """注入检查响应"""
    injection_risk: Dict[str, Any] = Field(..., description="注入风险信息")
    violations: List[SecurityViolationSchema] = Field(..., description="违规列表")
    sanitized_sql: Optional[str] = Field(None, description="清理后的SQL")


class FieldValidationResponse(BaseModel):
    """字段验证响应"""
    existence_check: Dict[str, Any] = Field(..., description="存在性检查结果")
    violations: List[SecurityViolationSchema] = Field(..., description="违规列表")
    references: Dict[str, Any] = Field(..., description="引用信息")


class SQLSanitizeResponse(BaseModel):
    """SQL清理响应"""
    original_sql: str = Field(..., description="原始SQL")
    sanitized_sql: Optional[str] = Field(None, description="清理后的SQL")
    security_level: SecurityLevel = Field(..., description="安全级别")
    changes_made: bool = Field(..., description="是否有修改")