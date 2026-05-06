"""
多源数据整合引擎 API

提供任务 5.2.1 的 API 接口：
1. 整合数据源信息、表结构、表关联、数据字典、知识库五大模块
2. 创建统一的元数据查询和聚合接口
3. 实现元数据的缓存和增量更新机制
4. 支持跨数据源的表关联分析和推荐
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from src.database import get_db
from src.services.multi_source_data_integration import (
    MultiSourceDataIntegrationEngine,
    MetadataQuery,
    IntegratedMetadata
)

# 创建路由器
router = APIRouter(prefix="/api/multi-source-integration", tags=["多源数据整合"])
logger = logging.getLogger(__name__)


@router.post("/query-metadata", response_model=Dict[str, Any])
async def query_integrated_metadata(
    user_question: str,
    data_source_ids: Optional[List[str]] = None,
    table_ids: Optional[List[str]] = None,
    include_relations: bool = True,
    include_dictionary: bool = True,
    include_knowledge: bool = True,
    max_tables: int = 10,
    token_budget: int = 4000,
    db: Session = Depends(get_db)
):
    """
    查询整合元数据
    
    整合数据源信息、表结构、表关联、数据字典、知识库五大模块的数据。
    
    Args:
        user_question: 用户问题
        data_source_ids: 指定的数据源ID列表（可选）
        table_ids: 指定的表ID列表（可选）
        include_relations: 是否包含表关联信息
        include_dictionary: 是否包含数据字典信息
        include_knowledge: 是否包含知识库信息
        max_tables: 最大表数量限制
        token_budget: Token预算
        db: 数据库会话
        
    Returns:
        整合后的元数据
    """
    try:
        logger.info(f"查询整合元数据，问题: {user_question[:100]}...")
        
        # 创建整合引擎
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 创建查询请求
        query = MetadataQuery(
            user_question=user_question,
            data_source_ids=data_source_ids,
            table_ids=table_ids,
            include_relations=include_relations,
            include_dictionary=include_dictionary,
            include_knowledge=include_knowledge,
            max_tables=max_tables,
            token_budget=token_budget
        )
        
        # 执行查询
        result = await integration_engine.query_integrated_metadata(query)
        
        # 转换为字典格式返回
        return {
            "success": True,
            "data": {
                "data_sources": result.data_sources,
                "tables": result.tables,
                "relations": result.relations,
                "dictionary_mappings": result.dictionary_mappings,
                "knowledge_items": result.knowledge_items,
                "enhanced_context": result.enhanced_context,
                "relevance_scores": result.relevance_scores,
                "total_tokens_used": result.total_tokens_used
            },
            "message": f"成功整合 {len(result.tables)} 个表的元数据"
        }
        
    except Exception as e:
        logger.error(f"查询整合元数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询整合元数据失败: {str(e)}")


@router.get("/cross-datasource-relations", response_model=Dict[str, Any])
async def get_cross_datasource_relations(
    data_source_ids: List[str] = Query(..., description="数据源ID列表"),
    db: Session = Depends(get_db)
):
    """
    获取跨数据源的表关联分析和推荐
    
    分析多个数据源之间的表关联关系，发现潜在的跨数据源关联。
    
    Args:
        data_source_ids: 数据源ID列表
        db: 数据库会话
        
    Returns:
        跨数据源关联分析结果
    """
    try:
        logger.info(f"分析跨数据源关联，涉及 {len(data_source_ids)} 个数据源")
        
        if len(data_source_ids) < 2:
            raise HTTPException(status_code=400, detail="至少需要2个数据源才能进行跨数据源关联分析")
        
        # 创建整合引擎
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 执行跨数据源关联分析
        relations = await integration_engine.get_cross_datasource_relations(data_source_ids)
        
        return {
            "success": True,
            "data": {
                "relations": relations,
                "total_relations": len(relations),
                "data_source_count": len(data_source_ids)
            },
            "message": f"发现 {len(relations)} 个潜在的跨数据源关联"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"跨数据源关联分析失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"跨数据源关联分析失败: {str(e)}")


@router.post("/update-cache", response_model=Dict[str, Any])
async def update_metadata_cache(
    table_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    增量更新元数据缓存
    
    当表结构或相关元数据发生变化时，增量更新相关的缓存项。
    
    Args:
        table_ids: 需要更新缓存的表ID列表
        db: 数据库会话
        
    Returns:
        缓存更新结果
    """
    try:
        logger.info(f"增量更新元数据缓存，涉及 {len(table_ids)} 个表")
        
        # 创建整合引擎
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 执行增量更新
        await integration_engine.update_metadata_cache(table_ids)
        
        return {
            "success": True,
            "data": {
                "updated_table_count": len(table_ids),
                "table_ids": table_ids
            },
            "message": f"成功更新 {len(table_ids)} 个表的元数据缓存"
        }
        
    except Exception as e:
        logger.error(f"增量更新缓存失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"增量更新缓存失败: {str(e)}")


@router.delete("/cache", response_model=Dict[str, Any])
async def clear_metadata_cache(
    db: Session = Depends(get_db)
):
    """
    清空元数据缓存
    
    清空所有的元数据缓存，强制下次查询重新生成。
    
    Args:
        db: 数据库会话
        
    Returns:
        缓存清空结果
    """
    try:
        logger.info("清空元数据缓存")
        
        # 创建整合引擎
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 清空缓存
        integration_engine.clear_cache()
        
        return {
            "success": True,
            "data": {},
            "message": "元数据缓存已清空"
        }
        
    except Exception as e:
        logger.error(f"清空缓存失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


@router.get("/cache/statistics", response_model=Dict[str, Any])
async def get_cache_statistics(
    db: Session = Depends(get_db)
):
    """
    获取缓存统计信息
    
    返回当前缓存的统计信息，包括缓存项数量、缓存键等。
    
    Args:
        db: 数据库会话
        
    Returns:
        缓存统计信息
    """
    try:
        logger.info("获取缓存统计信息")
        
        # 创建整合引擎
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 获取统计信息
        stats = integration_engine.get_cache_statistics()
        
        return {
            "success": True,
            "data": stats,
            "message": "缓存统计信息获取成功"
        }
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    db: Session = Depends(get_db)
):
    """
    健康检查
    
    检查多源数据整合引擎的健康状态。
    
    Args:
        db: 数据库会话
        
    Returns:
        健康状态信息
    """
    try:
        # 创建整合引擎进行基本检查
        integration_engine = MultiSourceDataIntegrationEngine(db)
        
        # 获取缓存统计作为健康检查的一部分
        stats = integration_engine.get_cache_statistics()
        
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "cache_items": stats["total_cached_items"],
                "timestamp": "2024-01-01T00:00:00Z"  # 实际应用中使用真实时间戳
            },
            "message": "多源数据整合引擎运行正常"
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data": {
                "status": "unhealthy",
                "error": str(e)
            },
            "message": "多源数据整合引擎异常"
        }