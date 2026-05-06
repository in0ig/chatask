"""
字典版本管理服务
实现字典版本的创建、比较、回滚等功能
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from src.models.data_preparation_model import Dictionary, DictionaryVersion, DictionaryVersionItem, DictionaryItem
from src.schemas.dictionary_version_schema import (
    DictionaryVersionCreate,
    CreateVersionFromCurrentRequest,
    VersionCompareRequest,
    VersionRollbackRequest,
    DictionaryVersionResponse,
    VersionCompareResponse,
    VersionRollbackResponse,
    DictionaryItemChange
)


class DictionaryVersionService:
    """
    字典版本管理服务类
    提供字典版本的创建、比较、回滚等操作
    """

    def __init__(self, db: Session):
        self.db = db

    def create_version_from_current(self, request: CreateVersionFromCurrentRequest) -> DictionaryVersionResponse:
        """
        从当前字典状态创建版本
        """
        # 验证字典是否存在
        dictionary = self.db.query(Dictionary).filter(
            Dictionary.id == request.dictionary_id
        ).first()
        if not dictionary:
            raise ValueError(f"字典不存在: {request.dictionary_id}")

        # 获取当前字典的所有项
        current_items = self.db.query(DictionaryItem).filter(
            DictionaryItem.dictionary_id == request.dictionary_id
        ).all()

        # 计算下一个版本号
        latest_version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.dictionary_id == request.dictionary_id
        ).order_by(DictionaryVersion.version_number.desc()).first()

        version_number = 1
        if latest_version:
            version_number = latest_version.version_number + 1

        # 创建新版本
        new_version = DictionaryVersion(
            dictionary_id=request.dictionary_id,
            version_number=version_number,
            version_name=request.version_name,
            description=request.description,
            change_type='created',
            change_summary=request.change_summary or f"从当前状态创建版本 {version_number}",
            created_by="system",  # 在实际应用中应使用当前用户ID
            items_count=len(current_items),
            is_current=True
        )
        self.db.add(new_version)
        self.db.flush()  # 获取新版本的ID

        # 创建版本项
        for item in current_items:
            version_item = DictionaryVersionItem(
                version_id=new_version.id,
                dictionary_id=item.dictionary_id,
                item_key=item.item_key,
                item_value=item.item_value,
                description=item.description,
                sort_order=item.sort_order,
                status=item.status,
                extra_data=item.extra_data,
                change_type='added'
            )
            self.db.add(version_item)

        # 将之前的当前版本设置为非当前版本
        if latest_version:
            latest_version.is_current = False

        self.db.commit()
        self.db.refresh(new_version)

        return DictionaryVersionResponse(
            id=new_version.id,
            dictionary_id=new_version.dictionary_id,
            version_number=new_version.version_number,
            version_name=new_version.version_name,
            description=new_version.description,
            change_type=new_version.change_type,
            change_summary=new_version.change_summary,
            created_by=new_version.created_by,
            created_at=new_version.created_at,
            is_current=new_version.is_current,
            items_count=new_version.items_count
        )

    def get_version_list(self, dictionary_id: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        获取字典版本列表
        """
        # 验证字典是否存在
        dictionary = self.db.query(Dictionary).filter(
            Dictionary.id == dictionary_id
        ).first()
        if not dictionary:
            raise ValueError(f"字典不存在: {dictionary_id}")

        # 获取版本列表
        query = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.dictionary_id == dictionary_id
        ).order_by(DictionaryVersion.version_number.desc())

        total = query.count()
        versions = query.offset((page - 1) * page_size).limit(page_size).all()

        items = [
            DictionaryVersionResponse(
                id=version.id,
                dictionary_id=version.dictionary_id,
                version_number=version.version_number,
                version_name=version.version_name,
                description=version.description,
                change_type=version.change_type,
                change_summary=version.change_summary,
                created_by=version.created_by,
                created_at=version.created_at,
                is_current=version.is_current,
                items_count=version.items_count
            )
            for version in versions
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def get_version_detail(self, version_id: str) -> Dict[str, Any]:
        """
        获取版本详情
        """
        version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.id == version_id
        ).first()
        if not version:
            raise ValueError(f"版本不存在: {version_id}")

        # 获取版本项
        items = self.db.query(DictionaryVersionItem).filter(
            DictionaryVersionItem.version_id == version_id
        ).all()

        # 获取字典信息
        dictionary = self.db.query(Dictionary).filter(
            Dictionary.id == version.dictionary_id
        ).first()

        # 计算统计信息
        total_versions = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.dictionary_id == version.dictionary_id
        ).count()
        current_version_number = version.version_number if version.is_current else None
        latest_change_time = self.db.query(func.max(DictionaryVersion.created_at)).filter(
            DictionaryVersion.dictionary_id == version.dictionary_id
        ).scalar()

        # 统计变更类型频率
        change_frequency = {}
        for change_type in ['created', 'updated', 'deleted', 'restored', 'rollback']:
            count = self.db.query(DictionaryVersion).filter(
                DictionaryVersion.dictionary_id == version.dictionary_id,
                DictionaryVersion.change_type == change_type
            ).count()
            if count > 0:
                change_frequency[change_type] = count

        return {
            "version_info": DictionaryVersionResponse(
                id=version.id,
                dictionary_id=version.dictionary_id,
                version_number=version.version_number,
                version_name=version.version_name,
                description=version.description,
                change_type=version.change_type,
                change_summary=version.change_summary,
                created_by=version.created_by,
                created_at=version.created_at,
                is_current=version.is_current,
                items_count=version.items_count
            ),
            "items": [
                {
                    "id": item.id,
                    "item_key": item.item_key,
                    "item_value": item.item_value,
                    "description": item.description,
                    "sort_order": item.sort_order,
                    "status": item.status,
                    "extra_data": item.extra_data,
                    "change_type": item.change_type,
                    "created_at": item.created_at.isoformat() if item.created_at else None
                }
                for item in items
            ],
            "statistics": {
                "total_versions": total_versions,
                "current_version_number": current_version_number,
                "latest_change_time": latest_change_time,
                "change_frequency": change_frequency
            }
        }

    def compare_versions(self, request: VersionCompareRequest) -> VersionCompareResponse:
        """
        比较两个版本的差异
        """
        # 验证版本是否存在
        source_version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.id == request.source_version_id
        ).first()
        if not source_version:
            raise ValueError(f"源版本不存在: {request.source_version_id}")

        target_version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.id == request.target_version_id
        ).first()
        if not target_version:
            raise ValueError(f"目标版本不存在: {request.target_version_id}")

        # 验证两个版本属于同一个字典
        if source_version.dictionary_id != target_version.dictionary_id:
            raise ValueError("比较的版本必须属于同一个字典")

        # 获取源版本的项
        source_items = self.db.query(DictionaryVersionItem).filter(
            DictionaryVersionItem.version_id == request.source_version_id
        ).all()
        source_items_dict = {item.item_key: item for item in source_items}

        # 获取目标版本的项
        target_items = self.db.query(DictionaryVersionItem).filter(
            DictionaryVersionItem.version_id == request.target_version_id
        ).all()
        target_items_dict = {item.item_key: item for item in target_items}

        # 计算差异
        changes = []
        added_count = 0
        updated_count = 0
        deleted_count = 0

        # 检查新增的项
        for key, item in target_items_dict.items():
            if key not in source_items_dict:
                changes.append(
                    DictionaryItemChange(
                        item_key=key,
                        change_type="added",
                        old_value=None,
                        new_value=item.item_value
                    )
                )
                added_count += 1

        # 检查删除的项
        for key, item in source_items_dict.items():
            if key not in target_items_dict:
                changes.append(
                    DictionaryItemChange(
                        item_key=key,
                        change_type="deleted",
                        old_value=item.item_value,
                        new_value=None
                    )
                )
                deleted_count += 1

        # 检查更新的项
        for key, item in source_items_dict.items():
            if key in target_items_dict:
                target_item = target_items_dict[key]
                if item.item_value != target_item.item_value or \
                   item.description != target_item.description or \
                   item.sort_order != target_item.sort_order or \
                   item.status != target_item.status or \
                   item.extra_data != target_item.extra_data:
                    changes.append(
                        DictionaryItemChange(
                            item_key=key,
                            change_type="updated",
                            old_value=item.item_value,
                            new_value=target_item.item_value
                        )
                    )
                    updated_count += 1

        # 排序变更列表
        changes.sort(key=lambda x: x.item_key)

        return VersionCompareResponse(
            dictionary_id=request.dictionary_id,
            source_version=DictionaryVersionResponse(
                id=source_version.id,
                dictionary_id=source_version.dictionary_id,
                version_number=source_version.version_number,
                version_name=source_version.version_name,
                description=source_version.description,
                change_type=source_version.change_type,
                change_summary=source_version.change_summary,
                created_by=source_version.created_by,
                created_at=source_version.created_at,
                is_current=source_version.is_current,
                items_count=source_version.items_count
            ),
            target_version=DictionaryVersionResponse(
                id=target_version.id,
                dictionary_id=target_version.dictionary_id,
                version_number=target_version.version_number,
                version_name=target_version.version_name,
                description=target_version.description,
                change_type=target_version.change_type,
                change_summary=target_version.change_summary,
                created_by=target_version.created_by,
                created_at=target_version.created_at,
                is_current=target_version.is_current,
                items_count=target_version.items_count
            ),
            changes=changes,
            summary={
                "added": added_count,
                "updated": updated_count,
                "deleted": deleted_count
            }
        )

    def rollback_version(self, request: VersionRollbackRequest) -> VersionRollbackResponse:
        """
        回滚到指定版本
        """
        # 验证目标版本是否存在
        target_version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.id == request.target_version_id
        ).first()
        if not target_version:
            raise ValueError(f"目标版本不存在: {request.target_version_id}")

        # 验证字典是否存在
        dictionary = self.db.query(Dictionary).filter(
            Dictionary.id == target_version.dictionary_id
        ).first()
        if not dictionary:
            raise ValueError(f"字典不存在: {target_version.dictionary_id}")

        # 获取目标版本的项
        target_items = self.db.query(DictionaryVersionItem).filter(
            DictionaryVersionItem.version_id == request.target_version_id
        ).all()

        # 获取当前版本（如果存在）
        current_version = self.db.query(DictionaryVersion).filter(
            DictionaryVersion.dictionary_id == target_version.dictionary_id,
            DictionaryVersion.is_current == True
        ).first()

        # 如果当前版本存在，将其设置为非当前版本
        if current_version:
            current_version.is_current = False

        # 创建新版本作为回滚版本
        new_version_number = target_version.version_number + 1
        new_version = DictionaryVersion(
            dictionary_id=target_version.dictionary_id,
            version_number=new_version_number,
            version_name=request.version_name,
            description=request.description or f"回滚到版本 {target_version.version_number}",
            change_type='rollback',
            change_summary=request.change_summary or f"回滚到版本 {target_version.version_number}",
            created_by="system",  # 在实际应用中应使用当前用户ID
            items_count=len(target_items),
            is_current=True
        )
        self.db.add(new_version)
        self.db.flush()  # 获取新版本的ID

        # 创建新版本的项
        for item in target_items:
            version_item = DictionaryVersionItem(
                version_id=new_version.id,
                dictionary_id=item.dictionary_id,
                item_key=item.item_key,
                item_value=item.item_value,
                description=item.description,
                sort_order=item.sort_order,
                status=item.status,
                extra_data=item.extra_data,
                change_type='restored'
            )
            self.db.add(version_item)

        # 删除当前字典中的所有项
        self.db.query(DictionaryItem).filter(
            DictionaryItem.dictionary_id == target_version.dictionary_id
        ).delete()

        # 将目标版本的项添加到当前字典
        for item in target_items:
            dict_item = DictionaryItem(
                dictionary_id=item.dictionary_id,
                item_key=item.item_key,
                item_value=item.item_value,
                description=item.description,
                sort_order=item.sort_order,
                status=item.status,
                extra_data=item.extra_data
            )
            self.db.add(dict_item)

        self.db.commit()
        self.db.refresh(new_version)

        return VersionRollbackResponse(
            success=True,
            message=f"成功回滚到版本 {target_version.version_number}",
            new_version=DictionaryVersionResponse(
                id=new_version.id,
                dictionary_id=new_version.dictionary_id,
                version_number=new_version.version_number,
                version_name=new_version.version_name,
                description=new_version.description,
                change_type=new_version.change_type,
                change_summary=new_version.change_summary,
                created_by=new_version.created_by,
                created_at=new_version.created_at,
                is_current=new_version.is_current,
                items_count=new_version.items_count
            ),
            changes_applied=len(target_items),
            rollback_time=datetime.now()
        )