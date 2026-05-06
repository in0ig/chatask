"""
本地数据分析引擎Schema定义
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryResultSchema(BaseModel):
    """查询结果Schema"""
    query_id: str = Field(..., description="查询ID")
    sql: str = Field(..., description="SQL语句")
    data: List[Dict[str, Any]] = Field(..., description="查询结果数据")
    columns: List[str] = Field(..., description="列名列表")
    row_count: int = Field(..., description="行数")
    executed_at: datetime = Field(..., description="执行时间")


class AnalysisRequest(BaseModel):
    """数据分析请求Schema"""
    session_id: str = Field(..., description="会话ID")
    query_result: QueryResultSchema = Field(..., description="当前查询结果")
    previous_results: List[QueryResultSchema] = Field(
        default_factory=list,
        description="历史查询结果"
    )
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="对话历史"
    )
    user_question: str = Field(..., description="用户问题")
    stream: bool = Field(default=False, description="是否使用流式响应")


class ComparisonRequest(BaseModel):
    """数据对比请求Schema"""
    session_id: str = Field(..., description="会话ID")
    current_result: QueryResultSchema = Field(..., description="当前查询结果")
    previous_result: QueryResultSchema = Field(..., description="之前的查询结果")
    comparison_question: str = Field(..., description="对比问题")


class AnalysisResponse(BaseModel):
    """数据分析响应Schema"""
    analysis_id: str = Field(..., description="分析ID")
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="分析回答")
    insights: List[str] = Field(..., description="数据洞察列表")
    data_points: List[Dict[str, Any]] = Field(..., description="关键数据点")
    created_at: datetime = Field(..., description="创建时间")


class AnalysisStatsResponse(BaseModel):
    """分析统计响应Schema"""
    total_analyses: int = Field(..., description="总分析次数")
    successful_analyses: int = Field(..., description="成功分析次数")
    failed_analyses: int = Field(..., description="失败分析次数")
    total_tokens_used: int = Field(..., description="总Token使用量")
    average_response_time: float = Field(..., description="平均响应时间（秒）")
    success_rate: float = Field(..., description="成功率")


class TrendAnalysisRequest(BaseModel):
    """趋势分析请求Schema"""
    session_id: str = Field(..., description="会话ID")
    time_series_data: List[QueryResultSchema] = Field(..., description="时间序列数据")
    analysis_question: str = Field(..., description="分析问题")
    time_column: str = Field(..., description="时间列名")
    value_columns: List[str] = Field(..., description="数值列名列表")


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求Schema"""
    session_id: str = Field(..., description="会话ID")
    query_result: QueryResultSchema = Field(..., description="查询结果")
    detection_columns: List[str] = Field(..., description="需要检测异常的列")
    threshold: Optional[float] = Field(None, description="异常阈值")


class InsightGenerationRequest(BaseModel):
    """洞察生成请求Schema"""
    session_id: str = Field(..., description="会话ID")
    query_result: QueryResultSchema = Field(..., description="查询结果")
    focus_areas: List[str] = Field(
        default_factory=list,
        description="关注领域（如：趋势、异常、相关性等）"
    )
