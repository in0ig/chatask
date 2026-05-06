from sqlalchemy import Column, Integer, String, Text, JSON, Enum, Boolean, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship
import enum
from src.models.base import Base

class PromptType(enum.Enum):
    intent_recognition = "intent_recognition"
    table_selection = "table_selection"
    sql_generation = "sql_generation"
    sql_error_recovery = "sql_error_recovery"
    data_interpretation = "data_interpretation"
    fluctuation_attribution = "fluctuation_attribution"
    follow_up_handling = "follow_up_handling"
    analysis_strategy_application = "analysis_strategy_application"

class ContextType(enum.Enum):
    local_model = "local_model"
    aliyun_model = "aliyun_model"

class Role(enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class ModelUsed(enum.Enum):
    aliyun = "aliyun"
    local = "local"
    none = "none"

class ModelType(enum.Enum):
    local = "local"
    aliyun = "aliyun"

class PromptConfig(Base):
    __tablename__ = 'prompt_config'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), nullable=False)
    prompt_type = Column(Enum(PromptType), nullable=False)
    prompt_category = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    examples = Column(JSON)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    enabled = Column(Boolean, default=True)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class SessionContext(Base):
    __tablename__ = 'session_context'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    context_type = Column(Enum(ContextType), nullable=False)
    messages = Column(JSON)
    token_count = Column(Integer, default=0)
    summary = Column(Text)
    last_summary_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    turn = Column(Integer, nullable=False)
    role = Column(Enum(Role), nullable=False)
    content = Column(Text, nullable=False)
    parent_message_id = Column(Integer, ForeignKey('conversation_messages.id', ondelete='CASCADE'))
    token_count = Column(Integer, default=0)
    model_used = Column(Enum(ModelUsed), default=ModelUsed.none)
    intent = Column(String(100))
    query_id = Column(String(100))
    analysis_id = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    error_message = Column(Text)  # 新增字段：存储错误信息
    
    # Self-referential relationship for parent messages
    # TODO: 暂时注释掉以解决多重类注册问题
    # parent = relationship("ConversationMessage", remote_side="ConversationMessage.id", backref="children", post_update=True)

class TokenUsageStats(Base):
    __tablename__ = 'token_usage_stats'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False)
    model_type = Column(Enum(ModelType), nullable=False)
    turn = Column(Integer, nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

# Add indexes
from sqlalchemy import Index

# ConversationMessage indexes
# 注意：由于暂时注释了自引用关系，也暂时注释相关索引
# Index('idx_session_turn', ConversationMessage.session_id, ConversationMessage.turn)
# Index('idx_parent', ConversationMessage.parent_message_id)

# Other indexes can be added as needed

# Ensure all models are included in Base.metadata
# This is important for Alembic to detect them

# Note: We need to ensure that our models are properly imported in env.py
# so that Base.metadata contains all our tables
