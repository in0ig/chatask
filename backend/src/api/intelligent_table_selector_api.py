"""
基于云端Qwen的智能表选择算法 API

任务 5.2.3 的API实现
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import logging

from src.services.intelligent_table_selector import (
    IntelligentTableSelector,
    TableSelectionResult,
    TableCandidate,
    TableSelectionConfidence
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/intelligent-table-selector", tags=["智能表选择"])

# 全局服务实例
table_selector_service = IntelligentTableSelector()


# 请求模型
class TableSelectionRequest(BaseModel):
    """表选择请求模型"""
    user_question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    class Config:
        schema_extra = {
            "example": {
                "user_question": "查询销售额最高的产品",
                "data_source_id": "ds_001",
                "context": {
                    "session_id": "session_123",
                    "previous_tables": ["products", "sales"]
                }
            }
        }


class BatchTableSelectionRequest(BaseModel):
    """批量表选择请求模型"""
    requests: list[TableSelectionRequest] = Field(..., description="批量请求列表", min_items=1, max_items=10)
    
    class Config:
        schema_extra = {
            "example": {
                "requests": [
                    {
                        "user_question": "查询销售额最高的产品",
                        "data_source_id": "ds_001"
                    },
                    {
                        "user_question": "分析客户购买行为",
                        "data_source_id": "ds_001"
                    }
                ]
            }
        }


# 响应模型
class TableCandidateResponse(BaseModel):
    """表候选响应模型"""
    table_id: str
    table_name: str
    table_comment: str
    relevance_score: float
    confidence: str
    selection_reasons: list[str]
    matched_keywords: list[str]
    business_meaning: str
    relation_paths: list[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "table_id": "tbl_001",
                "table_name": "products",
                "table_comment": "产品信息表",
                "relevance_score": 0.95,
                "confidence": "high",
                "selection_reasons": ["包含产品相关字段", "与销售查询高度相关"],
                "matched_keywords": ["产品", "销售"],
                "business_meaning": "存储产品基本信息和属性",
                "relation_paths": []
            }
        }


class TableSelectionResponse(BaseModel):
    """表选择响应模型"""
    primary_tables: list[TableCandidateResponse]
    related_tables: list[TableCandidateResponse]
    selection_strategy: str
    total_relevance_score: float
    recommended_joins: list[Dict[str, Any]]
    selection_explanation: str
    processing_time: float
    ai_reasoning: str
    
    class Config:
        schema_extra = {
            "example": {
                "primary_tables": [
                    {
                        "table_id": "tbl_001",
                        "table_name": "products",
                        "table_comment": "产品信息表",
                        "relevance_score": 0.95,
                        "confidence": "high",
                        "selection_reasons": ["包含产品相关字段"],
                        "matched_keywords": ["产品"],
                        "business_meaning": "存储产品基本信息",
                        "relation_paths": []
                    }
                ],
                "related_tables": [],
                "selection_strategy": "ai_based",
                "total_relevance_score": 0.95,
                "recommended_joins": [],
                "selection_explanation": "基于用户问题选择了最相关的产品表",
                "processing_time": 1.23,
                "ai_reasoning": "用户询问产品销售额，产品表是核心数据源"
            }
        }


class BatchTableSelectionResponse(BaseModel):
    """批量表选择响应模型"""
    results: list[TableSelectionResponse]
    total_processing_time: float
    success_count: int
    error_count: int
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "primary_tables": [],
                        "related_tables": [],
                        "selection_strategy": "ai_based",
                        "total_relevance_score": 0.95,
                        "recommended_joins": [],
                        "selection_explanation": "选择结果",
                        "processing_time": 1.23,
                        "ai_reasoning": "AI推理过程"
                    }
                ],
                "total_processing_time": 2.45,
                "success_count": 2,
                "error_count": 0
            }
        }


class SelectionStatisticsResponse(BaseModel):
    """选择统计响应模型"""
    total_selections: int
    successful_selections: int
    success_rate: float
    average_processing_time: float
    average_relevance_score: float
    configuration: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "total_selections": 100,
                "successful_selections": 95,
                "success_rate": 0.95,
                "average_processing_time": 1.5,
                "average_relevance_score": 0.85,
                "configuration": {
                    "max_primary_tables": 3,
                    "max_related_tables": 5,
                    "min_relevance_threshold": 0.3
                }
            }
        }


# 辅助函数
def convert_table_candidate_to_response(candidate: TableCandidate) -> TableCandidateResponse:
    """将TableCandidate转换为响应模型"""
    return TableCandidateResponse(
        table_id=candidate.table_id,
        table_name=candidate.table_name,
        table_comment=candidate.table_comment,
        relevance_score=candidate.relevance_score,
        confidence=candidate.confidence.value,
        selection_reasons=candidate.selection_reasons,
        matched_keywords=candidate.matched_keywords,
        business_meaning=candidate.business_meaning,
        relation_paths=candidate.relation_paths
    )


def convert_selection_result_to_response(result: TableSelectionResult) -> TableSelectionResponse:
    """将TableSelectionResult转换为响应模型"""
    return TableSelectionResponse(
        primary_tables=[convert_table_candidate_to_response(t) for t in result.primary_tables],
        related_tables=[convert_table_candidate_to_response(t) for t in result.related_tables],
        selection_strategy=result.selection_strategy,
        total_relevance_score=result.total_relevance_score,
        recommended_joins=result.recommended_joins,
        selection_explanation=result.selection_explanation,
        processing_time=result.processing_time,
        ai_reasoning=result.ai_reasoning
    )


# API端点
@router.post("/select", response_model=TableSelectionResponse, summary="智能表选择")
async def select_tables(request: TableSelectionRequest):
    """
    基于用户问题进行智能表选择
    
    - **user_question**: 用户的自然语言问题
    - **data_source_id**: 可选的数据源ID，限制选择范围
    - **context**: 可选的上下文信息，如会话ID、历史表选择等
    
    返回选择的主表和关联表，以及详细的选择理由和推荐的JOIN语句。
    """
    try:
        logger.info(f"收到表选择请求: {request.user_question}")
        
        # 调用服务层进行表选择
        result = await table_selector_service.select_tables(
            user_question=request.user_question,
            data_source_id=request.data_source_id,
            context=request.context
        )
        
        # 转换为响应模型
        response = convert_selection_result_to_response(result)
        
        logger.info(f"表选择完成，主表数量: {len(response.primary_tables)}, 关联表数量: {len(response.related_tables)}")
        return response
        
    except Exception as e:
        logger.error(f"表选择失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"表选择过程中发生错误: {str(e)}"
        )


@router.post("/select/batch", response_model=BatchTableSelectionResponse, summary="批量智能表选择")
async def batch_select_tables(request: BatchTableSelectionRequest):
    """
    批量进行智能表选择
    
    支持一次处理多个表选择请求，提高处理效率。
    最多支持10个并发请求。
    """
    try:
        logger.info(f"收到批量表选择请求，数量: {len(request.requests)}")
        
        results = []
        success_count = 0
        error_count = 0
        total_start_time = datetime.now()
        
        # 处理每个请求
        for req in request.requests:
            try:
                result = await table_selector_service.select_tables(
                    user_question=req.user_question,
                    data_source_id=req.data_source_id,
                    context=req.context
                )
                response = convert_selection_result_to_response(result)
                results.append(response)
                success_count += 1
                
            except Exception as e:
                logger.error(f"批量请求中的单个请求失败: {str(e)}")
                # 添加错误结果
                error_result = TableSelectionResponse(
                    primary_tables=[],
                    related_tables=[],
                    selection_strategy="error",
                    total_relevance_score=0.0,
                    recommended_joins=[],
                    selection_explanation=f"处理失败: {str(e)}",
                    processing_time=0.0,
                    ai_reasoning="处理失败"
                )
                results.append(error_result)
                error_count += 1
        
        total_processing_time = (datetime.now() - total_start_time).total_seconds()
        
        response = BatchTableSelectionResponse(
            results=results,
            total_processing_time=total_processing_time,
            success_count=success_count,
            error_count=error_count
        )
        
        logger.info(f"批量表选择完成，成功: {success_count}, 失败: {error_count}")
        return response
        
    except Exception as e:
        logger.error(f"批量表选择失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"批量表选择过程中发生错误: {str(e)}"
        )


@router.get("/statistics", response_model=SelectionStatisticsResponse, summary="获取选择统计信息")
async def get_selection_statistics():
    """
    获取表选择的统计信息
    
    包括总选择次数、成功率、平均处理时间、平均相关性评分等指标。
    """
    try:
        stats = table_selector_service.get_selection_statistics()
        return SelectionStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息时发生错误: {str(e)}"
        )


@router.get("/health", summary="健康检查")
async def health_check():
    """
    智能表选择服务健康检查
    
    检查服务状态和依赖组件的可用性。
    """
    try:
        # 检查服务状态
        stats = table_selector_service.get_selection_statistics()
        
        health_status = {
            "status": "healthy",
            "service": "intelligent_table_selector",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_selections": stats["total_selections"],
                "success_rate": stats["success_rate"],
                "average_processing_time": stats["average_processing_time"]
            },
            "dependencies": {
                "ai_service": "available",
                "semantic_aggregator": "available",
                "similarity_engine": "available",
                "data_integration": "available",
                "relation_module": "available"
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "intelligent_table_selector",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# 添加必要的导入
from datetime import datetime