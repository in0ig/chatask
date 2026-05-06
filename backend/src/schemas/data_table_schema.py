"""
数据表模式定义
定义数据表的请求和响应模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DataTableCreate(BaseModel):
    """
    创建数据表的请求模型
    """
    source_id: str = Field(..., description="所属数据源ID")
    table_name: str = Field(..., min_length=1, max_length=255, description="表名")
    description: Optional[str] = Field(None, description="表描述")
    row_count: Optional[int] = Field(None, ge=0, description="行数")
    column_count: Optional[int] = Field(None, ge=0, description="列数")
    status: Optional[bool] = Field(True, description="是否启用")

    class Config:
        schema_extra = {
            "example": {
                "source_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "table_name": "users",
                "description": "用户信息表",
                "row_count": 1000,
                "column_count": 5,
                "status": True
            }
        }


class DataTableUpdate(BaseModel):
    """
    更新数据表的请求模型
    """
    source_id: Optional[str] = Field(None, description="所属数据源ID")
    table_name: Optional[str] = Field(None, min_length=1, max_length=255, description="表名")
    schema_name: Optional[str] = Field(None, max_length=100, description="模式名/数据库名")
    description: Optional[str] = Field(None, description="表描述")
    row_count: Optional[int] = Field(None, ge=0, description="行数")
    column_count: Optional[int] = Field(None, ge=0, description="列数")
    status: Optional[bool] = Field(None, description="是否启用")
    last_refreshed: Optional[datetime] = Field(None, description="最后刷新时间")

    class Config:
        schema_extra = {
            "example": {
                "table_name": "users",
                "description": "用户信息表",
                "status": True
            }
        }


class DataTableResponse(BaseModel):
    """
    数据表响应模型
    """
    id: str = Field(..., description="数据表ID（UUID）")
    data_source_id: str = Field(..., description="所属数据源ID")
    data_source_name: Optional[str] = Field(None, description="数据源名称")
    table_name: str = Field(..., description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="表描述")
    data_mode: Optional[str] = Field(None, description="数据模式")
    status: bool = Field(..., description="是否启用")
    field_count: Optional[int] = Field(None, description="字段数")
    row_count: Optional[int] = Field(None, description="行数")
    import_status: Optional[str] = Field(None, description="导入状态")
    last_sync_time: Optional[datetime] = Field(None, description="最后同步时间")
    last_refreshed: Optional[datetime] = Field(None, description="最后刷新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True  # 支持从ORM模型转换
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "source_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "table_name": "users",
                "schema_name": "public",
                "description": "用户信息表",
                "row_count": 1000,
                "column_count": 5,
                "created_at": "2026-01-26T10:00:00Z",
                "updated_at": "2026-01-26T10:00:00Z",
                "status": True,
                "last_refreshed": "2026-01-26T10:00:00Z"
            }
        }


class DataTableListResponse(BaseModel):
    """
    数据表列表响应模型
    包含分页信息
    """
    items: List[DataTableResponse] = Field(..., description="数据表列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页数量")
    pages: int = Field(..., ge=1, description="总页数")

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                        "source_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                        "table_name": "users",
                        "schema_name": "public",
                        "description": "用户信息表",
                        "row_count": 1000,
                        "column_count": 5,
                        "created_at": "2026-01-26T10:00:00Z",
                        "updated_at": "2026-01-26T10:00:00Z",
                        "status": True,
                        "last_refreshed": "2026-01-26T10:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "pages": 1
            }
        }


class DataTableColumnResponse(BaseModel):
    """
    数据表字段响应模型
    """
    id: str = Field(..., description="字段ID（UUID）")
    table_id: str = Field(..., description="所属数据表ID")
    field_name: str = Field(..., description="字段名")
    data_type: Optional[str] = Field(None, description="数据类型")
    is_primary_key: bool = Field(..., description="是否为主键")
    is_foreign_key: bool = Field(..., description="是否为外键")
    is_nullable: bool = Field(..., description="是否允许为空")
    description: Optional[str] = Field(None, description="字段描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True  # 支持从ORM模型转换
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "table_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "field_name": "id",
                "data_type": "INT",
                "is_primary_key": True,
                "is_foreign_key": False,
                "is_nullable": False,
                "description": "主键",
                "created_at": "2026-01-26T10:00:00Z",
                "updated_at": "2026-01-26T10:00:00Z"
            }
        }


class DataTableColumnCreate(BaseModel):
    """
    创建数据表字段的请求模型
    """
    field_name: str = Field(..., min_length=1, max_length=255, description="字段名")
    data_type: Optional[str] = Field(None, description="数据类型")
    is_primary_key: bool = Field(False, description="是否为主键")
    is_foreign_key: bool = Field(False, description="是否为外键")
    is_nullable: bool = Field(True, description="是否允许为空")
    description: Optional[str] = Field(None, description="字段描述")

    class Config:
        schema_extra = {
            "example": {
                "field_name": "id",
                "data_type": "INT",
                "is_primary_key": True,
                "is_foreign_key": False,
                "is_nullable": False,
                "description": "主键"
            }
        }


class DataTableColumnUpdate(BaseModel):
    """
    更新数据表字段的请求模型
    """
    field_name: Optional[str] = Field(None, min_length=1, max_length=255, description="字段名")
    data_type: Optional[str] = Field(None, description="数据类型")
    is_primary_key: Optional[bool] = Field(None, description="是否为主键")
    is_foreign_key: Optional[bool] = Field(None, description="是否为外键")
    is_nullable: Optional[bool] = Field(None, description="是否允许为空")
    description: Optional[str] = Field(None, description="字段描述")

    class Config:
        schema_extra = {
            "example": {
                "field_name": "id",
                "description": "主键"
            }
        }


class TableFieldResponse(BaseModel):
    """
    表字段响应模型
    """
    id: str = Field(..., description="字段ID")
    table_id: str = Field(..., description="所属表ID")
    field_name: str = Field(..., description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: str = Field(..., description="数据类型")
    description: Optional[str] = Field(None, description="字段描述")
    is_primary_key: bool = Field(False, description="是否主键")
    is_nullable: bool = Field(True, description="是否可为空")
    default_value: Optional[str] = Field(None, description="默认值")
    dictionary_id: Optional[str] = Field(None, description="关联字典ID")
    is_queryable: bool = Field(True, description="是否可查询")
    is_aggregatable: bool = Field(False, description="是否可聚合")
    sort_order: int = Field(0, description="排序顺序")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class TableFieldUpdate(BaseModel):
    """
    表字段更新模型
    """
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="字段描述")
    dictionary_id: Optional[str] = Field(None, description="关联字典ID")
    is_queryable: Optional[bool] = Field(None, description="是否可查询")
    is_aggregatable: Optional[bool] = Field(None, description="是否可聚合")
    sort_order: Optional[int] = Field(None, description="排序顺序")

    class Config:
        schema_extra = {
            "example": {
                "display_name": "用户ID",
                "description": "用户唯一标识",
                "is_queryable": True,
                "is_aggregatable": False,
                "sort_order": 1
            }
        }


# ========== 增强的响应模型（用于表详情 API）==========

class DictionaryItemSimple(BaseModel):
    """
    简化的字典项模型（用于字段详情）
    """
    item_key: str = Field(..., description="字典项键")
    item_value: str = Field(..., description="字典项值")
    description: Optional[str] = Field(None, description="描述")

    class Config:
        from_attributes = True


class DictionarySimple(BaseModel):
    """
    简化的字典模型（用于字段详情）
    """
    id: str = Field(..., description="字典ID")
    code: str = Field(..., description="字典编码")
    name: str = Field(..., description="字典名称")
    items: List[DictionaryItemSimple] = Field(default_factory=list, description="字典项列表")

    class Config:
        from_attributes = True


class FieldWithDictionaryResponse(BaseModel):
    """
    包含数据字典信息的字段响应模型
    """
    id: str = Field(..., description="字段ID")
    table_id: str = Field(..., description="所属表ID")
    field_name: str = Field(..., description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: str = Field(..., description="数据类型")
    description: Optional[str] = Field(None, description="字段描述")
    is_primary_key: bool = Field(False, description="是否主键")
    is_nullable: bool = Field(True, description="是否可为空")
    default_value: Optional[str] = Field(None, description="默认值")
    dictionary_id: Optional[str] = Field(None, description="关联字典ID")
    dictionary: Optional[DictionarySimple] = Field(None, description="关联的数据字典详情")
    is_queryable: bool = Field(True, description="是否可查询")
    is_aggregatable: bool = Field(False, description="是否可聚合")
    sort_order: int = Field(0, description="排序顺序")

    class Config:
        from_attributes = True


class TableRelationResponse(BaseModel):
    """
    表关联关系响应模型
    """
    id: str = Field(..., description="关联ID")
    relation_name: str = Field(..., description="关联名称")
    primary_table_id: str = Field(..., description="主表ID")
    primary_table_name: str = Field(..., description="主表名称")
    primary_field_id: str = Field(..., description="主表字段ID")
    primary_field_name: str = Field(..., description="主表字段名称")
    foreign_table_id: str = Field(..., description="外键表ID")
    foreign_table_name: str = Field(..., description="外键表名称")
    foreign_field_id: str = Field(..., description="外键字段ID")
    foreign_field_name: str = Field(..., description="外键字段名称")
    join_type: str = Field(..., description="连接类型：INNER/LEFT/RIGHT/FULL")
    description: Optional[str] = Field(None, description="关联描述")
    status: bool = Field(True, description="是否启用")

    class Config:
        from_attributes = True


class DataTableDetailResponse(BaseModel):
    """
    数据表详情响应模型（包含字段和关联关系）
    """
    id: str = Field(..., description="数据表ID")
    data_source_id: str = Field(..., description="所属数据源ID")
    table_name: str = Field(..., description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="表描述")
    data_mode: Optional[str] = Field(None, description="数据模式")
    status: bool = Field(..., description="是否启用")
    field_count: Optional[int] = Field(None, description="字段数")
    row_count: Optional[int] = Field(None, description="行数")
    fields: List[FieldWithDictionaryResponse] = Field(default_factory=list, description="字段列表（包含数据字典）")
    relations: List[TableRelationResponse] = Field(default_factory=list, description="表关联关系列表")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "table-uuid",
                "data_source_id": "source-uuid",
                "table_name": "orders",
                "description": "订单表",
                "status": True,
                "field_count": 5,
                "row_count": 1000,
                "fields": [
                    {
                        "id": "field-uuid",
                        "field_name": "status",
                        "description": "订单状态",
                        "data_type": "VARCHAR",
                        "dictionary_id": "dict-uuid",
                        "dictionary": {
                            "id": "dict-uuid",
                            "code": "order_status",
                            "name": "订单状态字典",
                            "items": [
                                {"item_key": "pending", "item_value": "待处理"},
                                {"item_key": "completed", "item_value": "已完成"}
                            ]
                        }
                    }
                ],
                "relations": [
                    {
                        "id": "relation-uuid",
                        "relation_name": "订单-客户关联",
                        "primary_table_name": "orders",
                        "primary_field_name": "customer_id",
                        "foreign_table_name": "customers",
                        "foreign_field_name": "id",
                        "join_type": "LEFT"
                    }
                ]
            }
        }
