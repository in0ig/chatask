from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import relationship
import uuid

from .base import Base

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_bases'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(VARCHAR(200), nullable=False)
    description = Column(VARCHAR(1000))
    type = Column(Enum('TERM', 'LOGIC', 'EVENT'), nullable=False)
    scope = Column(Enum('GLOBAL', 'TABLE'), nullable=False)
    status = Column(Boolean, default=True)
    table_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系：知识库包含多个知识项
    knowledge_items = relationship('KnowledgeItem', back_populates='knowledge_base', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name='{self.name}', type='{self.type}', scope='{self.scope}')>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'scope': self.scope,
            'status': self.status,
            'table_id': self.table_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }