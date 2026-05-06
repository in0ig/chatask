"""
字典版本管理相关的 Pydantic 模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class VersionChangeType(str, Enum):
    """版本变更类型"""
    CREATED = "created"  # 创建
    UPDATED = "updated"  # 更新
    DELETED = "deleted"  # 删除
    RESTORED = "restored"  # 恢复
    ROLLBACK = "rollback"  # 回滚


class DictionaryVersionCreate(BaseModel):
    """创建字典版本的请求模式"""
    dictionary_id: str = Field(..., description="字典ID")
    version_name: Optional[str] = Field(None, description="版本名称")
    description: Optional[str] = Field(None, description="版本描述")
    change_type: VersionChangeType = Field(..., description="变更类型")
    change_summary: Optional[str] = Field(None, description="变更摘要")


class DictionaryVersionResponse(BaseModel):
    """字典版本的响应模式"""
    id: str = Field(..., description="版本ID")
    dictionary_id: str = Field(..., description="字典ID")
    version_number: int = Field(..., description="版本号")
    version_name: Optional[str] = Field(None, description="版本名称")
    description: Optional[str] = Field(None, description="版本描述")
    change_type: VersionChangeType = Field(..., description="变更类型")
    change_summary: Optional[str] = Field(None, description="变更摘要")
    items_count: int = Field(..., description="字典项数量")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: datetime = Field(..., description="创建时间")
    is_current: bool = Field(default=False, description="是否为当前版本")

    class Config:
        from_attributes = True


class DictionaryVersionListResponse(BaseModel):
    """字典版本列表响应模式"""
    items: List[DictionaryVersionResponse] = Field(..., description="版本列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")


class VersionCompareRequest(BaseModel):
    """版本比较请求模式"""
    dictionary_id: str = Field(..., description="字典ID")
    source_version_id: str = Field(..., description="源版本ID")
    target_version_id: str = Field(..., description="目标版本ID")


class DictionaryItemChange(BaseModel):
    """字典项变更信息"""
    item_key: str = Field(..., description="字典项键")
    change_type: str = Field(..., description="变更类型: added, updated, deleted")
    old_value: Optional[str] = Field(None, description="旧值")
    new_value: Optional[str] = Field(None, description="新值")


class VersionCompareResponse(BaseModel):
    """版本比较响应模式"""
    dictionary_id: str = Field(..., description="字典ID")
    source_version: DictionaryVersionResponse = Field(..., description="源版本信息")
    target_version: DictionaryVersionResponse = Field(..., description="目标版本信息")
    changes: List[DictionaryItemChange] = Field(..., description="变更列表")
    summary: Dict[str, int] = Field(..., description="变更摘要统计")


class VersionRollbackRequest(BaseModel):
    """版本回滚请求模式"""
    dictionary_id: str = Field(..., description="字典ID")
    target_version_id: str = Field(..., description="目标版本ID")
    description: Optional[str] = Field(None, description="回滚说明")


class VersionRollbackResponse(BaseModel):
    """版本回滚响应模式"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    new_version: Optional[DictionaryVersionResponse] = Field(None, description="新创建的版本信息")
    changes_applied: int = Field(..., description="应用的变更数量")
    rollback_time: datetime = Field(..., description="回滚时间")


class VersionStatistics(BaseModel):
    """版本统计信息"""
    total_versions: int = Field(..., description="总版本数")
    current_version_number: int = Field(..., description="当前版本号")
    latest_change_time: Optional[datetime] = Field(None, description="最新变更时间")
    change_frequency: Dict[str, int] = Field(..., description="变更类型频率统计")


class DictionaryVersionDetail(BaseModel):
    """字典版本详情模式"""
    version_info: DictionaryVersionResponse = Field(..., description="版本基本信息")
    items: List[Dict[str, Any]] = Field(..., description="该版本的字典项列表")
    statistics: VersionStatistics = Field(..., description="统计信息")


class CreateVersionFromCurrentRequest(BaseModel):
    """从当前状态创建版本的请求模式"""
    dictionary_id: str = Field(..., description="字典ID")
    version_name: Optional[str] = Field(None, description="版本名称")
    description: Optional[str] = Field(None, description="版本描述")
    change_summary: Optional[str] = Field(None, description="变更摘要")