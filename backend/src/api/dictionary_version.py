"""
字典版本管理 API
提供字典版本的创建、比较、回滚等接口
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.services.dictionary_version_service import DictionaryVersionService
from src.schemas.dictionary_version_schema import (
    CreateVersionFromCurrentRequest,
    VersionCompareRequest,
    VersionRollbackRequest,
    DictionaryVersionResponse,
    DictionaryVersionListResponse,
    VersionCompareResponse,
    VersionRollbackResponse,
    VersionStatistics
)
from src.database import get_db

router = APIRouter(tags=["dictionary-version"])


@router.post("/create-from-current", response_model=DictionaryVersionResponse)
def create_version_from_current(
    request: CreateVersionFromCurrentRequest,
    db: Session = Depends(get_db)
):
    """
    从当前字典状态创建版本
    """
    try:
        service = DictionaryVersionService(db)
        return service.create_version_from_current(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建版本失败: {str(e)}")


@router.get("/{dictionary_id}/list", response_model=DictionaryVersionListResponse)
def get_version_list(
    dictionary_id: str,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小，1-100"),
    db: Session = Depends(get_db)
):
    """
    获取字典版本列表
    """
    try:
        service = DictionaryVersionService(db)
        result = service.get_version_list(dictionary_id, page, page_size)
        return DictionaryVersionListResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本列表失败: {str(e)}")


@router.get("/detail/{version_id}", response_model=Dict[str, Any])
def get_version_detail(
    version_id: str,
    db: Session = Depends(get_db)
):
    """
    获取版本详情
    """
    try:
        service = DictionaryVersionService(db)
        return service.get_version_detail(version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本详情失败: {str(e)}")


@router.post("/compare", response_model=VersionCompareResponse)
def compare_versions(
    request: VersionCompareRequest,
    db: Session = Depends(get_db)
):
    """
    比较两个版本的差异
    """
    try:
        service = DictionaryVersionService(db)
        return service.compare_versions(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"版本比较失败: {str(e)}")


@router.post("/rollback", response_model=VersionRollbackResponse)
def rollback_version(
    request: VersionRollbackRequest,
    db: Session = Depends(get_db)
):
    """
    回滚到指定版本
    """
    try:
        service = DictionaryVersionService(db)
        return service.rollback_version(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"版本回滚失败: {str(e)}")


@router.get("/statistics/{dictionary_id}", response_model=VersionStatistics)
def get_version_statistics(
    dictionary_id: str,
    db: Session = Depends(get_db)
):
    """
    获取字典版本统计信息
    
    - 接收 dictionary_id 路径参数
    - 调用 DictionaryVersionService.get_version_statistics 方法
    - 返回 VersionStatistics 响应模型
    - 异常处理：ValueError -> 404 错误，Exception -> 500 错误
    """
    try:
        service = DictionaryVersionService(db)
        return service.get_version_statistics(dictionary_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本统计信息失败: {str(e)}")