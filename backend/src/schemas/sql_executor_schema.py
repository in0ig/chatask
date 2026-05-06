"""
SQL执行服务的Schema定义
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class DatabaseTypeEnum(str, Enum):
    """数据库类型枚举"""
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    POSTGRESQL = "postgresql"


class ExecutionRequest(BaseModel):
    """SQL执行请求"""
    sql: str = Field(..., description="SQL查询语句")
    data_source_id: int = Field(..., description="数据源ID")
    use_cache: bool = Field(default=True, description="是否使用缓存")
    timeout_seconds: Optional[int] = Field(default=30, description="超时时间（秒）")
    max_rows: Optional[int] = Field(default=10000, description="最大返回行数")
    
    @validator('sql')
    def validate_sql(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL语句不能为空")
        return v.strip()
    
    @validator('timeout_seconds')
    def validate_timeout(cls, v):
        if v is not None and (v < 1 or v > 300):
            raise ValueError("超时时间必须在1-300秒之间")
        return v
    
    @validator('max_rows')
    def validate_max_rows(cls, v):
        if v is not None and (v < 1 or v > 100000):
            raise ValueError("最大行数必须在1-100000之间")
        return v


class PaginatedExecutionRequest(BaseModel):
    """分页执行请求"""
    sql: str = Field(..., description="SQL查询语句")
    data_source_id: int = Field(..., description="数据源ID")
    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=1000, ge=1, le=10000, description="每页大小")
    
    @validator('sql')
    def validate_sql(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL语句不能为空")
        return v.strip()


class StreamExecutionRequest(BaseModel):
    """流式执行请求"""
    sql: str = Field(..., description="SQL查询语句")
    data_source_id: int = Field(..., description="数据源ID")
    chunk_size: int = Field(default=100, ge=10, le=1000, description="每次返回的行数")
    
    @validator('sql')
    def validate_sql(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL语句不能为空")
        return v.strip()


class PageInfo(BaseModel):
    """分页信息"""
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    offset: int = Field(..., description="偏移量")
    has_next: bool = Field(..., description="是否有下一页")


class QueryResultResponse(BaseModel):
    """查询结果响应"""
    columns: List[str] = Field(..., description="列名列表")
    rows: List[List[Any]] = Field(..., description="数据行列表")
    row_count: int = Field(..., description="返回的行数")
    execution_time: float = Field(..., description="执行时间（秒）")
    is_truncated: bool = Field(default=False, description="是否被截断")
    has_more: bool = Field(default=False, description="是否还有更多数据")
    page_info: Optional[PageInfo] = Field(None, description="分页信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ExecutionStatisticsResponse(BaseModel):
    """执行统计响应"""
    total_queries: int = Field(..., description="总查询数")
    successful_queries: int = Field(..., description="成功查询数")
    failed_queries: int = Field(..., description="失败查询数")
    timeout_queries: int = Field(..., description="超时查询数")
    success_rate: float = Field(..., description="成功率")
    average_execution_time: float = Field(..., description="平均执行时间（秒）")
    total_rows_returned: int = Field(..., description="总返回行数")
    cache_hits: int = Field(..., description="缓存命中数")
    cache_hit_rate: float = Field(..., description="缓存命中率")
    active_queries: int = Field(..., description="活跃查询数")
    cache_size: int = Field(..., description="缓存大小")


class HealthStatusResponse(BaseModel):
    """健康状态响应"""
    status: str = Field(..., description="状态（healthy/degraded/unhealthy）")
    active_queries: int = Field(..., description="活跃查询数")
    max_concurrent_queries: int = Field(..., description="最大并发查询数")
    cache_size: int = Field(..., description="缓存大小")
    statistics: ExecutionStatisticsResponse = Field(..., description="统计信息")


class FormatRequest(BaseModel):
    """格式化请求"""
    format_type: str = Field(..., description="格式类型（json/csv/table）")
    
    @validator('format_type')
    def validate_format_type(cls, v):
        if v not in ['json', 'csv', 'table']:
            raise ValueError("格式类型必须是 json、csv 或 table")
        return v


class BatchExecutionRequest(BaseModel):
    """批量执行请求"""
    queries: List[ExecutionRequest] = Field(..., description="查询列表", max_items=10)
    
    @validator('queries')
    def validate_queries(cls, v):
        if not v:
            raise ValueError("查询列表不能为空")
        if len(v) > 10:
            raise ValueError("批量执行最多支持10个查询")
        return v


class BatchExecutionResponse(BaseModel):
    """批量执行响应"""
    results: List[QueryResultResponse] = Field(..., description="结果列表")
    total_execution_time: float = Field(..., description="总执行时间（秒）")
    successful_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
