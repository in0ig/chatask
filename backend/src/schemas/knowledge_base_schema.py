from pydantic import BaseModel
from typing import Optional
from enum import Enum

# 知识库类型枚举
class KnowledgeBaseType(str, Enum):
    TERM = "TERM"
    LOGIC = "LOGIC"
    EVENT = "EVENT"

# 知识库范围枚举
class KnowledgeBaseScope(str, Enum):
    GLOBAL = "GLOBAL"
    TABLE = "TABLE"

# 创建知识库的请求模型
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: KnowledgeBaseType
    scope: KnowledgeBaseScope
    status: Optional[bool] = True
    table_id: Optional[str] = None

# 更新知识库的请求模型
class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[KnowledgeBaseType] = None
    scope: Optional[KnowledgeBaseScope] = None
    status: Optional[bool] = None
    table_id: Optional[str] = None

# 响应模型
class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: KnowledgeBaseType
    scope: KnowledgeBaseScope
    status: bool
    table_id: Optional[str] = None
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
            'name': obj.name,
            'description': obj.description,
            'type': obj.type,
            'scope': obj.scope,
            'status': obj.status,
            'table_id': obj.table_id,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)