from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

# 数据模式枚举
class DataMode(str, Enum):
    DIRECT_QUERY = "DIRECT_QUERY"
    IMPORT = "IMPORT"

# 导入状态枚举
class ImportStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

# 连接类型枚举
class JoinType(str, Enum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"

# 数据表创建请求模型
class DataTableCreate(BaseModel):
    """创建数据表请求模型"""
    data_source_id: str = Field(..., description="数据源ID")
    table_name: str = Field(..., description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    data_mode: DataMode = Field(..., description="数据模式：DIRECT_QUERY或IMPORT")
    status: Optional[bool] = Field(True, description="是否启用")
    created_by: str = Field(..., description="创建人")

# 数据表更新请求模型
class DataTableUpdate(BaseModel):
    """更新数据表请求模型"""
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    table_name: Optional[str] = Field(None, description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    data_mode: Optional[DataMode] = Field(None, description="数据模式：DIRECT_QUERY或IMPORT")
    status: Optional[bool] = Field(None, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建人")

# 数据表响应模型
class DataTableResponse(BaseModel):
    """数据表响应模型"""
    id: str = Field(..., description="数据表ID（UUID）")
    data_source_id: str = Field(..., description="数据源ID")
    table_name: str = Field(..., description="表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    data_mode: DataMode = Field(..., description="数据模式：DIRECT_QUERY或IMPORT")
    status: bool = Field(..., description="是否启用")
    field_count: Optional[int] = Field(None, description="字段数量")
    row_count: Optional[int] = Field(None, description="行数")
    import_status: Optional[ImportStatus] = Field(None, description="导入状态")
    last_sync_time: Optional[str] = Field(None, description="最后同步时间")
    created_by: str = Field(..., description="创建人")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'data_source_id': obj.data_source_id,
            'table_name': obj.table_name,
            'display_name': obj.display_name,
            'description': obj.description,
            'data_mode': obj.data_mode,
            'status': obj.status,
            'field_count': obj.field_count,
            'row_count': obj.row_count,
            'import_status': obj.import_status,
            'last_sync_time': obj.last_sync_time.isoformat() if obj.last_sync_time else None,
            'created_by': obj.created_by,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 字段创建请求模型
class TableFieldCreate(BaseModel):
    """创建表字段请求模型"""
    table_id: str = Field(..., description="数据表ID")
    field_name: str = Field(..., description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: str = Field(..., description="数据类型")
    description: Optional[str] = Field(None, description="描述")
    is_primary_key: Optional[bool] = Field(False, description="是否为主键")
    is_nullable: Optional[bool] = Field(True, description="是否允许为空")
    default_value: Optional[str] = Field(None, description="默认值")
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    is_queryable: Optional[bool] = Field(True, description="是否可查询")
    is_aggregatable: Optional[bool] = Field(True, description="是否可聚合")
    sort_order: Optional[int] = Field(0, description="排序顺序")

# 字段更新请求模型
class TableFieldUpdate(BaseModel):
    """更新表字段请求模型"""
    table_id: Optional[str] = Field(None, description="数据表ID")
    field_name: Optional[str] = Field(None, description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: Optional[str] = Field(None, description="数据类型")
    description: Optional[str] = Field(None, description="描述")
    is_primary_key: Optional[bool] = Field(None, description="是否为主键")
    is_nullable: Optional[bool] = Field(None, description="是否允许为空")
    default_value: Optional[str] = Field(None, description="默认值")
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    is_queryable: Optional[bool] = Field(None, description="是否可查询")
    is_aggregatable: Optional[bool] = Field(None, description="是否可聚合")
    sort_order: Optional[int] = Field(None, description="排序顺序")

# 字段响应模型
class TableFieldResponse(BaseModel):
    """表字段响应模型"""
    id: str = Field(..., description="字段ID（UUID）")
    table_id: str = Field(..., description="数据表ID")
    field_name: str = Field(..., description="字段名")
    display_name: Optional[str] = Field(None, description="显示名称")
    data_type: str = Field(..., description="数据类型")
    description: Optional[str] = Field(None, description="描述")
    is_primary_key: bool = Field(..., description="是否为主键")
    is_nullable: bool = Field(..., description="是否允许为空")
    default_value: Optional[str] = Field(None, description="默认值")
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    is_queryable: bool = Field(..., description="是否可查询")
    is_aggregatable: bool = Field(..., description="是否可聚合")
    sort_order: int = Field(..., description="排序顺序")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'table_id': obj.table_id,
            'field_name': obj.field_name,
            'display_name': obj.display_name,
            'data_type': obj.data_type,
            'description': obj.description,
            'is_primary_key': obj.is_primary_key,
            'is_nullable': obj.is_nullable,
            'default_value': obj.default_value,
            'dictionary_id': obj.dictionary_id,
            'is_queryable': obj.is_queryable,
            'is_aggregatable': obj.is_aggregatable,
            'sort_order': obj.sort_order,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 字典创建请求模型
class DictionaryCreate(BaseModel):
    """创建字典请求模型"""
    code: str = Field(..., description="字典编码")
    name: str = Field(..., description="字典名称")
    parent_id: Optional[str] = Field(None, description="父字典ID")
    description: Optional[str] = Field(None, description="描述")
    dict_type: Optional[str] = Field(None, description="字典类型")
    status: Optional[bool] = Field(True, description="是否启用")
    sort_order: Optional[int] = Field(0, description="排序顺序")
    created_by: str = Field(..., description="创建人")

# 字典更新请求模型
class DictionaryUpdate(BaseModel):
    """更新字典请求模型"""
    code: Optional[str] = Field(None, description="字典编码")
    name: Optional[str] = Field(None, description="字典名称")
    parent_id: Optional[str] = Field(None, description="父字典ID")
    description: Optional[str] = Field(None, description="描述")
    dict_type: Optional[str] = Field(None, description="字典类型")
    status: Optional[bool] = Field(None, description="是否启用")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    created_by: Optional[str] = Field(None, description="创建人")

# 字典响应模型
class DictionaryResponse(BaseModel):
    """字典响应模型"""
    id: str = Field(..., description="字典ID（UUID）")
    code: str = Field(..., description="字典编码")
    name: str = Field(..., description="字典名称")
    parent_id: Optional[str] = Field(None, description="父字典ID")
    description: Optional[str] = Field(None, description="描述")
    dict_type: Optional[str] = Field(None, description="字典类型")
    status: bool = Field(..., description="是否启用")
    sort_order: int = Field(..., description="排序顺序")
    created_by: str = Field(..., description="创建人")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'code': obj.code,
            'name': obj.name,
            'parent_id': obj.parent_id,
            'description': obj.description,
            'dict_type': obj.dict_type,
            'status': obj.status,
            'sort_order': obj.sort_order,
            'created_by': obj.created_by,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 字典项创建请求模型
class DictionaryItemCreate(BaseModel):
    """创建字典项请求模型"""
    dictionary_id: str = Field(..., description="字典ID")
    item_key: str = Field(..., description="键值")
    item_value: str = Field(..., description="值")
    description: Optional[str] = Field(None, description="描述")
    sort_order: Optional[int] = Field(0, description="排序顺序")
    status: Optional[bool] = Field(True, description="是否启用")
    extra_data: Optional[dict] = Field(None, description="额外数据")

# 字典项更新请求模型
class DictionaryItemUpdate(BaseModel):
    """更新字典项请求模型"""
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    item_key: Optional[str] = Field(None, description="键值")
    item_value: Optional[str] = Field(None, description="值")
    description: Optional[str] = Field(None, description="描述")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    status: Optional[bool] = Field(None, description="是否启用")
    extra_data: Optional[dict] = Field(None, description="额外数据")

# 字典项响应模型
class DictionaryItemResponse(BaseModel):
    """字典项响应模型"""
    id: str = Field(..., description="字典项ID（UUID）")
    dictionary_id: str = Field(..., description="字典ID")
    item_key: str = Field(..., description="键值")
    item_value: str = Field(..., description="值")
    description: Optional[str] = Field(None, description="描述")
    sort_order: int = Field(..., description="排序顺序")
    status: bool = Field(..., description="是否启用")
    extra_data: Optional[dict] = Field(None, description="额外数据")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'dictionary_id': obj.dictionary_id,
            'item_key': obj.item_key,
            'item_value': obj.item_value,
            'description': obj.description,
            'sort_order': obj.sort_order,
            'status': obj.status,
            'extra_data': obj.extra_data,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 批量添加字典项请求模型
class DictionaryItemBatchCreate(BaseModel):
    """批量添加字典项请求模型"""
    items: List[DictionaryItemCreate] = Field(..., description="字典项列表，至少包含一个字典项")
    
    @validator('items')
    def check_items_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError('字典项列表不能为空')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "item_key": "status_active",
                        "item_value": "激活",
                        "description": "账户激活状态",
                        "sort_order": 1,
                        "status": True
                    },
                    {
                        "item_key": "status_inactive",
                        "item_value": "未激活",
                        "description": "账户未激活状态",
                        "sort_order": 2,
                        "status": True
                    }
                ]
            }
        }

# 批量添加字典项响应模型
class DictionaryItemBatchResponse(BaseModel):
    """批量添加字典项响应模型"""
    success_count: int = Field(..., description="成功添加的字典项数量")
    failed_count: int = Field(..., description="失败的字典项数量")
    failed_items: List[dict] = Field(..., description="失败的字典项详情，包含错误信息")
    total_processed: int = Field(..., description="总共处理的字典项数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 2,
                "failed_count": 0,
                "failed_items": [],
                "total_processed": 2
            }
        }

# 动态字典配置创建请求模型
class DynamicDictionaryConfigCreate(BaseModel):
    """创建动态字典配置请求模型"""
    dictionary_id: str = Field(..., description="字典ID")
    data_source_id: str = Field(..., description="数据源ID")
    sql_query: str = Field(..., description="SQL查询语句")
    key_field: str = Field(..., description="键字段名")
    value_field: str = Field(..., description="值字段名")
    refresh_interval: Optional[int] = Field(3600, description="刷新间隔（秒）")

# 动态字典配置更新请求模型
class DynamicDictionaryConfigUpdate(BaseModel):
    """更新动态字典配置请求模型"""
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    sql_query: Optional[str] = Field(None, description="SQL查询语句")
    key_field: Optional[str] = Field(None, description="键字段名")
    value_field: Optional[str] = Field(None, description="值字段名")
    refresh_interval: Optional[int] = Field(None, description="刷新间隔（秒）")

# 动态字典配置响应模型
class DynamicDictionaryConfigResponse(BaseModel):
    """动态字典配置响应模型"""
    id: str = Field(..., description="动态字典配置ID（UUID）")
    dictionary_id: str = Field(..., description="字典ID")
    data_source_id: str = Field(..., description="数据源ID")
    sql_query: str = Field(..., description="SQL查询语句")
    key_field: str = Field(..., description="键字段名")
    value_field: str = Field(..., description="值字段名")
    refresh_interval: int = Field(..., description="刷新间隔（秒）")
    last_refresh_time: Optional[str] = Field(None, description="最后刷新时间")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'dictionary_id': obj.dictionary_id,
            'data_source_id': obj.data_source_id,
            'sql_query': obj.sql_query,
            'key_field': obj.key_field,
            'value_field': obj.value_field,
            'refresh_interval': obj.refresh_interval,
            'last_refresh_time': obj.last_refresh_time.isoformat() if obj.last_refresh_time else None,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 表关联创建请求模型
class TableRelationCreate(BaseModel):
    """创建表关联请求模型"""
    relation_name: str = Field(..., description="关联名称")
    primary_table_id: str = Field(..., description="主表ID")
    primary_field_id: str = Field(..., description="主表字段ID")
    foreign_table_id: str = Field(..., description="外键表ID")
    foreign_field_id: str = Field(..., description="外键字段ID")
    join_type: JoinType = Field(..., description="连接类型：INNER、LEFT、RIGHT、FULL")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[bool] = Field(True, description="是否启用")
    created_by: str = Field(..., description="创建人")

# 表关联更新请求模型
class TableRelationUpdate(BaseModel):
    """更新表关联请求模型"""
    relation_name: Optional[str] = Field(None, description="关联名称")
    primary_table_id: Optional[str] = Field(None, description="主表ID")
    primary_field_id: Optional[str] = Field(None, description="主表字段ID")
    foreign_table_id: Optional[str] = Field(None, description="外键表ID")
    foreign_field_id: Optional[str] = Field(None, description="外键字段ID")
    join_type: Optional[JoinType] = Field(None, description="连接类型：INNER、LEFT、RIGHT、FULL")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[bool] = Field(None, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建人")

# 表关联响应模型
class TableRelationResponse(BaseModel):
    """表关联响应模型"""
    id: str = Field(..., description="关联ID（UUID）")
    relation_name: str = Field(..., description="关联名称")
    primary_table_id: str = Field(..., description="主表ID")
    primary_field_id: str = Field(..., description="主表字段ID")
    foreign_table_id: str = Field(..., description="外键表ID")
    foreign_field_id: str = Field(..., description="外键字段ID")
    join_type: JoinType = Field(..., description="连接类型：INNER、LEFT、RIGHT、FULL")
    description: Optional[str] = Field(None, description="描述")
    status: bool = Field(..., description="是否启用")
    created_by: str = Field(..., description="创建人")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'relation_name': obj.relation_name,
            'primary_table_id': obj.primary_table_id,
            'primary_field_id': obj.primary_field_id,
            'foreign_table_id': obj.foreign_table_id,
            'foreign_field_id': obj.foreign_field_id,
            'join_type': obj.join_type,
            'description': obj.description,
            'status': obj.status,
            'created_by': obj.created_by,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)