"""
意图识别上下文管理 API - 任务 5.1.2
提供基于对话历史的意图推断、动态调整和澄清机制的API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..services.intent_context_manager import (
    get_intent_context_manager,
    IntentContextManager,
    ContextualIntentResult,
    ClarificationRequest,
    IntentAdjustment,
    ConfidenceLevel,
    ClarificationReason
)
from ..services.intent_recognition_service import IntentType
from ..schemas.base_schema import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intent-context", tags=["Intent Context Management"])


# Pydantic 模型
from pydantic import BaseModel, Field


class ContextualIntentRequest(BaseModel):
    """上下文意图识别请求"""
    session_id: str = Field(..., description="会话ID")
    user_question: str = Field(..., description="用户问题")
    force_clarification: bool = Field(False, description="是否强制澄清")


class ContextualIntentResponse(BaseModel):
    """上下文意图识别响应"""
    intent_type: str = Field(..., description="意图类型")
    confidence: float = Field(..., description="置信度")
    confidence_level: str = Field(..., description="置信度级别")
    reasoning: str = Field(..., description="推理过程")
    context_influence: Dict[str, Any] = Field(..., description="上下文影响")
    adjustment_history: List[Dict[str, Any]] = Field(..., description="调整历史")
    clarification_needed: bool = Field(..., description="是否需要澄清")
    clarification_request: Optional[Dict[str, Any]] = Field(None, description="澄清请求")


class IntentConfirmationRequest(BaseModel):
    """意图确认请求"""
    session_id: str = Field(..., description="会话ID")
    confirmed_intent: str = Field(..., description="确认的意图类型")
    user_feedback: Optional[str] = Field(None, description="用户反馈")


class SessionStatsResponse(BaseModel):
    """会话统计响应"""
    session_id: str = Field(..., description="会话ID")
    total_intents: int = Field(..., description="总意图数量")
    intent_distribution: Dict[str, float] = Field(..., description="意图分布")
    last_intent: Optional[str] = Field(None, description="最后意图")
    last_confidence: Optional[float] = Field(None, description="最后置信度")
    last_update: Optional[datetime] = Field(None, description="最后更新时间")
    adjustment_count: int = Field(..., description="调整次数")


@router.post("/identify", response_model=BaseResponse[ContextualIntentResponse])
async def identify_intent_with_context(
    request: ContextualIntentRequest,
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    基于上下文识别意图
    
    Args:
        request: 上下文意图识别请求
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[ContextualIntentResponse]: 上下文意图识别结果
    """
    try:
        logger.info(f"Processing contextual intent identification for session {request.session_id}")
        
        # 执行上下文意图识别
        result = await manager.identify_intent_with_context(
            session_id=request.session_id,
            user_question=request.user_question,
            force_clarification=request.force_clarification
        )
        
        # 转换调整历史
        adjustment_history = []
        for adj in result.adjustment_history:
            adjustment_history.append({
                "original_intent": adj.original_intent.value,
                "adjusted_intent": adj.adjusted_intent.value,
                "reason": adj.reason,
                "confidence_change": adj.confidence_change,
                "timestamp": adj.timestamp.isoformat(),
                "user_confirmed": adj.user_confirmed
            })
        
        # 转换澄清请求
        clarification_request = None
        if result.clarification_request:
            clarification_request = {
                "session_id": result.clarification_request.session_id,
                "original_question": result.clarification_request.original_question,
                "detected_intent": result.clarification_request.detected_intent.value,
                "confidence": result.clarification_request.confidence,
                "reason": result.clarification_request.reason.value,
                "clarification_questions": result.clarification_request.clarification_questions,
                "suggested_intents": [
                    {"intent": intent.value, "confidence": conf}
                    for intent, conf in result.clarification_request.suggested_intents
                ],
                "timestamp": result.clarification_request.timestamp.isoformat()
            }
        
        response_data = ContextualIntentResponse(
            intent_type=result.intent_result.intent.value,
            confidence=result.intent_result.confidence,
            confidence_level=result.confidence_level.value,
            reasoning=result.intent_result.reasoning,
            context_influence=result.context_influence,
            adjustment_history=adjustment_history,
            clarification_needed=result.clarification_needed,
            clarification_request=clarification_request
        )
        
        logger.info(f"Contextual intent identification completed for session {request.session_id}: "
                   f"{result.intent_result.intent.value} (confidence: {result.intent_result.confidence:.2f})")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="上下文意图识别成功"
        )
        
    except Exception as e:
        logger.error(f"Contextual intent identification failed for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上下文意图识别失败: {str(e)}")


@router.post("/confirm", response_model=BaseResponse[bool])
async def confirm_intent_adjustment(
    request: IntentConfirmationRequest,
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    确认意图调整
    
    Args:
        request: 意图确认请求
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[bool]: 确认结果
    """
    try:
        logger.info(f"Processing intent confirmation for session {request.session_id}")
        
        # 验证意图类型
        try:
            confirmed_intent = IntentType(request.confirmed_intent)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的意图类型: {request.confirmed_intent}")
        
        # 确认意图调整
        success = await manager.confirm_intent_adjustment(
            session_id=request.session_id,
            confirmed_intent=confirmed_intent,
            user_feedback=request.user_feedback
        )
        
        if success:
            logger.info(f"Intent adjustment confirmed for session {request.session_id}: {confirmed_intent.value}")
            return BaseResponse(
                success=True,
                data=True,
                message="意图调整确认成功"
            )
        else:
            logger.warning(f"Intent adjustment confirmation failed for session {request.session_id}")
            return BaseResponse(
                success=False,
                data=False,
                message="意图调整确认失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intent confirmation failed for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"意图确认失败: {str(e)}")


@router.get("/session/{session_id}/stats", response_model=BaseResponse[SessionStatsResponse])
async def get_session_intent_stats(
    session_id: str,
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    获取会话意图统计
    
    Args:
        session_id: 会话ID
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[SessionStatsResponse]: 会话统计信息
    """
    try:
        logger.info(f"Getting intent stats for session {session_id}")
        
        # 获取会话统计
        stats = manager.get_session_intent_stats(session_id)
        
        response_data = SessionStatsResponse(
            session_id=stats["session_id"],
            total_intents=stats["total_intents"],
            intent_distribution=stats["intent_distribution"],
            last_intent=stats["last_intent"].value if stats["last_intent"] else None,
            last_confidence=stats["last_confidence"],
            last_update=stats["last_update"],
            adjustment_count=stats["adjustment_count"]
        )
        
        logger.info(f"Intent stats retrieved for session {session_id}: {stats['total_intents']} intents")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message="会话意图统计获取成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get intent stats for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话意图统计失败: {str(e)}")


@router.get("/session/{session_id}/adjustments", response_model=BaseResponse[List[Dict[str, Any]]])
async def get_session_adjustments(
    session_id: str,
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    获取会话意图调整历史
    
    Args:
        session_id: 会话ID
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[List[Dict[str, Any]]]: 调整历史列表
    """
    try:
        logger.info(f"Getting intent adjustments for session {session_id}")
        
        # 获取调整历史
        adjustments = manager._get_adjustment_history(session_id)
        
        # 转换为字典格式
        adjustment_list = []
        for adj in adjustments:
            adjustment_list.append({
                "original_intent": adj.original_intent.value,
                "adjusted_intent": adj.adjusted_intent.value,
                "reason": adj.reason,
                "confidence_change": adj.confidence_change,
                "timestamp": adj.timestamp.isoformat(),
                "user_confirmed": adj.user_confirmed
            })
        
        logger.info(f"Retrieved {len(adjustment_list)} adjustments for session {session_id}")
        
        return BaseResponse(
            success=True,
            data=adjustment_list,
            message="意图调整历史获取成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get intent adjustments for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取意图调整历史失败: {str(e)}")


@router.delete("/session/{session_id}", response_model=BaseResponse[bool])
async def clear_session_context(
    session_id: str,
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    清除会话上下文
    
    Args:
        session_id: 会话ID
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[bool]: 清除结果
    """
    try:
        logger.info(f"Clearing context for session {session_id}")
        
        # 清除会话状态
        if session_id in manager.session_states:
            del manager.session_states[session_id]
            
        logger.info(f"Context cleared for session {session_id}")
        
        return BaseResponse(
            success=True,
            data=True,
            message="会话上下文清除成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to clear context for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除会话上下文失败: {str(e)}")


@router.get("/confidence-levels", response_model=BaseResponse[Dict[str, float]])
async def get_confidence_levels(
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    获取置信度级别配置
    
    Args:
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[Dict[str, float]]: 置信度级别配置
    """
    try:
        logger.info("Getting confidence level configuration")
        
        confidence_config = {
            level.value: threshold
            for level, threshold in manager.confidence_thresholds.items()
        }
        
        return BaseResponse(
            success=True,
            data=confidence_config,
            message="置信度级别配置获取成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get confidence levels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取置信度级别配置失败: {str(e)}")


@router.get("/clarification-reasons", response_model=BaseResponse[List[str]])
async def get_clarification_reasons():
    """
    获取澄清原因列表
    
    Returns:
        BaseResponse[List[str]]: 澄清原因列表
    """
    try:
        logger.info("Getting clarification reasons")
        
        reasons = [reason.value for reason in ClarificationReason]
        
        return BaseResponse(
            success=True,
            data=reasons,
            message="澄清原因列表获取成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get clarification reasons: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取澄清原因列表失败: {str(e)}")


@router.get("/health", response_model=BaseResponse[Dict[str, Any]])
async def health_check(
    manager: IntentContextManager = Depends(get_intent_context_manager)
):
    """
    健康检查
    
    Args:
        manager: 意图上下文管理器
        
    Returns:
        BaseResponse[Dict[str, Any]]: 健康状态信息
    """
    try:
        logger.info("Performing intent context manager health check")
        
        # 检查服务状态
        active_sessions = len(manager.session_states)
        
        # 检查依赖服务
        dependencies_status = {
            "intent_service": manager.intent_service is not None,
            "context_manager": manager.context_manager is not None,
            "ai_service": manager.ai_service is not None
        }
        
        health_info = {
            "status": "healthy",
            "active_sessions": active_sessions,
            "dependencies": dependencies_status,
            "configuration": {
                "context_weight": manager.context_weight,
                "history_window": manager.history_window,
                "confidence_thresholds": {
                    level.value: threshold
                    for level, threshold in manager.confidence_thresholds.items()
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Intent context manager health check completed: {active_sessions} active sessions")
        
        return BaseResponse(
            success=True,
            data=health_info,
            message="意图上下文管理器健康检查成功"
        )
        
    except Exception as e:
        logger.error(f"Intent context manager health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")