"""
WebSocket流式通信数据模式定义
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class StreamMessageTypeEnum(str, Enum):
    """流式消息类型枚举"""
    THINKING = "thinking"
    RESULT = "result"
    CHART = "chart"
    ERROR = "error"
    STATUS = "status"
    HEARTBEAT = "heartbeat"
    STAGE_START = "stage_start"
    STAGE_UPDATE = "stage_update"
    STAGE_COMPLETE = "stage_complete"


class ConnectionStatusEnum(str, Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class StreamMessageRequest(BaseModel):
    """流式消息请求"""
    message_type: StreamMessageTypeEnum = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    connection_id: Optional[str] = Field(None, description="指定连接ID")


class ThinkingMessageRequest(BaseModel):
    """思考消息请求"""
    content: str = Field(..., description="思考内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ResultMessageRequest(BaseModel):
    """结果消息请求"""
    content: str = Field(..., description="结果内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ChartMessageRequest(BaseModel):
    """图表消息请求"""
    chart_data: Dict[str, Any] = Field(..., description="图表数据")


class ErrorMessageRequest(BaseModel):
    """错误消息请求"""
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")


class StatusMessageRequest(BaseModel):
    """状态消息请求"""
    status: str = Field(..., description="状态信息")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="进度（0.0-1.0）")


class StageStartRequest(BaseModel):
    """阶段开始消息请求"""
    stage_id: str = Field(..., description="阶段ID")
    stage_name: str = Field(..., description="阶段名称")
    content: str = Field(default="", description="阶段内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class StageUpdateRequest(BaseModel):
    """阶段更新消息请求"""
    stage_id: str = Field(..., description="阶段ID")
    content: str = Field(..., description="更新内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class StageCompleteRequest(BaseModel):
    """阶段完成消息请求"""
    stage_id: str = Field(..., description="阶段ID")
    stage_name: str = Field(..., description="阶段名称")
    content: str = Field(default="", description="完成内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class StreamMessageResponse(BaseModel):
    """流式消息响应"""
    id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    type: StreamMessageTypeEnum = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    timestamp: float = Field(..., description="时间戳")
    sequence: int = Field(..., description="消息序号")
    # 可折叠相关字段
    stage_id: Optional[str] = Field(None, description="阶段ID")
    stage_name: Optional[str] = Field(None, description="阶段名称")
    stage_status: Optional[str] = Field(None, description="阶段状态")
    collapsible: bool = Field(False, description="是否可折叠")
    collapsed: bool = Field(False, description="是否默认折叠")


class ConnectionInfo(BaseModel):
    """连接信息"""
    connection_id: str = Field(..., description="连接ID")
    status: ConnectionStatusEnum = Field(..., description="连接状态")
    connected_at: str = Field(..., description="连接时间")
    last_heartbeat: float = Field(..., description="最后心跳时间")
    message_sequence: int = Field(..., description="消息序号")
    pending_messages: int = Field(..., description="待发送消息数")


class SessionConnectionStatus(BaseModel):
    """会话连接状态"""
    session_id: str = Field(..., description="会话ID")
    connection_count: int = Field(..., description="连接数量")
    connections: List[ConnectionInfo] = Field(..., description="连接列表")


class AllConnectionsStatus(BaseModel):
    """所有连接状态"""
    total_connections: int = Field(..., description="总连接数")
    total_sessions: int = Field(..., description="总会话数")
    sessions: Dict[str, SessionConnectionStatus] = Field(..., description="会话状态")


class WebSocketMessage(BaseModel):
    """WebSocket消息格式"""
    type: StreamMessageTypeEnum = Field(..., description="消息类型")
    id: Optional[str] = Field(None, description="消息ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    content: Optional[str] = Field(None, description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    timestamp: Optional[float] = Field(None, description="时间戳")
    sequence: Optional[int] = Field(None, description="消息序号")
    # 可折叠相关字段
    stage_id: Optional[str] = Field(None, description="阶段ID")
    stage_name: Optional[str] = Field(None, description="阶段名称")
    stage_status: Optional[str] = Field(None, description="阶段状态")
    collapsible: Optional[bool] = Field(None, description="是否可折叠")
    collapsed: Optional[bool] = Field(None, description="是否默认折叠")


class HeartbeatMessage(BaseModel):
    """心跳消息"""
    type: str = Field(default="heartbeat", description="消息类型")
    timestamp: float = Field(..., description="时间戳")


class ApiResponse(BaseModel):
    """API响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    total_connections: int = Field(..., description="总连接数")
    total_sessions: int = Field(..., description="总会话数")
    timestamp: str = Field(..., description="检查时间")


# 图表数据相关模式
class ChartDataColumn(BaseModel):
    """图表数据列"""
    name: str = Field(..., description="列名")
    type: str = Field(..., description="数据类型")
    description: Optional[str] = Field(None, description="列描述")


class ChartData(BaseModel):
    """图表数据"""
    columns: List[ChartDataColumn] = Field(..., description="列定义")
    rows: List[List[Any]] = Field(..., description="数据行")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ChartConfig(BaseModel):
    """图表配置"""
    type: str = Field(..., description="图表类型")
    title: Optional[str] = Field(None, description="图表标题")
    theme: Optional[str] = Field("light", description="图表主题")
    options: Optional[Dict[str, Any]] = Field(None, description="图表选项")


class ChartMessage(BaseModel):
    """图表消息"""
    chart_data: ChartData = Field(..., description="图表数据")
    chart_config: Optional[ChartConfig] = Field(None, description="图表配置")


# 错误相关模式
class StreamError(BaseModel):
    """流式错误"""
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: float = Field(..., description="错误时间")


class ConnectionError(BaseModel):
    """连接错误"""
    connection_id: str = Field(..., description="连接ID")
    error_type: str = Field(..., description="错误类型")
    error_message: str = Field(..., description="错误信息")
    timestamp: float = Field(..., description="错误时间")


# 状态更新相关模式
class StatusUpdate(BaseModel):
    """状态更新"""
    status: str = Field(..., description="状态信息")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="进度")
    stage: Optional[str] = Field(None, description="当前阶段")
    estimated_time: Optional[float] = Field(None, description="预估剩余时间（秒）")


class ProcessingStage(BaseModel):
    """处理阶段"""
    stage_name: str = Field(..., description="阶段名称")
    stage_description: str = Field(..., description="阶段描述")
    progress: float = Field(..., ge=0.0, le=1.0, description="阶段进度")
    start_time: float = Field(..., description="开始时间")
    end_time: Optional[float] = Field(None, description="结束时间")


# 会话管理相关模式
class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    message_count: int = Field(..., description="消息数量")
    connection_count: int = Field(..., description="连接数量")


class SessionStats(BaseModel):
    """会话统计"""
    total_sessions: int = Field(..., description="总会话数")
    active_sessions: int = Field(..., description="活跃会话数")
    total_messages: int = Field(..., description="总消息数")
    average_session_duration: float = Field(..., description="平均会话时长（秒）")


# 性能监控相关模式
class PerformanceMetrics(BaseModel):
    """性能指标"""
    message_throughput: float = Field(..., description="消息吞吐量（消息/秒）")
    average_latency: float = Field(..., description="平均延迟（毫秒）")
    connection_success_rate: float = Field(..., description="连接成功率")
    message_delivery_rate: float = Field(..., description="消息投递成功率")
    memory_usage: float = Field(..., description="内存使用量（MB）")


class SystemHealth(BaseModel):
    """系统健康状态"""
    status: str = Field(..., description="系统状态")
    uptime: float = Field(..., description="运行时间（秒）")
    performance: PerformanceMetrics = Field(..., description="性能指标")
    connections: AllConnectionsStatus = Field(..., description="连接状态")
    timestamp: datetime = Field(..., description="检查时间")