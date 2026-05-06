"""
对话会话 Schema 定义
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SessionStatusEnum(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"
    ERROR = "error"


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: Optional[str] = Field(None, description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    description: Optional[str] = Field(None, description="会话描述")
    auto_archive: bool = Field(True, description="是否自动归档")
    archive_after_days: int = Field(30, description="多少天后归档")


class UpdateSessionStatusRequest(BaseModel):
    """更新会话状态请求"""
    status: SessionStatusEnum = Field(..., description="新状态")
    reason: Optional[str] = Field(None, description="状态变更原因")


class MigrateSessionRequest(BaseModel):
    """迁移会话请求"""
    target_user_id: str = Field(..., description="目标用户ID")
    reason: Optional[str] = Field(None, description="迁移原因")


class SessionResponse(BaseModel):
    """会话响应"""
    id: int
    session_id: str
    user_id: Optional[str]
    status: str
    title: Optional[str]
    description: Optional[str]
    message_count: int
    total_tokens: int
    error_count: int
    created_at: str
    updated_at: str
    last_activity_at: str
    closed_at: Optional[str]
    archived_at: Optional[str]
    auto_archive: bool
    archive_after_days: int


class SessionListResponse(BaseModel):
    """会话列表响应"""
    success: bool
    total: int
    limit: int
    offset: int
    sessions: List[SessionResponse]


class SessionStatisticsResponse(BaseModel):
    """会话统计响应"""
    success: bool
    statistics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OperationResponse(BaseModel):
    """操作响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
