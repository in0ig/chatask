"""
知识库语义注入API

提供知识库语义注入相关的API端点，包括语义注入、知识查询、缓存管理等功能。
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.services.knowledge_semantic_injection import (
    KnowledgeSemanticInjectionService,
    SemanticInjectionResult,
    KnowledgeSemanticInfo,
    TermKnowledge,
    LogicKnowledge,
    EventKnowledge
)
from src.utils import get_db_session
from src.schemas.base_schema import BaseResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-semantic", tags=["knowledge-semantic-injection"])


# 请求模型
class KnowledgeSemanticInjectionRequest(BaseModel):
    """知识库语义注入请求"""
    user_question: str = Field(..., description="用户问题")
    table_ids: Optional[List[str]] = Field(None, description="相关表ID列表")
    include_global: bool = Field(True, description="是否包含全局知识")
    max_terms: int = Field(10, ge=1, le=50, description="最大术语数量")
    max_logics: int = Field(5, ge=1, le=20, description="最大逻辑数量")
    max_events: int = Field(3, ge=1, le=10, description="最大事件数量")


# 响应模型
class TermKnowledgeResponse(BaseModel):
    """业务术语知识响应"""
    id: str
    name: str
    explanation: str
    example_question: Optional[str] = None
    scope: str
    table_id: Optional[str] = None
    relevance_score: float


class LogicKnowledgeResponse(BaseModel):
    """业务逻辑知识响应"""
    id: str
    explanation: str
    example_question: Optional[str] = None
    scope: str
    table_id: Optional[str] = None
    relevance_score: float


class EventKnowledgeResponse(BaseModel):
    """事件知识响应"""
    id: str
    explanation: str
    event_date_start: Optional[str] = None
    event_date_end: Optional[str] = None
    scope: str
    table_id: Optional[str] = None
    relevance_score: float
    is_active: bool


class KnowledgeSemanticInfoResponse(BaseModel):
    """知识库语义信息响应"""
    terms: List[TermKnowledgeResponse]
    logics: List[LogicKnowledgeResponse]
    events: List[EventKnowledgeResponse]
    total_relevance_score: float


class SemanticInjectionResponse(BaseModel):
    """语义注入响应"""
    enhanced_context: str
    knowledge_info: KnowledgeSemanticInfoResponse
    injection_summary: Dict[str, Any]


# API端点
@router.post("/inject", response_model=BaseResponse[SemanticInjectionResponse])
async def inject_knowledge_semantics(
    request: KnowledgeSemanticInjectionRequest,
    db: Session = Depends(get_db_session)
):
    """
    注入知识库语义信息
    
    根据用户问题和相关表，智能匹配业务术语、业务逻辑和事件知识，
    生成增强的语义上下文。
    """
    try:
        logger.info(f"收到知识库语义注入请求: {request.user_question[:100]}...")
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 执行语义注入
        result = service.inject_knowledge_semantics(
            user_question=request.user_question,
            table_ids=request.table_ids,
            include_global=request.include_global,
            max_terms=request.max_terms,
            max_logics=request.max_logics,
            max_events=request.max_events
        )
        
        # 转换响应格式
        response_data = SemanticInjectionResponse(
            enhanced_context=result.enhanced_context,
            knowledge_info=_convert_knowledge_info(result.knowledge_info),
            injection_summary=result.injection_summary
        )
        
        logger.info(f"知识库语义注入成功，总相关性得分: {result.knowledge_info.total_relevance_score:.2f}")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="知识库语义注入成功"
        )
        
    except Exception as e:
        logger.error(f"知识库语义注入失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库语义注入失败: {str(e)}"
        )


@router.get("/table/{table_id}", response_model=BaseResponse[KnowledgeSemanticInfoResponse])
async def get_knowledge_by_table(
    table_id: str,
    db: Session = Depends(get_db_session)
):
    """
    获取指定表的所有知识
    
    返回指定表相关的所有业务术语、业务逻辑和事件知识。
    """
    try:
        logger.info(f"获取表级知识: {table_id}")
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 获取表级知识
        knowledge_info = service.get_knowledge_by_table(table_id)
        
        # 转换响应格式
        response_data = _convert_knowledge_info(knowledge_info)
        
        logger.info(f"获取表级知识成功，共 {len(knowledge_info.terms + knowledge_info.logics + knowledge_info.events)} 项")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="获取表级知识成功"
        )
        
    except Exception as e:
        logger.error(f"获取表级知识失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表级知识失败: {str(e)}"
        )


@router.get("/global", response_model=BaseResponse[KnowledgeSemanticInfoResponse])
async def get_global_knowledge(
    db: Session = Depends(get_db_session)
):
    """
    获取全局知识
    
    返回所有全局范围的业务术语、业务逻辑和事件知识。
    """
    try:
        logger.info("获取全局知识")
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 获取全局知识
        knowledge_info = service.get_global_knowledge()
        
        # 转换响应格式
        response_data = _convert_knowledge_info(knowledge_info)
        
        logger.info(f"获取全局知识成功，共 {len(knowledge_info.terms + knowledge_info.logics + knowledge_info.events)} 项")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="获取全局知识成功"
        )
        
    except Exception as e:
        logger.error(f"获取全局知识失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取全局知识失败: {str(e)}"
        )


@router.post("/batch-inject", response_model=BaseResponse[List[SemanticInjectionResponse]])
async def batch_inject_knowledge_semantics(
    requests: List[KnowledgeSemanticInjectionRequest],
    db: Session = Depends(get_db_session)
):
    """
    批量注入知识库语义信息
    
    支持同时处理多个用户问题的语义注入。
    """
    try:
        logger.info(f"收到批量知识库语义注入请求，共 {len(requests)} 个问题")
        
        if len(requests) > 10:  # 限制批量处理数量
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="批量处理数量不能超过10个"
            )
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 批量处理
        results = []
        for request in requests:
            result = service.inject_knowledge_semantics(
                user_question=request.user_question,
                table_ids=request.table_ids,
                include_global=request.include_global,
                max_terms=request.max_terms,
                max_logics=request.max_logics,
                max_events=request.max_events
            )
            
            response_data = SemanticInjectionResponse(
                enhanced_context=result.enhanced_context,
                knowledge_info=_convert_knowledge_info(result.knowledge_info),
                injection_summary=result.injection_summary
            )
            results.append(response_data)
        
        logger.info(f"批量知识库语义注入成功，处理了 {len(results)} 个问题")
        
        return BaseResponse(
            success=True,
            data=results,
            message="批量知识库语义注入成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量知识库语义注入失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量知识库语义注入失败: {str(e)}"
        )


@router.get("/search", response_model=BaseResponse[KnowledgeSemanticInfoResponse])
async def search_knowledge(
    keywords: str = Query(..., description="搜索关键词"),
    knowledge_type: Optional[str] = Query(None, description="知识类型 (TERM/LOGIC/EVENT)"),
    scope: Optional[str] = Query(None, description="知识范围 (GLOBAL/TABLE)"),
    table_id: Optional[str] = Query(None, description="表ID"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db_session)
):
    """
    搜索知识库
    
    根据关键词搜索相关的业务术语、业务逻辑和事件知识。
    """
    try:
        logger.info(f"搜索知识库: {keywords}")
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 构建搜索参数
        table_ids = [table_id] if table_id else None
        include_global = scope != "TABLE"
        
        # 根据知识类型调整搜索参数
        max_terms = limit if not knowledge_type or knowledge_type == "TERM" else 0
        max_logics = limit if not knowledge_type or knowledge_type == "LOGIC" else 0
        max_events = limit if not knowledge_type or knowledge_type == "EVENT" else 0
        
        # 执行搜索（使用语义注入功能）
        result = service.inject_knowledge_semantics(
            user_question=keywords,
            table_ids=table_ids,
            include_global=include_global,
            max_terms=max_terms,
            max_logics=max_logics,
            max_events=max_events
        )
        
        # 转换响应格式
        response_data = _convert_knowledge_info(result.knowledge_info)
        
        total_items = len(result.knowledge_info.terms + result.knowledge_info.logics + result.knowledge_info.events)
        logger.info(f"搜索知识库成功，找到 {total_items} 项相关知识")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message=f"搜索知识库成功，找到 {total_items} 项相关知识"
        )
        
    except Exception as e:
        logger.error(f"搜索知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索知识库失败: {str(e)}"
        )


@router.delete("/cache", response_model=BaseResponse[Dict[str, str]])
async def clear_cache(
    db: Session = Depends(get_db_session)
):
    """
    清空知识库语义注入缓存
    
    清空所有缓存的知识库数据，强制重新从数据库加载。
    """
    try:
        logger.info("清空知识库语义注入缓存")
        
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 清空缓存
        service.clear_cache()
        
        logger.info("知识库语义注入缓存清空成功")
        
        return BaseResponse(
            success=True,
            data={"status": "cache_cleared"},
            message="知识库语义注入缓存清空成功"
        )
        
    except Exception as e:
        logger.error(f"清空知识库语义注入缓存失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空知识库语义注入缓存失败: {str(e)}"
        )


@router.get("/health", response_model=BaseResponse[Dict[str, Any]])
async def health_check(
    db: Session = Depends(get_db_session)
):
    """
    健康检查
    
    检查知识库语义注入服务的健康状态。
    """
    try:
        # 创建服务实例
        service = KnowledgeSemanticInjectionService(db)
        
        # 执行简单的健康检查
        global_knowledge = service.get_global_knowledge()
        
        health_info = {
            "status": "healthy",
            "service": "knowledge_semantic_injection",
            "global_knowledge_count": len(global_knowledge.terms + global_knowledge.logics + global_knowledge.events),
            "database_connection": "ok"
        }
        
        return BaseResponse(
            success=True,
            data=health_info,
            message="知识库语义注入服务健康"
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


# 辅助函数
def _convert_knowledge_info(knowledge_info: KnowledgeSemanticInfo) -> KnowledgeSemanticInfoResponse:
    """转换知识库语义信息为响应格式"""
    return KnowledgeSemanticInfoResponse(
        terms=[
            TermKnowledgeResponse(
                id=term.id,
                name=term.name,
                explanation=term.explanation,
                example_question=term.example_question,
                scope=term.scope,
                table_id=term.table_id,
                relevance_score=term.relevance_score
            )
            for term in knowledge_info.terms
        ],
        logics=[
            LogicKnowledgeResponse(
                id=logic.id,
                explanation=logic.explanation,
                example_question=logic.example_question,
                scope=logic.scope,
                table_id=logic.table_id,
                relevance_score=logic.relevance_score
            )
            for logic in knowledge_info.logics
        ],
        events=[
            EventKnowledgeResponse(
                id=event.id,
                explanation=event.explanation,
                event_date_start=event.event_date_start.isoformat() if event.event_date_start else None,
                event_date_end=event.event_date_end.isoformat() if event.event_date_end else None,
                scope=event.scope,
                table_id=event.table_id,
                relevance_score=event.relevance_score,
                is_active=event.is_active
            )
            for event in knowledge_info.events
        ],
        total_relevance_score=knowledge_info.total_relevance_score
    )