"""
字段映射相关的 Pydantic 模式
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FieldMappingCreate(BaseModel):
    """创建字段映射的请求模式"""
    table_id: str = Field(..., description="数据表ID")
    field_id: str = Field(..., description="字段ID")
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    business_name: str = Field(..., description="业务名称")
    business_meaning: Optional[str] = Field(None, description="业务含义")
    value_range: Optional[str] = Field(None, description="取值范围")
    is_required: bool = Field(default=False, description="是否必填")
    default_value: Optional[str] = Field(None, description="默认值")


class FieldMappingUpdate(BaseModel):
    """更新字段映射的请求模式"""
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    business_name: Optional[str] = Field(None, description="业务名称")
    business_meaning: Optional[str] = Field(None, description="业务含义")
    value_range: Optional[str] = Field(None, description="取值范围")
    is_required: Optional[bool] = Field(None, description="是否必填")
    default_value: Optional[str] = Field(None, description="默认值")


class FieldMappingResponse(BaseModel):
    """字段映射的响应模式"""
    id: str = Field(..., description="映射ID")
    table_id: str = Field(..., description="数据表ID")
    field_id: str = Field(..., description="字段ID")
    field_name: str = Field(..., description="字段名称")
    field_type: str = Field(..., description="字段类型")
    dictionary_id: Optional[str] = Field(None, description="字典ID")
    dictionary_name: Optional[str] = Field(None, description="字典名称")
    business_name: str = Field(..., description="业务名称")
    business_meaning: Optional[str] = Field(None, description="业务含义")
    value_range: Optional[str] = Field(None, description="取值范围")
    is_required: bool = Field(..., description="是否必填")
    default_value: Optional[str] = Field(None, description="默认值")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class FieldMappingListResponse(BaseModel):
    """字段映射列表响应模式"""
    items: List[FieldMappingResponse] = Field(..., description="映射列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")


class BatchFieldMappingCreate(BaseModel):
    """批量创建字段映射的请求模式"""
    table_id: str = Field(..., description="数据表ID")
    mappings: List[dict] = Field(..., description="映射列表")


class BatchFieldMappingUpdate(BaseModel):
    """批量更新字段映射的请求模式"""
    mappings: List[dict] = Field(..., description="映射更新列表")


class FieldMappingImportRequest(BaseModel):
    """字段映射导入请求模式"""
    table_id: str = Field(..., description="数据表ID")
    import_mode: str = Field(default="merge", description="导入模式: merge(合并) 或 replace(替换)")


class FieldMappingExportRequest(BaseModel):
    """字段映射导出请求模式"""
    table_id: str = Field(..., description="数据表ID")
    export_format: str = Field(default="excel", description="导出格式: excel 或 csv")


class BatchOperationResponse(BaseModel):
    """批量操作响应模式"""
    success_count: int = Field(..., description="成功处理的数量")
    error_count: int = Field(..., description="失败处理的数量")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")