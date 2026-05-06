"""
动态字典配置 API
提供动态字典的配置管理、查询测试、数据刷新等功能
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.dynamic_dictionary_service import DynamicDictionaryService
from ..schemas.dynamic_dictionary_schema import (
    DynamicDictionaryConfigCreate,
    DynamicDictionaryConfigUpdate,
    DynamicDictionaryConfigResponse,
    QueryTestRequest,
    QueryTestResponse,
    RefreshResult,
    DynamicDictionaryListResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dynamic-dictionaries", tags=["动态字典配置"])


@router.post("/", response_model=DynamicDictionaryConfigResponse, summary="创建动态字典配置")
async def create_dynamic_dictionary_config(
    config_data: DynamicDictionaryConfigCreate,
    db: Session = Depends(get_db)
):
    """
    创建动态字典配置
    
    - **dictionary_id**: 字典ID
    - **data_source_id**: 数据源ID
    - **sql_query**: SQL查询语句（只允许SELECT语句）
    - **key_field**: 键字段名
    - **value_field**: 值字段名
    - **refresh_interval**: 刷新间隔（秒，最小60秒）
    """
    try:
        service = DynamicDictionaryService(db)
        config = service.create_config(config_data)
        return DynamicDictionaryConfigResponse.from_orm(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建动态字典配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建配置失败")


@router.get("/{dictionary_id}", response_model=DynamicDictionaryConfigResponse, summary="获取动态字典配置")
async def get_dynamic_dictionary_config(
    dictionary_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定字典的动态配置
    
    - **dictionary_id**: 字典ID
    """
    try:
        service = DynamicDictionaryService(db)
        config = service.get_config(dictionary_id)
        if not config:
            raise HTTPException(status_code=404, detail="动态字典配置不存在")
        return DynamicDictionaryConfigResponse.from_orm(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取动态字典配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取配置失败")


@router.put("/{dictionary_id}", response_model=DynamicDictionaryConfigResponse, summary="更新动态字典配置")
async def update_dynamic_dictionary_config(
    dictionary_id: str,
    config_data: DynamicDictionaryConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新动态字典配置
    
    - **dictionary_id**: 字典ID
    - 其他字段为可选更新字段
    """
    try:
        service = DynamicDictionaryService(db)
        config = service.update_config(dictionary_id, config_data)
        return DynamicDictionaryConfigResponse.from_orm(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新动态字典配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新配置失败")


@router.delete("/{dictionary_id}", summary="删除动态字典配置")
async def delete_dynamic_dictionary_config(
    dictionary_id: str,
    db: Session = Depends(get_db)
):
    """
    删除动态字典配置
    
    - **dictionary_id**: 字典ID
    """
    try:
        service = DynamicDictionaryService(db)
        service.delete_config(dictionary_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除动态字典配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除配置失败")


@router.post("/test-query", response_model=QueryTestResponse, summary="测试SQL查询")
async def test_sql_query(
    test_request: QueryTestRequest,
    db: Session = Depends(get_db)
):
    """
    测试SQL查询是否正确
    
    - **data_source_id**: 数据源ID
    - **sql_query**: SQL查询语句
    - **key_field**: 键字段名
    - **value_field**: 值字段名
    
    返回查询结果的示例数据（最多10条）和总记录数
    """
    try:
        service = DynamicDictionaryService(db)
        result = service.test_query(test_request)
        return result
    except Exception as e:
        logger.error(f"测试SQL查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="测试查询失败")


@router.post("/{dictionary_id}/refresh", response_model=RefreshResult, summary="手动刷新动态字典")
async def refresh_dynamic_dictionary(
    dictionary_id: str,
    db: Session = Depends(get_db)
):
    """
    手动刷新动态字典数据
    
    - **dictionary_id**: 字典ID
    
    执行SQL查询并更新字典项数据
    """
    try:
        service = DynamicDictionaryService(db)
        result = service.refresh_dictionary(dictionary_id)
        return result
    except Exception as e:
        logger.error(f"刷新动态字典失败: {str(e)}")
        raise HTTPException(status_code=500, detail="刷新字典失败")


@router.get("/", response_model=DynamicDictionaryListResponse, summary="获取动态字典配置列表")
async def get_dynamic_dictionary_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db)
):
    """
    获取动态字典配置列表
    
    - **page**: 页码（从1开始）
    - **page_size**: 每页大小（1-100）
    """
    try:
        service = DynamicDictionaryService(db)
        configs, total = service.get_configs_list(page, page_size)
        
        items = [DynamicDictionaryConfigResponse.from_orm(config) for config in configs]
        
        return DynamicDictionaryListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"获取动态字典配置列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取配置列表失败")


@router.get("/{dictionary_id}/refresh-status", summary="检查刷新状态")
async def check_refresh_status(
    dictionary_id: str,
    db: Session = Depends(get_db)
):
    """
    检查动态字典是否需要刷新
    
    - **dictionary_id**: 字典ID
    """
    try:
        service = DynamicDictionaryService(db)
        needs_refresh = service.check_refresh_needed(dictionary_id)
        
        config = service.get_config(dictionary_id)
        if not config:
            raise HTTPException(status_code=404, detail="动态字典配置不存在")
        
        return {
            "needs_refresh": needs_refresh,
            "last_refresh_time": config.last_refresh_time,
            "refresh_interval": config.refresh_interval
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查刷新状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查刷新状态失败")