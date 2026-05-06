"""
意图识别API - 基于云端Qwen模型的智能意图识别
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging

from ..services.intent_recognition_service import (
    get_intent_service, 
    IntentRecognitionService, 
    IntentResult, 
    IntentType,
    IntentRecognitionError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intent", tags=["意图识别"])


# 请求模型
class IntentRecognitionRequest(BaseModel):
    """意图识别请求"""
    user_question: str = Field(..., description="用户问题", min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    class Config:
        schema_extra = {
            "example": {
                "user_question": "查询最近一个月的销售数据",
                "context": {
                    "conversation_history": [],
                    "user_preferences": {"language": "zh-CN"},
                    "session_state": "active"
                }
            }
        }


# 响应模型
class IntentRecognitionResponse(BaseModel):
    """意图识别响应"""
    intent: str = Field(..., description="识别的意图类型")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="推理过程")
    original_question: str = Field(..., description="原始问题")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    class Config:
        schema_extra = {
            "example": {
                "intent": "query",
                "confidence": 0.95,
                "reasoning": "用户明确要求查询销售数据，属于智能问数类型",
                "original_question": "查询最近一个月的销售数据",
                "metadata": {
                    "processing_time": 1.2,
                    "model_version": "qwen-turbo"
                }
            }
        }


class IntentStatisticsResponse(BaseModel):
    """意图识别统计响应"""
    total_requests: int = Field(..., description="总请求数")
    successful_recognitions: int = Field(..., description="成功识别数")
    failed_recognitions: int = Field(..., description="失败识别数")
    success_rate: float = Field(..., description="成功率")
    failure_rate: float = Field(..., description="失败率")
    avg_confidence: float = Field(..., description="平均置信度")
    avg_response_time: float = Field(..., description="平均响应时间")
    intent_distribution: Dict[str, float] = Field(..., description="意图分布")
    
    class Config:
        schema_extra = {
            "example": {
                "total_requests": 100,
                "successful_recognitions": 95,
                "failed_recognitions": 5,
                "success_rate": 0.95,
                "failure_rate": 0.05,
                "avg_confidence": 0.87,
                "avg_response_time": 1.5,
                "intent_distribution": {
                    "query": 0.7,
                    "report": 0.25,
                    "unknown": 0.05
                }
            }
        }


@router.post("/recognize", response_model=IntentRecognitionResponse)
async def recognize_intent(
    request: IntentRecognitionRequest,
    intent_service: IntentRecognitionService = Depends(get_intent_service)
):
    """
    识别用户问题的意图
    
    - **user_question**: 用户问题（必需）
    - **context**: 上下文信息（可选）
    
    返回识别的意图类型、置信度和推理过程
    """
    try:
        # 调用意图识别服务
        result = await intent_service.identify_intent(
            user_question=request.user_question,
            context=request.context
        )
        
        return IntentRecognitionResponse(
            intent=result.intent.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            original_question=result.original_question,
            metadata=result.metadata
        )
        
    except IntentRecognitionError as e:
        logger.error(f"Intent recognition error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "意图识别失败",
                "message": str(e),
                "original_question": e.original_question
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in intent recognition: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "服务器内部错误",
                "message": "意图识别服务暂时不可用"
            }
        )


@router.get("/statistics", response_model=IntentStatisticsResponse)
async def get_intent_statistics(
    intent_service: IntentRecognitionService = Depends(get_intent_service)
):
    """
    获取意图识别统计信息
    
    返回意图识别的统计数据，包括成功率、平均置信度、意图分布等
    """
    try:
        stats = intent_service.get_intent_statistics()
        
        return IntentStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting intent statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "获取统计信息失败",
                "message": str(e)
            }
        )


@router.post("/statistics/reset")
async def reset_intent_statistics(
    intent_service: IntentRecognitionService = Depends(get_intent_service)
):
    """
    重置意图识别统计信息
    
    清空所有统计数据，重新开始计数
    """
    try:
        intent_service.reset_statistics()
        
        return {
            "success": True,
            "message": "意图识别统计信息已重置"
        }
        
    except Exception as e:
        logger.error(f"Error resetting intent statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "重置统计信息失败",
                "message": str(e)
            }
        )


@router.get("/health")
async def health_check(
    intent_service: IntentRecognitionService = Depends(get_intent_service)
):
    """
    意图识别服务健康检查
    
    检查服务状态和基本配置信息
    """
    try:
        stats = intent_service.get_intent_statistics()
        
        return {
            "status": "healthy",
            "service": "intent_recognition",
            "version": "1.0.0",
            "statistics": {
                "total_requests": stats["total_requests"],
                "success_rate": stats["success_rate"],
                "avg_response_time": stats["avg_response_time"]
            },
            "configuration": {
                "confidence_threshold": intent_service.confidence_threshold,
                "max_retries": intent_service.max_retries
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# 批量意图识别（可选功能）
class BatchIntentRequest(BaseModel):
    """批量意图识别请求"""
    questions: list[str] = Field(..., description="问题列表", min_items=1, max_items=10)
    context: Optional[Dict[str, Any]] = Field(None, description="共享上下文信息")


class BatchIntentResponse(BaseModel):
    """批量意图识别响应"""
    results: list[IntentRecognitionResponse] = Field(..., description="识别结果列表")
    summary: Dict[str, Any] = Field(..., description="批量处理摘要")


@router.post("/recognize/batch", response_model=BatchIntentResponse)
async def recognize_intents_batch(
    request: BatchIntentRequest,
    intent_service: IntentRecognitionService = Depends(get_intent_service)
):
    """
    批量识别多个问题的意图
    
    - **questions**: 问题列表（最多10个）
    - **context**: 共享上下文信息（可选）
    
    返回每个问题的意图识别结果和批量处理摘要
    """
    try:
        results = []
        successful_count = 0
        failed_count = 0
        
        for question in request.questions:
            try:
                result = await intent_service.identify_intent(
                    user_question=question,
                    context=request.context
                )
                
                results.append(IntentRecognitionResponse(
                    intent=result.intent.value,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                    original_question=result.original_question,
                    metadata=result.metadata
                ))
                
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Failed to recognize intent for question '{question}': {str(e)}")
                
                # 添加失败结果
                results.append(IntentRecognitionResponse(
                    intent="unknown",
                    confidence=0.0,
                    reasoning=f"识别失败: {str(e)}",
                    original_question=question,
                    metadata={"error": str(e)}
                ))
                
                failed_count += 1
        
        # 计算批量处理摘要
        total_count = len(request.questions)
        summary = {
            "total_questions": total_count,
            "successful_recognitions": successful_count,
            "failed_recognitions": failed_count,
            "success_rate": successful_count / total_count if total_count > 0 else 0.0,
            "avg_confidence": sum(r.confidence for r in results) / total_count if total_count > 0 else 0.0
        }
        
        return BatchIntentResponse(
            results=results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Batch intent recognition error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "批量意图识别失败",
                "message": str(e)
            }
        )