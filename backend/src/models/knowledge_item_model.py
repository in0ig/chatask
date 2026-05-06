from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import relationship
import uuid

from .base import Base

class KnowledgeItem(Base):
    __tablename__ = 'knowledge_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = Column(String(36), ForeignKey('knowledge_bases.id'), nullable=False)
    type = Column(Enum('TERM', 'LOGIC', 'EVENT'), nullable=False)
    
    # 1. 名词知识 (TERM) 独有
    name = Column(VARCHAR(200), nullable=True)  # 知识名称 (Only for TERM)
    
    # 2. 通用字段 (Common)
    explanation = Column(Text, nullable=False)  # 解释 (Required for ALL)
    
    # 3. 业务逻辑 (LOGIC) & 名词 (TERM) 共有
    example_question = Column(Text, nullable=True)  # 提问示例 (For TERM & LOGIC)
    
    # 4. 事件知识 (EVENT) 独有
    event_date_start = Column(DateTime, nullable=True)  # 事件开始时间
    event_date_end = Column(DateTime, nullable=True)    # 事件结束时间 (Optional)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系：关联到知识库
    knowledge_base = relationship('KnowledgeBase', back_populates='knowledge_items')
    
    def __repr__(self):
        return f"<KnowledgeItem(id={self.id}, type='{self.type}', name='{self.name}')>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'knowledge_base_id': self.knowledge_base_id,
            'type': self.type,
            'name': self.name,
            'explanation': self.explanation,
            'example_question': self.example_question,
            'event_date_start': self.event_date_start.isoformat() if self.event_date_start else None,
            'event_date_end': self.event_date_end.isoformat() if self.event_date_end else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }