from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import logging

from ..database import get_db
from ..services.semantic_injection_service import semantic_injection_service
from ..schemas.base_schema import BaseResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/semantic-injection", tags=["semantic-injection"])

class SemanticInjectionRequest(BaseModel):
    """语义注入请求模型"""
    table_name: str
    data: List[Dict[str, Any]]

class BatchSemanticInjectionRequest(BaseModel):
    """批量语义注入请求模型"""
    table_data_map: Dict[str, List[Dict[str, Any]]]

class SemanticMappingResponse(BaseModel):
    """语义映射响应模型"""
    dictionary_id: Optional[str]
    dictionary_name: Optional[str]
    dictionary_code: Optional[str]
    field_mapping_id: Optional[str]
    mapping_type: Optional[str]
    value_mappings: Dict[str, Any]
    metadata: Dict[str, Any]

class SemanticSchemaResponse(BaseModel):
    """语义模式响应模型"""
    table_name: str
    semantic_fields: Dict[str, Any]
    metadata: Dict[str, Any]

@router.get("/field-mapping/{table_name}/{field_name}")
async def get_field_semantic_mapping(
    table_name: str,
    field_name: str,
    db: Session = Depends(get_db)
) -> BaseResponse[SemanticMappingResponse]:
    """获取字段的语义映射信息
    
    Args:
        table_name: 表名
        field_name: 字段名
        db: 数据库会话
        
    Returns:
        字段的语义映射信息
    """
    try:
        semantic_mapping = semantic_injection_service.get_field_semantic_mapping(
            db, table_name, field_name
        )
        
        if not semantic_mapping:
            return BaseResponse(
                success=False,
                message=f"未找到字段 {table_name}.{field_name} 的语义映射",
                data=None
            )
        
        return BaseResponse(
            success=True,
            message="获取字段语义映射成功",
            data=semantic_mapping
        )
        
    except Exception as e:
        logger.error(f"获取字段语义映射失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取字段语义映射失败: {str(e)}")

@router.post("/inject")
async def inject_semantic_values(
    request: SemanticInjectionRequest,
    db: Session = Depends(get_db)
) -> BaseResponse[List[Dict[str, Any]]]:
    """为查询结果注入语义值
    
    Args:
        request: 语义注入请求
        db: 数据库会话
        
    Returns:
        注入语义信息后的数据
    """
    try:
        enhanced_data = semantic_injection_service.inject_semantic_values(
            db, request.table_name, request.data
        )
        
        return BaseResponse(
            success=True,
            message="语义值注入成功",
            data=enhanced_data
        )
        
    except Exception as e:
        logger.error(f"语义值注入失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"语义值注入失败: {str(e)}")

@router.post("/batch-inject")
async def batch_inject_semantic_values(
    request: BatchSemanticInjectionRequest,
    db: Session = Depends(get_db)
) -> BaseResponse[Dict[str, List[Dict[str, Any]]]]:
    """批量为多个表的数据注入语义值
    
    Args:
        request: 批量语义注入请求
        db: 数据库会话
        
    Returns:
        注入语义信息后的数据映射
    """
    try:
        enhanced_data_map = semantic_injection_service.batch_inject_semantic_values(
            db, request.table_data_map
        )
        
        return BaseResponse(
            success=True,
            message="批量语义值注入成功",
            data=enhanced_data_map
        )
        
    except Exception as e:
        logger.error(f"批量语义值注入失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量语义值注入失败: {str(e)}")

@router.get("/schema/{table_name}")
async def get_table_semantic_schema(
    table_name: str,
    db: Session = Depends(get_db)
) -> BaseResponse[SemanticSchemaResponse]:
    """获取表的语义模式
    
    Args:
        table_name: 表名
        db: 数据库会话
        
    Returns:
        表的语义模式信息
    """
    try:
        schema = semantic_injection_service.get_table_semantic_schema(db, table_name)
        
        return BaseResponse(
            success=True,
            message="获取表语义模式成功",
            data=schema
        )
        
    except Exception as e:
        logger.error(f"获取表语义模式失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取表语义模式失败: {str(e)}")

@router.post("/cache/clear")
async def clear_semantic_cache() -> BaseResponse[Dict[str, str]]:
    """清空语义注入缓存
    
    Returns:
        清空结果
    """
    try:
        semantic_injection_service.clear_cache()
        
        return BaseResponse(
            success=True,
            message="语义注入缓存已清空",
            data={"status": "cleared"}
        )
        
    except Exception as e:
        logger.error(f"清空语义注入缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空语义注入缓存失败: {str(e)}")

@router.get("/cache/stats")
async def get_cache_stats() -> BaseResponse[Dict[str, Any]]:
    """获取缓存统计信息
    
    Returns:
        缓存统计信息
    """
    try:
        stats = semantic_injection_service.get_cache_stats()
        
        return BaseResponse(
            success=True,
            message="获取缓存统计信息成功",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"获取缓存统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取缓存统计信息失败: {str(e)}")

@router.get("/health")
async def health_check() -> BaseResponse[Dict[str, str]]:
    """健康检查
    
    Returns:
        服务状态
    """
    return BaseResponse(
        success=True,
        message="语义注入服务运行正常",
        data={"status": "healthy"}
    )