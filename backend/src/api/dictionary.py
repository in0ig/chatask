"""
字典管理API端点
实现字典的CRUD功能，支持树形结构查询和依赖检查
"""
import logging
import os
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile
from typing import List, Optional
from pydantic import ValidationError
from sqlalchemy.orm import Session
from src.models.data_preparation_model import Dictionary, DictionaryItem
from src.schemas.data_preparation_schema import (
    DictionaryCreate,
    DictionaryUpdate,
    DictionaryResponse,
    DictionaryItemCreate,
    DictionaryItemUpdate,
    DictionaryItemResponse,
    DictionaryItemBatchResponse,
    DictionaryItemBatchCreate
)
from src.services.data_preparation_service import DictionaryService
from src.database import get_db

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dictionaries", tags=["数据字典"])

dictionary_service = DictionaryService()

@router.get("/", response_model=List[DictionaryResponse])
async def get_dictionaries(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1-100"),
    search: Optional[str] = Query(None, description="搜索关键词（编码或名称）"),
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    parent_id: Optional[str] = Query(None, description="父字典ID，用于筛选"),
    db: Session = Depends(get_db)
):
    """
    获取字典列表
    
    支持分页、搜索、按状态和父字典筛选功能
    """
    logger.info(f"Retrieving dictionaries with filters - page: {page}, page_size: {page_size}, search: {search}, status: {status}, parent_id: {parent_id}")
    
    try:
        # 调用服务层获取字典列表
        logger.info(f"Calling dictionary_service.get_all_dictionaries with type: {type(dictionary_service)}")
        logger.info(f"Method exists: {hasattr(dictionary_service, 'get_all_dictionaries')}")
        
        dictionaries_result = dictionary_service.get_all_dictionaries(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            parent_id=parent_id
        )
        
        logger.info(f"Dictionary service returned: {type(dictionaries_result)}, content: {dictionaries_result}")
        if isinstance(dictionaries_result, dict) and 'items' in dictionaries_result:
            items = dictionaries_result['items']
            total = dictionaries_result['total']
            logger.info(f"Retrieved {len(items)} dictionaries out of {total} total")
            return items
        else:
            logger.error(f"Unexpected return type from dictionary service: {type(dictionaries_result)}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to retrieve dictionaries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取字典列表失败")


@router.get("/tree", response_model=List[DictionaryResponse])
async def get_dictionaries_tree(
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    db: Session = Depends(get_db)
):
    """
    获取字典树形结构
    
    返回完整的层级树结构，包含所有子字典
    """
    logger.info(f"Retrieving dictionaries tree structure with status filter: {status}")
    
    try:
        # 调用服务层获取树形结构
        tree = dictionary_service.get_dictionaries_tree(db, status=status)
        
        logger.info(f"Retrieved {len(tree)} nodes in dictionaries tree")
        return tree
        
    except Exception as e:
        logger.error(f"Failed to retrieve dictionaries tree: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取字典树形结构失败")


@router.post("/", response_model=DictionaryResponse, status_code=201)
async def create_dictionary(
    dict_data: DictionaryCreate,
    db: Session = Depends(get_db)
):
    """
    创建字典
    
    - 验证字典编码唯一性
    - 验证父字典是否存在
    - 支持所有字段的创建
    """
    logger.info(f"Creating new dictionary: {dict_data.name} (code: {dict_data.code})")
    
    try:
        # 验证字典编码是否唯一
        existing_dict = dictionary_service.get_dictionary_by_code(db, dict_data.code)
        if existing_dict:
            logger.warning(f"Dictionary with code {dict_data.code} already exists")
            raise HTTPException(
                status_code=409, 
                detail=f"字典编码已存在: {dict_data.code}"
            )
        
        # 如果指定了父字典，验证父字典是否存在
        if dict_data.parent_id:
            parent_dict = db.query(Dictionary).filter(Dictionary.id == dict_data.parent_id).first()
            if not parent_dict:
                logger.warning(f"Parent dictionary with ID {dict_data.parent_id} not found")
                raise HTTPException(
                    status_code=404, 
                    detail=f"父字典不存在: {dict_data.parent_id}"
                )
        
        # 创建字典
        db_dict = dictionary_service.create_dictionary(db, dict_data)
        
        # 转换为响应模型
        dict_dict = db_dict.to_dict()
        logger.info(f"Dictionary created successfully: {dict_data.name} (ID: {db_dict.id})")
        return DictionaryResponse(**dict_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error creating dictionary: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error creating dictionary: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create dictionary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建字典失败")


@router.get("/{dict_id}", response_model=DictionaryResponse)
async def get_dictionary_by_id(
    dict_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的字典详情
    """
    logger.info(f"Retrieving dictionary details for ID: {dict_id}")
    
    try:
        dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
        
        if not dictionary:
            logger.warning(f"Dictionary with ID {dict_id} not found")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 转换为响应模型
        dict_dict = dictionary.to_dict()
        logger.info(f"Retrieved dictionary details for ID: {dict_id}")
        return DictionaryResponse(**dict_dict)
        
    except HTTPException:
        # 重新抛出HTTP异常，不要转换为500错误
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve dictionary {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取字典详情失败")


@router.put("/{dict_id}", response_model=DictionaryResponse)
async def update_dictionary(
    dict_id: str,
    dict_data: DictionaryUpdate,
    db: Session = Depends(get_db)
):
    """
    更新字典
    
    - 支持部分更新
    - 验证字典编码唯一性（排除自身）
    - 验证父字典是否存在
    - 防止循环引用
    """
    logger.info(f"Updating dictionary {dict_id}")
    
    try:
        # 获取现有字典
        existing_dict = dictionary_service.get_dictionary_by_id(db, dict_id)
        
        if not existing_dict:
            logger.warning(f"Dictionary with ID {dict_id} not found for update")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 如果更新了字典编码，验证新编码是否唯一
        if dict_data.code and dict_data.code != existing_dict.code:
            existing_dict_with_code = dictionary_service.get_dictionary_by_code(db, dict_data.code)
            if existing_dict_with_code:
                logger.warning(f"Dictionary with code {dict_data.code} already exists")
                raise HTTPException(
                    status_code=409, 
                    detail=f"字典编码已存在: {dict_data.code}"
                )
        
        # 如果更新了父字典，验证父字典是否存在
        if dict_data.parent_id:
            parent_dict = db.query(Dictionary).filter(Dictionary.id == dict_data.parent_id).first()
            if not parent_dict:
                logger.warning(f"Parent dictionary with ID {dict_data.parent_id} not found")
                raise HTTPException(
                    status_code=404, 
                    detail=f"父字典不存在: {dict_data.parent_id}"
                )
            
            # 检查是否会造成循环引用
            if dict_data.parent_id == dict_id:
                logger.warning(f"Cannot set dictionary {dict_id} as its own parent")
                raise HTTPException(
                    status_code=400, 
                    detail="不能将字典设置为自身的父字典"
                )
            
            # 检查是否会造成循环引用（递归检查）
            if dictionary_service.is_ancestor(db, dict_data.parent_id, dict_id):
                logger.warning(f"Setting {dict_data.parent_id} as parent of {dict_id} would create a circular reference")
                raise HTTPException(
                    status_code=400, 
                    detail="设置父字典会导致循环引用"
                )
        
        # 更新字典
        db_dict = dictionary_service.update_dictionary(db, dict_id, dict_data)
        
        # 转换为响应模型
        dict_dict = db_dict.to_dict()
        logger.info(f"Dictionary {dict_id} updated successfully")
        return DictionaryResponse(**dict_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error updating dictionary: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error updating dictionary: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update dictionary {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新字典失败")


@router.delete("/{dict_id}", status_code=204)
async def delete_dictionary(
    dict_id: str,
    db: Session = Depends(get_db)
):
    """
    删除字典
    
    - 检查是否有子字典
    - 检查是否有字段引用
    - 检查是否有动态字典配置
    - 有依赖时返回错误提示
    """
    logger.info(f"Attempting to delete dictionary with ID: {dict_id}")
    
    try:
        # 检查是否有子字典
        has_children = dictionary_service.has_children(db, dict_id)
        if has_children:
            logger.warning(f"Cannot delete dictionary {dict_id}: has child dictionaries")
            raise HTTPException(
                status_code=400, 
                detail="该字典有子字典，无法删除。请先删除所有子字典。"
            )
        
        # 检查是否有字段引用
        has_field_references = dictionary_service.has_field_references(db, dict_id)
        if has_field_references:
            logger.warning(f"Cannot delete dictionary {dict_id}: has field references")
            raise HTTPException(
                status_code=400, 
                detail="该字典被字段引用，无法删除。请先移除相关字段的字典引用。"
            )
        
        # 检查是否有动态字典配置
        has_dynamic_configs = dictionary_service.has_dynamic_configs(db, dict_id)
        if has_dynamic_configs:
            logger.warning(f"Cannot delete dictionary {dict_id}: has dynamic configurations")
            raise HTTPException(
                status_code=400, 
                detail="该字典有关联的动态字典配置，无法删除。请先删除相关动态配置。"
            )
        
        # 删除字典
        success = dictionary_service.delete_dictionary(db, dict_id)
        
        if not success:
            logger.warning(f"Dictionary with ID {dict_id} not found for deletion")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        logger.info(f"Dictionary {dict_id} deleted successfully")
        
    except HTTPException:
        # Re-raise HTTP exceptions without converting to 500
        raise
    except Exception as e:
        logger.error(f"Failed to delete dictionary {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除字典失败")


# 新增：获取字典项列表
@router.get("/{dict_id}/items", response_model=List[DictionaryItemResponse])
async def get_dictionary_items(
    dict_id: str,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1-100"),
    search: Optional[str] = Query(None, description="搜索关键词（键值或值）"),
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    db: Session = Depends(get_db)
):
    """
    获取指定字典的字典项列表
    
    支持分页、搜索、按状态筛选功能
    """
    logger.info(f"Retrieving dictionary items for dictionary {dict_id} with filters - page: {page}, page_size: {page_size}, search: {search}, status: {status}")
    
    try:
        # 验证字典是否存在
        dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
        if not dictionary:
            logger.warning(f"Dictionary with ID {dict_id} not found")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 调用服务层获取字典项列表
        items_result = dictionary_service.get_dictionary_items(
            db=db,
            dictionary_id=dict_id,
            page=page,
            page_size=page_size,
            search=search,
            status=status
        )
        
        logger.info(f"Retrieved {len(items_result['items'])} dictionary items out of {items_result['total']} total")
        return items_result['items']
        
    except Exception as e:
        logger.error(f"Failed to retrieve dictionary items for {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取字典项列表失败")


# 新增：创建字典项
@router.post("/{dict_id}/items", response_model=DictionaryItemResponse, status_code=201)
async def create_dictionary_item(
    dict_id: str,
    item_data: DictionaryItemCreate,
    db: Session = Depends(get_db)
):
    """
    创建字典项
    
    - 验证字典是否存在
    - 验证键值在字典内唯一
    - 支持所有字段的创建
    """
    logger.info(f"Creating new dictionary item for dictionary {dict_id}: {item_data.item_key} -> {item_data.item_value}")
    
    try:
        # 验证字典是否存在
        dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
        if not dictionary:
            logger.warning(f"Dictionary with ID {dict_id} not found")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 验证键值在字典内是否唯一
        existing_item = dictionary_service.get_dictionary_item_by_key(db, dict_id, item_data.item_key)
        if existing_item:
            logger.warning(f"Dictionary item with key {item_data.item_key} already exists in dictionary {dict_id}")
            raise HTTPException(
                status_code=409, 
                detail=f"字典项键值已存在: {item_data.item_key}"
            )
        
        # 创建字典项
        db_item = dictionary_service.create_dictionary_item(db, dict_id, item_data)
        
        # 转换为响应模型
        item_dict = db_item.to_dict()
        logger.info(f"Dictionary item created successfully: {item_data.item_key} (ID: {db_item.id})")
        return DictionaryItemResponse(**item_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error creating dictionary item: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error creating dictionary item: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create dictionary item: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建字典项失败")


# 新增：更新字典项
@router.put("/{dict_id}/items/{item_id}", response_model=DictionaryItemResponse)
async def update_dictionary_item(
    dict_id: str,
    item_id: str,
    item_data: DictionaryItemUpdate,
    db: Session = Depends(get_db)
):
    """
    更新字典项
    
    - 支持部分更新
    - 验证字典是否存在
    - 验证键值在字典内唯一（排除自身）
    """
    logger.info(f"Updating dictionary item {item_id} for dictionary {dict_id}")
    
    try:
        # 验证字典是否存在
        dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
        if not dictionary:
            logger.warning(f"Dictionary with ID {dict_id} not found")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 获取现有字典项
        existing_item = dictionary_service.get_dictionary_item_by_id(db, item_id)
        
        if not existing_item:
            logger.warning(f"Dictionary item with ID {item_id} not found for update")
            raise HTTPException(status_code=404, detail="字典项不存在")
        
        # 如果更新了键值，验证新键值在字典内是否唯一
        if item_data.item_key and item_data.item_key != existing_item.item_key:
            existing_item_with_key = dictionary_service.get_dictionary_item_by_key(db, dict_id, item_data.item_key)
            if existing_item_with_key:
                logger.warning(f"Dictionary item with key {item_data.item_key} already exists in dictionary {dict_id}")
                raise HTTPException(
                    status_code=409, 
                    detail=f"字典项键值已存在: {item_data.item_key}"
                )
        
        # 更新字典项
        db_item = dictionary_service.update_dictionary_item(db, item_id, item_data)
        
        # 转换为响应模型
        item_dict = db_item.to_dict()
        logger.info(f"Dictionary item {item_id} updated successfully")
        return DictionaryItemResponse(**item_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error updating dictionary item: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error updating dictionary item: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update dictionary item {item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新字典项失败")


# 新增：删除字典项
@router.delete("/{dict_id}/items/{item_id}", status_code=204)
async def delete_dictionary_item(
    dict_id: str,
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    删除字典项
    
    - 验证字典是否存在
    - 验证字典项是否存在
    """
    logger.info(f"Attempting to delete dictionary item {item_id} for dictionary {dict_id}")
    
    try:
        # 验证字典是否存在
        dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
        if not dictionary:
            logger.warning(f"Dictionary with ID {dict_id} not found")
            raise HTTPException(status_code=404, detail="字典不存在")
        
        # 获取现有字典项
        existing_item = dictionary_service.get_dictionary_item_by_id(db, item_id)
        
        if not existing_item:
            logger.warning(f"Dictionary item with ID {item_id} not found for deletion")
            raise HTTPException(status_code=404, detail="字典项不存在")
        
        # 删除字典项
        success = dictionary_service.delete_dictionary_item(db, item_id)
        
        if not success:
            logger.warning(f"Dictionary item with ID {item_id} not found for deletion")
            raise HTTPException(status_code=404, detail="字典项不存在")
        
        logger.info(f"Dictionary item {item_id} deleted successfully")
        
    except HTTPException:
        # Re-raise HTTP exceptions without converting to 500
        raise
    except Exception as e:
        logger.error(f"Failed to delete dictionary item {item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除字典项失败")


# 新增：批量添加字典项
@router.post("/{dict_id}/items/batch", response_model=DictionaryItemBatchResponse, status_code=201)
async def batch_create_dictionary_items(
    dict_id: str,
    batch_data: DictionaryItemBatchCreate,
    db: Session = Depends(get_db)
):
    """
    批量添加字典项
    
    - 支持一次性添加多个字典项
    - 验证字典是否存在
    - 验证每个字典项的键值在字典内唯一
    - 使用事务确保数据一致性
    - 返回成功和失败的统计信息
    - 提供详细的错误信息
    """
    logger.info(f"Batch creating {len(batch_data.items)} dictionary items for dictionary {dict_id}")
    
    # 验证字典是否存在
    dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
    if not dictionary:
        logger.warning(f"Dictionary with ID {dict_id} not found for batch creation")
        raise HTTPException(status_code=404, detail="字典不存在")
    
    success_count = 0
    failed_count = 0
    failed_items = []
    
    try:
        # 使用数据库事务确保数据一致性
        with db.begin():
            for index, item_data in enumerate(batch_data.items):
                try:
                    # 验证键值在字典内是否唯一
                    existing_item = dictionary_service.get_dictionary_item_by_key(db, dict_id, item_data.item_key)
                    if existing_item:
                        logger.warning(f"Dictionary item with key {item_data.item_key} already exists in dictionary {dict_id}")
                        failed_items.append({
                            "index": index,
                            "item_key": item_data.item_key,
                            "error": f"字典项键值已存在: {item_data.item_key}"
                        })
                        failed_count += 1
                        continue
                    
                    # 创建字典项
                    db_item = dictionary_service.create_dictionary_item(db, dict_id, item_data)
                    
                    # 成功计数
                    success_count += 1
                    
                except ValidationError as e:
                    logger.error(f"Validation error creating dictionary item at index {index}: {str(e)}")
                    failed_items.append({
                        "index": index,
                        "item_key": getattr(item_data, 'item_key', 'unknown'),
                        "error": f"数据验证失败: {str(e)}"
                    })
                    failed_count += 1
                except ValueError as e:
                    # 服务层抛出的业务逻辑错误
                    logger.error(f"Business logic error creating dictionary item at index {index}: {str(e)}")
                    failed_items.append({
                        "index": index,
                        "item_key": getattr(item_data, 'item_key', 'unknown'),
                        "error": f"业务逻辑错误: {str(e)}"
                    })
                    failed_count += 1
                except Exception as e:
                    # 其他未知错误
                    logger.error(f"Unexpected error creating dictionary item at index {index}: {str(e)}", exc_info=True)
                    failed_items.append({
                        "index": index,
                        "item_key": getattr(item_data, 'item_key', 'unknown'),
                        "error": f"未知错误: {str(e)}"
                    })
                    failed_count += 1
        
        logger.info(f"Batch creation completed: {success_count} succeeded, {failed_count} failed")
        
        return DictionaryItemBatchResponse(
            success_count=success_count,
            failed_count=failed_count,
            failed_items=failed_items,
            total_processed=len(batch_data.items)
        )
        
    except Exception as e:
        logger.error(f"Failed to batch create dictionary items for {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量添加字典项失败")


# 新增：导出字典为Excel或CSV
@router.get("/{dict_id}/export", response_model=dict)
async def export_dictionary(
    dict_id: str,
    format_type: str = Query("excel", description="导出格式，支持excel或csv"),
    db: Session = Depends(get_db)
):
    """
    导出字典数据为Excel或CSV文件
    
    - 支持Excel (.xlsx) 和 CSV (.csv) 两种格式
    - 返回文件下载链接
    - 包含完整的字典项数据
    """
    logger.info(f"Exporting dictionary {dict_id} in {format_type} format")
    
    # 验证字典是否存在
    dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
    if not dictionary:
        logger.warning(f"Dictionary with ID {dict_id} not found")
        raise HTTPException(status_code=404, detail="字典不存在")
    
    # 验证格式类型
    if format_type not in ["excel", "csv"]:
        logger.warning(f"Unsupported format type: {format_type}")
        raise HTTPException(status_code=400, detail="不支持的格式类型，支持excel或csv")
    
    try:
        # 获取字典项数据
        items = dictionary_service.get_dictionary_items(db, dictionary_id=dict_id, page=1, page_size=10000)
        
        # 导出数据
        from src.services.dictionary_import_export import DictionaryImportExportService
        export_service = DictionaryImportExportService()
        
        if format_type == "excel":
            file_path = export_service.export_dictionary_to_excel(dict_id, items.items)
            download_url = f"/api/dictionaries/{dict_id}/download?format=excel"
        else:
            file_path = export_service.export_dictionary_to_csv(dict_id, items.items)
            download_url = f"/api/dictionaries/{dict_id}/download?format=csv"
        
        logger.info(f"Dictionary exported successfully in {format_type} format")
        
        return {
            "message": f"字典 {dictionary.name} 导出成功",
            "format": format_type,
            "download_url": download_url,
            "file_name": file_path.split('/')[-1],
            "item_count": len(items.items)
        }
        
    except Exception as e:
        logger.error(f"Failed to export dictionary {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="导出字典失败")


# 新增：下载导出的文件
@router.get("/{dict_id}/download")
async def download_exported_file(
    dict_id: str,
    format_type: str = Query("excel", description="文件格式，支持excel或csv"),
    db: Session = Depends(get_db)
):
    """
    下载导出的字典文件
    
    - 返回文件流供浏览器下载
    """
    logger.info(f"Downloading exported file for dictionary {dict_id} in {format_type} format")
    
    # 验证字典是否存在
    dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
    if not dictionary:
        logger.warning(f"Dictionary with ID {dict_id} not found")
        raise HTTPException(status_code=404, detail="字典不存在")
    
    # 验证格式类型
    if format_type not in ["excel", "csv"]:
        logger.warning(f"Unsupported format type: {format_type}")
        raise HTTPException(status_code=400, detail="不支持的格式类型，支持excel或csv")
    
    try:
        from src.services.dictionary_import_export import DictionaryImportExportService
        export_service = DictionaryImportExportService()
        
        # 获取导出文件路径
        file_path = export_service.get_export_file_path(dict_id, format_type)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f"Export file not found: {file_path}")
            raise HTTPException(status_code=404, detail="导出文件不存在")
        
        # 设置响应头
        filename = os.path.basename(file_path)
        
        # 设置正确的MIME类型
        if format_type == "excel":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            media_type = "text/csv; charset=utf-8-sig"
        
        # 返回文件流
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
    except Exception as e:
        logger.error(f"Failed to download exported file for dictionary {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="下载导出文件失败")


# 新增：获取缓存状态
@router.get("/cache/stats", response_model=dict)
async def get_cache_stats():
    """
    获取字典缓存统计信息
    
    Returns:
        缓存统计信息字典
    """
    logger.info("Retrieving dictionary cache stats")
    
    try:
        stats = dictionary_cache.get_cache_stats()
        logger.info("Successfully retrieved cache stats")
        return stats
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取缓存状态失败")


# 新增：导入字典数据
@router.post("/{dict_id}/import", response_model=dict)
async def import_dictionary(
    dict_id: str,
    file: UploadFile,
    db: Session = Depends(get_db)
):
    """
    从Excel或CSV文件导入字典数据
    
    - 支持Excel (.xlsx, .xls) 和 CSV (.csv) 格式
    - 验证数据格式和完整性
    - 返回导入结果统计信息
    - 支持更新现有字典项和创建新字典项
    """
    logger.info(f"Importing dictionary data for {dict_id} from file: {file.filename}")
    
    # 验证字典是否存在
    dictionary = dictionary_service.get_dictionary_by_id(db, dict_id)
    if not dictionary:
        logger.warning(f"Dictionary with ID {dict_id} not found")
        raise HTTPException(status_code=404, detail="字典不存在")
    
    # 验证文件
    if not file.filename:
        logger.warning("No file provided for import")
        raise HTTPException(status_code=400, detail="未提供文件")
    
    # 保存上传的文件
    upload_dir = os.getenv('UPLOAD_DIR', './public/uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_name = f"{int(pd.Timestamp.now().timestamp())}-{file.filename}"
    file_path = os.path.join(upload_dir, file_name)
    
    try:
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Uploaded file saved to: {file_path}")
        
        # 验证文件
        from src.services.dictionary_import_export import DictionaryImportExportService
        export_service = DictionaryImportExportService()
        validation_result = export_service.validate_import_file(file_path)
        
        # 根据文件扩展名选择导入方法
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in ['.xlsx', '.xls']:
            result = export_service.import_dictionary_from_excel(file_path, dict_id, db)
        elif file_extension == '.csv':
            result = export_service.import_dictionary_from_csv(file_path, dict_id, db)
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")
        
        # 删除临时文件
        os.unlink(file_path)
        
        logger.info(f"Import completed for {dict_id}: {result['success_count']} succeeded, {result['failed_count']} failed")
        
        return {
            "message": f"字典 {dictionary.name} 导入完成",
            "success_count": result['success_count'],
            "failed_count": result['failed_count'],
            "total_processed": result['total_processed'],
            "failed_items": result['failed_items']
        }
        
    except Exception as e:
        # 删除临时文件
        if 'file_path' in locals() and os.path.exists(file_path):
            os.unlink(file_path)
        
        logger.error(f"Failed to import dictionary data for {dict_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入字典数据失败: {str(e)}")
