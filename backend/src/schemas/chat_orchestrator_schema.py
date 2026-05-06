"""
对话流程编排引擎数据模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ChatStageEnum(str, Enum):
    """对话阶段枚举"""
    INTENT_RECOGNITION = "intent_recognition"
    TABLE_SELECTION = "table_selection"
    INTENT_CLARIFICATION = "intent_clarification"
    SQL_GENERATION = "sql_generation"
    SQL_EXECUTION = "sql_execution"
    DATA_ANALYSIS = "data_analysis"
    RESULT_PRESENTATION = "result_presentation"
    ERROR_HANDLING = "error_handling"
    COMPLETED = "completed"


class ChatIntentEnum(str, Enum):
    """对话意图枚举"""
    SMART_QUERY = "smart_query"
    REPORT_GENERATION = "report_generation"
    DATA_FOLLOWUP = "data_followup"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"


class ChatStartRequest(BaseModel):
    """开始对话请求"""
    session_id: str = Field(..., description="会话ID")
    user_question: str = Field(..., description="用户问题")
    data_source_id: Optional[str] = Field(None, description="数据源ID（UUID）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "chat_001",
                "user_question": "查询销售额最高的产品",
                "data_source_id": "0ef69205-1c8a-4632-8597-48c91e1e6245"
            }
        }


class ChatContinueRequest(BaseModel):
    """继续对话请求"""
    session_id: str = Field(..., description="会话ID")
    user_response: str = Field(..., description="用户回复")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "chat_001",
                "user_response": "是的，请继续"
            }
        }


class ChatFollowupRequest(BaseModel):
    """追问请求"""
    session_id: str = Field(..., description="会话ID")
    followup_question: str = Field(..., description="追问问题")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "chat_001",
                "followup_question": "为什么这个产品销售额最高？"
            }
        }


class BatchChatRequest(BaseModel):
    """批量对话请求"""
    session_id: str = Field(..., description="会话ID")
    user_question: str = Field(..., description="用户问题")
    data_source_id: Optional[str] = Field(None, description="数据源ID（UUID）")


class ChatContextInfo(BaseModel):
    """对话上下文信息"""
    session_id: str = Field(..., description="会话ID")
    current_stage: ChatStageEnum = Field(..., description="当前阶段")
    intent: ChatIntentEnum = Field(..., description="对话意图")
    selected_tables: List[str] = Field(default_factory=list, description="选择的表")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    error_count: int = Field(0, description="错误次数")
    retry_count: int = Field(0, description="重试次数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    has_result: bool = Field(False, description="是否有查询结果")
    previous_data_count: int = Field(0, description="历史数据数量")


class ChatSessionStatus(BaseModel):
    """会话状态"""
    session_id: str = Field(..., description="会话ID")
    exists: bool = Field(..., description="会话是否存在")
    current_stage: Optional[ChatStageEnum] = Field(None, description="当前阶段")
    intent: Optional[ChatIntentEnum] = Field(None, description="对话意图")
    selected_tables: List[str] = Field(default_factory=list, description="选择的表")
    error_count: int = Field(0, description="错误次数")
    retry_count: int = Field(0, description="重试次数")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    has_result: bool = Field(False, description="是否有查询结果")
    previous_data_count: int = Field(0, description="历史数据数量")


class AllSessionsStatus(BaseModel):
    """所有会话状态"""
    total_sessions: int = Field(..., description="总会话数")
    sessions: Dict[str, Dict[str, Any]] = Field(..., description="会话详情")


class ChatResult(BaseModel):
    """对话结果"""
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    intent: Optional[str] = Field(None, description="识别的意图")
    tables: List[str] = Field(default_factory=list, description="选择的表")
    sql: Optional[str] = Field(None, description="生成的SQL")
    result: Optional[Dict[str, Any]] = Field(None, description="查询结果")
    analysis: Optional[str] = Field(None, description="数据分析")
    stage: Optional[str] = Field(None, description="当前阶段")
    error: Optional[str] = Field(None, description="错误信息")
    needs_clarification: bool = Field(False, description="是否需要澄清")
    clarification_question: Optional[str] = Field(None, description="澄清问题")
    retry_available: bool = Field(False, description="是否可重试")
    terminated: bool = Field(False, description="是否已终止")


class ClarificationResult(BaseModel):
    """澄清结果"""
    success: bool = Field(..., description="是否成功")
    needs_clarification: bool = Field(..., description="是否需要澄清")
    clarification_question: str = Field(..., description="澄清问题")
    session_id: str = Field(..., description="会话ID")
    selected_tables: List[str] = Field(default_factory=list, description="选择的表")


class FollowupResult(BaseModel):
    """追问结果"""
    success: bool = Field(..., description="是否成功")
    answer: str = Field(..., description="追问答案")
    session_id: str = Field(..., description="会话ID")
    type: str = Field("followup", description="结果类型")
    error: Optional[str] = Field(None, description="错误信息")


class BatchChatResult(BaseModel):
    """批量对话结果"""
    total: int = Field(..., description="总请求数")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[ChatResult] = Field(..., description="详细结果")


class ChatStageInfo(BaseModel):
    """对话阶段信息"""
    value: str = Field(..., description="阶段值")
    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")


class ChatIntentInfo(BaseModel):
    """对话意图信息"""
    value: str = Field(..., description="意图值")
    name: str = Field(..., description="意图名称")
    description: str = Field(..., description="意图描述")


class ChatStagesResponse(BaseModel):
    """对话阶段响应"""
    stages: List[ChatStageInfo] = Field(..., description="阶段列表")


class ChatIntentsResponse(BaseModel):
    """对话意图响应"""
    intents: List[ChatIntentInfo] = Field(..., description="意图列表")


class ChatHealthStatus(BaseModel):
    """对话服务健康状态"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    total_sessions: int = Field(..., description="总会话数")
    timestamp: str = Field(..., description="检查时间")


class IntentRecognitionResult(BaseModel):
    """意图识别结果"""
    success: bool = Field(..., description="是否成功")
    intent: str = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度")
    reason: str = Field(..., description="判断理由")
    error: Optional[str] = Field(None, description="错误信息")


class TableSelectionResult(BaseModel):
    """选表结果"""
    success: bool = Field(..., description="是否成功")
    tables: List[str] = Field(..., description="选择的表")
    reason: str = Field(..., description="选择理由")
    needs_clarification: bool = Field(False, description="是否需要澄清")
    clarification_question: Optional[str] = Field(None, description="澄清问题")
    error: Optional[str] = Field(None, description="错误信息")


class SQLGenerationResult(BaseModel):
    """SQL生成结果"""
    success: bool = Field(..., description="是否成功")
    sql: str = Field(..., description="生成的SQL")
    error: Optional[str] = Field(None, description="错误信息")


class SQLExecutionResult(BaseModel):
    """SQL执行结果"""
    success: bool = Field(..., description="是否成功")
    result: Optional[Dict[str, Any]] = Field(None, description="查询结果")
    error: Optional[str] = Field(None, description="错误信息")


class DataAnalysisResult(BaseModel):
    """数据分析结果"""
    success: bool = Field(..., description="是否成功")
    analysis: str = Field(..., description="分析结果")
    error: Optional[str] = Field(None, description="错误信息")


class QueryResultData(BaseModel):
    """查询结果数据"""
    columns: List[str] = Field(..., description="列名")
    rows: List[List[Any]] = Field(..., description="数据行")
    total_rows: int = Field(..., description="总行数")
    execution_time: float = Field(..., description="执行时间")


class ChartData(BaseModel):
    """图表数据"""
    type: str = Field(..., description="图表类型")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., description="图表数据")
    xAxis: Optional[str] = Field(None, description="X轴标签")
    yAxis: Optional[str] = Field(None, description="Y轴标签")


class PreviousDataInfo(BaseModel):
    """历史数据信息"""
    data: Dict[str, Any] = Field(..., description="历史数据")
    timestamp: str = Field(..., description="时间戳")
    sql: Optional[str] = Field(None, description="对应的SQL")


class ChatError(BaseModel):
    """对话错误"""
    error: str = Field(..., description="错误信息")
    timestamp: str = Field(..., description="错误时间")
    stage: str = Field(..., description="错误阶段")


class ChatMetadata(BaseModel):
    """对话元数据"""
    errors: List[ChatError] = Field(default_factory=list, description="错误列表")
    performance: Dict[str, float] = Field(default_factory=dict, description="性能指标")
    tokens_used: Dict[str, int] = Field(default_factory=dict, description="Token使用量")
    model_calls: Dict[str, int] = Field(default_factory=dict, description="模型调用次数")