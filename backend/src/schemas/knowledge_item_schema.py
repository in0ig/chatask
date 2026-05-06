from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class KnowledgeType(str, Enum):
    TERM = "TERM"
    LOGIC = "LOGIC"
    EVENT = "EVENT"

class KnowledgeItemBase(BaseModel):
    type: KnowledgeType
    name: Optional[str] = Field(None, max_length=200, description="知识名称 (仅名词知识需要)")
    explanation: str = Field(..., max_length=1500, description="解释 (所有类型必需)")
    example_question: Optional[str] = Field(None, max_length=200, description="提问示例 (名词和业务逻辑知识)")
    event_date_start: Optional[str] = Field(None, description="事件开始时间 (仅事件知识)")
    event_date_end: Optional[str] = Field(None, description="事件结束时间 (仅事件知识)")

class KnowledgeItemCreate(KnowledgeItemBase):
    knowledge_base_id: str = Field(..., description="所属知识库ID")

class KnowledgeItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    explanation: Optional[str] = Field(None, max_length=1500)
    example_question: Optional[str] = Field(None, max_length=200)
    event_date_start: Optional[str] = None
    event_date_end: Optional[str] = None

class KnowledgeItemResponse(KnowledgeItemBase):
    id: str
    knowledge_base_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }
    
    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'knowledge_base_id': obj.knowledge_base_id,
            'type': obj.type,
            'name': obj.name,
            'explanation': obj.explanation,
            'example_question': obj.example_question,
            'event_date_start': obj.event_date_start.isoformat() if obj.event_date_start else None,
            'event_date_end': obj.event_date_end.isoformat() if obj.event_date_end else None,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemResponse]
    total: int
    page: int
    page_size: int