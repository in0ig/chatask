"""
表格文件夹模式定义
定义文件夹的请求和响应模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class TableFolderBase(BaseModel):
    """
    表格文件夹基础模型
    """
    name: str = Field(..., min_length=1, max_length=100, description="文件夹名称")
    description: Optional[str] = Field(None, description="文件夹描述")
    sort_order: Optional[int] = Field(0, ge=0, description="排序顺序")
    status: Optional[bool] = Field(True, description="是否启用")

    class Config:
        schema_extra = {
            "example": {
                "name": "销售数据",
                "description": "销售相关的数据表文件夹",
                "sort_order": 1,
                "status": True
            }
        }


class TableFolderCreate(TableFolderBase):
    """
    创建表格文件夹的请求模型
    """
    parent_id: Optional[str] = Field(None, description="父文件夹ID，支持层级结构")
    created_by: Optional[str] = Field(None, description="创建人")

    class Config:
        schema_extra = {
            "example": {
                "name": "销售数据",
                "description": "销售相关的数据表文件夹",
                "parent_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "created_by": "admin",
                "sort_order": 1,
                "status": True
            }
        }


class TableFolderUpdate(TableFolderBase):
    """
    更新表格文件夹的请求模型
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="文件夹名称")
    parent_id: Optional[str] = Field(None, description="父文件夹ID，支持层级结构")
    created_by: Optional[str] = Field(None, description="创建人")

    class Config:
        schema_extra = {
            "example": {
                "name": "销售数据",
                "description": "销售相关的数据表文件夹",
                "parent_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "sort_order": 1,
                "status": True
            }
        }


class TableFolderResponse(TableFolderBase):
    """
    表格文件夹响应模型
    """
    id: str = Field(..., description="文件夹ID（UUID）")
    parent_id: Optional[str] = Field(None, description="父文件夹ID，支持层级结构")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True  # 支持从ORM模型转换
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "name": "销售数据",
                "description": "销售相关的数据表文件夹",
                "parent_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "sort_order": 1,
                "status": True,
                "created_by": "admin",
                "created_at": "2026-01-30T10:00:00Z",
                "updated_at": "2026-01-30T10:00:00Z"
            }
        }


class TableFolderTree(BaseModel):
    """
    表格文件夹树形结构模型
    支持嵌套的子文件夹结构
    """
    id: str = Field(..., description="文件夹ID（UUID）")
    name: str = Field(..., description="文件夹名称")
    description: Optional[str] = Field(None, description="文件夹描述")
    parent_id: Optional[str] = Field(None, description="父文件夹ID，支持层级结构")
    sort_order: int = Field(0, description="排序顺序")
    status: bool = Field(True, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    children: List['TableFolderTree'] = Field(default_factory=list, description="子文件夹列表")

    class Config:
        from_attributes = True  # 支持从ORM模型转换
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "name": "销售数据",
                "description": "销售相关的数据表文件夹",
                "parent_id": None,
                "sort_order": 1,
                "status": True,
                "created_by": "admin",
                "created_at": "2026-01-30T10:00:00Z",
                "updated_at": "2026-01-30T10:00:00Z",
                "children": [
                    {
                        "id": "b2c3d4e5-f6g7-8901-h2i3-j4k5l6m7n8o9",
                        "name": "2025年",
                        "description": "2025年度销售数据",
                        "parent_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                        "sort_order": 1,
                        "status": True,
                        "created_by": "admin",
                        "created_at": "2026-01-30T10:00:00Z",
                        "updated_at": "2026-01-30T10:00:00Z",
                        "children": []
                    }
                ]
            }
        }

# 递归类型定义，解决循环引用问题
TableFolderTree.model_rebuild()