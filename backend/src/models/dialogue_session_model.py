"""
对话会话数据库模型
实现会话状态的持久化存储
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.sql import func
from datetime import datetime
import enum

from src.database import Base


class SessionStatus(enum.Enum):
    """会话状态枚举"""
    ACTIVE = "active"          # 活跃
    PAUSED = "paused"          # 暂停
    CLOSED = "closed"          # 关闭
    ARCHIVED = "archived"      # 已归档
    ERROR = "error"            # 错误状态


class DialogueSession(Base):
    """对话会话模型"""
    __tablename__ = "dialogue_sessions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True, comment="会话唯一标识")
    user_id = Column(String(100), nullable=True, index=True, comment="用户ID")
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, comment="会话状态")
    
    # 会话元数据
    title = Column(String(200), nullable=True, comment="会话标题")
    description = Column(Text, nullable=True, comment="会话描述")
    
    # 会话上下文（JSON格式存储）
    context_data = Column(JSON, nullable=True, comment="会话上下文数据")
    cloud_messages = Column(JSON, nullable=True, comment="云端历史消息")
    local_messages = Column(JSON, nullable=True, comment="本地历史消息")
    
    # 会话统计
    message_count = Column(Integer, default=0, comment="消息总数")
    total_tokens = Column(Integer, default=0, comment="Token总数")
    error_count = Column(Integer, default=0, comment="错误次数")
    
    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    last_activity_at = Column(DateTime, default=func.now(), nullable=False, comment="最后活动时间")
    closed_at = Column(DateTime, nullable=True, comment="关闭时间")
    archived_at = Column(DateTime, nullable=True, comment="归档时间")
    
    # 配置
    auto_archive = Column(Boolean, default=True, comment="是否自动归档")
    archive_after_days = Column(Integer, default=30, comment="多少天后归档")
    
    def __repr__(self):
        return f"<DialogueSession(session_id='{self.session_id}', status='{self.status.value}', message_count={self.message_count})>"
    
    def to_dict(self, include_messages: bool = False):
        """
        转换为字典
        
        Args:
            include_messages: 是否包含消息内容（默认不包含，减少数据传输）
        """
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "auto_archive": self.auto_archive,
            "archive_after_days": self.archive_after_days
        }
        
        # 可选包含消息内容
        if include_messages:
            result["cloud_messages"] = self.cloud_messages or []
            result["local_messages"] = self.local_messages or []
        
        return result
