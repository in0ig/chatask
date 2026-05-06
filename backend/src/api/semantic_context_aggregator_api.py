"""
语义上下文聚合引擎API

提供语义上下文聚合、Token预算管理、模块优先级配置等功能的API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.database import get_db
from src.services.semantic_context_aggregator import (
    SemanticContextAggregator,
    TokenBudget,
    ModuleType,
    ContextPriority,
    AggregationResult
)
from src.schemas.base_schema import BaseResponse

router = APIRouter(prefix="/api/semantic-context", tags=["语义上下文聚合"])


class TokenBudgetRequest(BaseModel):
    """Token预算请求"""
    total_budget: int = Field(default=4000, ge=1000, le=10000, description="总Token预算")
    reserved_for_response: int = Field(default=1000, ge=500, le=3000, description="为响应预留的Token")


class ModulePriorityRequest(BaseModel):
    """模块优先级请求"""
    data_source: Optional[ContextPriority] = Field(default=None, description="数据源模块优先级")
    table_structure: Optional[ContextPriority] = Field(default=None, description="表结构模块优先级")
    table_relation: Optional[ContextPriority] = Field(default=None, description="表关联模块优先级")
    dictionary: Optional[ContextPriority] = Field(default=None, description="数据字典模块优先级")
    knowledge: Optional[ContextPriority] = Field(default=None, description="知识库模块优先级")


class SemanticContextRequest(BaseModel):
    """语义上下文聚合请求"""
    user_question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    table_ids: Optional[List[str]] = Field(default=None, description="相关表ID列表")
    include_global: bool = Field(default=True, description="是否包含全局知识")
    token_budget: Optional[TokenBudgetRequest] = Field(default=None, description="Token预算配置")
    module_priorities: Optional[ModulePriorityRequest] = Field(default=None, description="模块优先级配置")


class BatchSemanticContextRequest(BaseModel):
    """批量语义上下文聚合请求"""
    requests: List[SemanticContextRequest] = Field(..., max_items=10, description="批量请求列表")


class AggregationResultResponse(BaseModel):
    """聚合结果响应"""
    enhanced_context: str = Field(..., description="增强后的上下文")
    modules_used: List[str] = Field(..., description="使用的模块列表")
    total_tokens_used: int = Field(..., description="总Token使用量")
    token_budget_remaining: int = Field(..., description="剩余Token预算")
    relevance_scores: Dict[str, float] = Field(..., description="模块相关性评分")
    optimization_summary: Dict[str, Any] = Field(..., description="优化摘要")


@router.post("/aggregate", response_model=BaseResponse[AggregationResultResponse])
async def aggregate_semantic_context(
    request: SemanticContextRequest,
    db: Session = Depends(get_db)
):
    """
    聚合语义上下文
    
    智能聚合五模块元数据，生成最优的语义上下文组合。
    """
    try:
        service = SemanticContextAggregator(db)
        
        # 转换Token预算
        token_budget = None
        if request.token_budget:
            token_budget = TokenBudget(
                total_budget=request.token_budget.total_budget,
                reserved_for_response=request.token_budget.reserved_for_response
            )
        
        # 转换模块优先级
        module_priorities = None
        if request.module_priorities:
            module_priorities = {}
            if request.module_priorities.data_source:
                module_priorities[ModuleType.DATA_SOURCE] = request.module_priorities.data_source
            if request.module_priorities.table_structure:
                module_priorities[ModuleType.TABLE_STRUCTURE] = request.module_priorities.table_structure
            if request.module_priorities.table_relation:
                module_priorities[ModuleType.TABLE_RELATION] = request.module_priorities.table_relation
            if request.module_priorities.dictionary:
                module_priorities[ModuleType.DICTIONARY] = request.module_priorities.dictionary
            if request.module_priorities.knowledge:
                module_priorities[ModuleType.KNOWLEDGE] = request.module_priorities.knowledge
        
        # 执行聚合
        result = await service.aggregate_semantic_context(
            user_question=request.user_question,
            table_ids=request.table_ids,
            include_global=request.include_global,
            token_budget=token_budget,
            module_priorities=module_priorities
        )
        
        response_data = AggregationResultResponse(
            enhanced_context=result.enhanced_context,
            modules_used=result.modules_used,
            total_tokens_used=result.total_tokens_used,
            token_budget_remaining=result.token_budget_remaining,
            relevance_scores=result.relevance_scores,
            optimization_summary=result.optimization_summary
        )
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="语义上下文聚合成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语义上下文聚合失败: {str(e)}")


@router.post("/batch-aggregate", response_model=BaseResponse[List[AggregationResultResponse]])
async def batch_aggregate_semantic_context(
    request: BatchSemanticContextRequest,
    db: Session = Depends(get_db)
):
    """
    批量聚合语义上下文
    
    批量处理多个语义上下文聚合请求。
    """
    try:
        if len(request.requests) > 10:
            raise HTTPException(status_code=400, detail="批量请求数量不能超过10个")
        
        service = SemanticContextAggregator(db)
        results = []
        
        for req in request.requests:
            # 转换Token预算
            token_budget = None
            if req.token_budget:
                token_budget = TokenBudget(
                    total_budget=req.token_budget.total_budget,
                    reserved_for_response=req.token_budget.reserved_for_response
                )
            
            # 转换模块优先级
            module_priorities = None
            if req.module_priorities:
                module_priorities = {}
                if req.module_priorities.data_source:
                    module_priorities[ModuleType.DATA_SOURCE] = req.module_priorities.data_source
                if req.module_priorities.table_structure:
                    module_priorities[ModuleType.TABLE_STRUCTURE] = req.module_priorities.table_structure
                if req.module_priorities.table_relation:
                    module_priorities[ModuleType.TABLE_RELATION] = req.module_priorities.table_relation
                if req.module_priorities.dictionary:
                    module_priorities[ModuleType.DICTIONARY] = req.module_priorities.dictionary
                if req.module_priorities.knowledge:
                    module_priorities[ModuleType.KNOWLEDGE] = req.module_priorities.knowledge
            
            # 执行聚合
            result = await service.aggregate_semantic_context(
                user_question=req.user_question,
                table_ids=req.table_ids,
                include_global=req.include_global,
                token_budget=token_budget,
                module_priorities=module_priorities
            )
            
            response_data = AggregationResultResponse(
                enhanced_context=result.enhanced_context,
                modules_used=result.modules_used,
                total_tokens_used=result.total_tokens_used,
                token_budget_remaining=result.token_budget_remaining,
                relevance_scores=result.relevance_scores,
                optimization_summary=result.optimization_summary
            )
            
            results.append(response_data)
        
        return BaseResponse(
            success=True,
            data=results,
            message=f"批量语义上下文聚合成功，处理了{len(results)}个请求"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量语义上下文聚合失败: {str(e)}")


@router.get("/modules", response_model=BaseResponse[Dict[str, Any]])
async def get_available_modules():
    """
    获取可用的语义模块信息
    
    返回所有可用的语义模块类型和优先级选项。
    """
    try:
        modules_info = {
            "module_types": [module_type.value for module_type in ModuleType],
            "priority_levels": [priority.value for priority in ContextPriority],
            "default_priorities": {
                ModuleType.TABLE_STRUCTURE.value: ContextPriority.CRITICAL.value,
                ModuleType.DICTIONARY.value: ContextPriority.HIGH.value,
                ModuleType.DATA_SOURCE.value: ContextPriority.HIGH.value,
                ModuleType.TABLE_RELATION.value: ContextPriority.MEDIUM.value,
                ModuleType.KNOWLEDGE.value: ContextPriority.MEDIUM.value
            },
            "token_budget_defaults": {
                "total_budget": 4000,
                "reserved_for_response": 1000,
                "available_for_context": 3000
            }
        }
        
        return BaseResponse(
            success=True,
            data=modules_info,
            message="获取模块信息成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模块信息失败: {str(e)}")


@router.post("/clear-cache", response_model=BaseResponse[Dict[str, str]])
async def clear_aggregator_cache(
    db: Session = Depends(get_db)
):
    """
    清空聚合器缓存
    
    清空语义上下文聚合器的所有缓存数据。
    """
    try:
        service = SemanticContextAggregator(db)
        service.clear_cache()
        
        return BaseResponse(
            success=True,
            data={"status": "cleared"},
            message="聚合器缓存清空成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


@router.get("/health", response_model=BaseResponse[Dict[str, Any]])
async def health_check(
    db: Session = Depends(get_db)
):
    """
    健康检查
    
    检查语义上下文聚合引擎的健康状态。
    """
    try:
        service = SemanticContextAggregator(db)
        
        # 执行简单的聚合测试
        test_result = await service.aggregate_semantic_context(
            user_question="测试问题",
            table_ids=None,
            include_global=False,
            token_budget=TokenBudget(total_budget=1000, reserved_for_response=500)
        )
        
        health_info = {
            "status": "healthy",
            "modules_available": len([module_type.value for module_type in ModuleType]),
            "test_aggregation": {
                "success": True,
                "modules_used": len(test_result.modules_used),
                "tokens_used": test_result.total_tokens_used
            },
            "cache_status": "active"
        }
        
        return BaseResponse(
            success=True,
            data=health_info,
            message="语义上下文聚合引擎健康"
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            data={"status": "unhealthy", "error": str(e)},
            message="语义上下文聚合引擎异常"
        )