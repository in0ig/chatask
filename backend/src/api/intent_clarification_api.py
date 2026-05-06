"""
意图澄清API

提供意图澄清相关的REST API端点。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..services.intent_clarification_service import IntentClarificationService
from ..services.ai_model_service import AIModelService
from ..services.prompt_manager import PromptManager

router = APIRouter(prefix="/api/intent-clarification", tags=["intent-clarification"])

# 全局服务实例
_clarification_service: Optional[IntentClarificationService] = None


def get_clarification_service() -> IntentClarificationService:
    """获取意图澄清服务实例"""
    global _clarification_service
    if _clarification_service is None:
        # 初始化依赖服务（允许为None以支持降级策略）
        try:
            from ..config.ai_config import get_ai_config
            ai_config = get_ai_config()
            ai_service = AIModelService(config=ai_config)
        except Exception:
            ai_service = None
        
        try:
            prompt_manager = PromptManager()
        except Exception:
            prompt_manager = None
        
        _clarification_service = IntentClarificationService(
            ai_model_service=ai_service,
            prompt_manager=prompt_manager
        )
    return _clarification_service


# ============= Request/Response Models =============

class TableSelectionInfo(BaseModel):
    """表选择信息"""
    table_id: Optional[str] = None
    table_name: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    relevant_fields: List[str] = Field(default_factory=list)


class TableSelection(BaseModel):
    """表选择结果"""
    selected_tables: List[TableSelectionInfo]
    overall_reasoning: str = ""


class GenerateClarificationRequest(BaseModel):
    """生成澄清问题请求"""
    original_question: str = Field(..., description="用户原始问题")
    table_selection: TableSelection = Field(..., description="智能选表结果")
    context: Optional[Dict[str, Any]] = Field(default=None, description="额外上下文")


class ClarificationQuestionResponse(BaseModel):
    """澄清问题响应"""
    question: str
    options: List[str]
    question_type: str
    reasoning: str
    importance: float


class ClarificationResultResponse(BaseModel):
    """澄清结果响应"""
    clarification_needed: bool
    questions: List[ClarificationQuestionResponse]
    summary: str
    confidence: float
    reasoning: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfirmClarificationRequest(BaseModel):
    """确认澄清请求"""
    session_id: str = Field(..., description="会话ID")
    user_responses: List[Dict[str, Any]] = Field(..., description="用户响应")


class ModifyClarificationRequest(BaseModel):
    """修改澄清请求"""
    session_id: str = Field(..., description="会话ID")
    modifications: Dict[str, Any] = Field(..., description="修改内容")


class IntentUpdateRequest(BaseModel):
    """意图更新请求"""
    session_id: str = Field(..., description="会话ID")
    user_feedbacks: List[Dict[str, Any]] = Field(..., description="用户反馈列表")


class RollbackRequest(BaseModel):
    """回溯请求"""
    session_id: str = Field(..., description="会话ID")
    round_number: int = Field(..., description="目标轮次", ge=1)


class ClarificationSessionResponse(BaseModel):
    """澄清会话响应"""
    session_id: str
    original_question: str
    clarification_result: Optional[ClarificationResultResponse]
    user_responses: List[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str


# ============= API Endpoints =============

@router.post("/generate", response_model=ClarificationResultResponse)
async def generate_clarification(
    request: GenerateClarificationRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    生成意图澄清问题
    
    根据用户问题和智能选表结果，生成需要澄清的问题。
    """
    try:
        # 转换table_selection为字典
        table_selection_dict = {
            "selected_tables": [
                {
                    "table_id": t.table_id,
                    "table_name": t.table_name,
                    "relevance_score": t.relevance_score,
                    "reasoning": t.reasoning,
                    "relevant_fields": t.relevant_fields
                }
                for t in request.table_selection.selected_tables
            ],
            "overall_reasoning": request.table_selection.overall_reasoning
        }
        
        result = await service.generate_clarification(
            original_question=request.original_question,
            table_selection=table_selection_dict,
            context=request.context
        )
        
        # 创建会话
        session_id = f"clarification_{datetime.now().timestamp()}"
        service.create_session(
            session_id=session_id,
            original_question=request.original_question,
            table_selection=table_selection_dict,
            clarification_result=result
        )
        
        return ClarificationResultResponse(
            clarification_needed=result.clarification_needed,
            questions=[
                ClarificationQuestionResponse(
                    question=q.question,
                    options=q.options,
                    question_type=q.question_type,
                    reasoning=q.reasoning,
                    importance=q.importance
                )
                for q in result.questions
            ],
            summary=result.summary,
            confidence=result.confidence,
            reasoning=result.reasoning,
            metadata={"session_id": session_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成澄清问题失败: {str(e)}")


@router.post("/confirm")
async def confirm_clarification(
    request: ConfirmClarificationRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    确认澄清结果
    
    用户确认澄清问题的答案。
    """
    try:
        result = service.confirm_clarification(
            session_id=request.session_id,
            user_responses=request.user_responses
        )
        
        return {
            "success": True,
            "message": "澄清已确认",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"确认澄清失败: {str(e)}")


@router.post("/modify")
async def modify_clarification(
    request: ModifyClarificationRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    修改澄清内容
    
    用户修改澄清问题的答案或提供额外信息。
    """
    try:
        result = service.modify_clarification(
            session_id=request.session_id,
            modifications=request.modifications
        )
        
        return {
            "success": True,
            "message": "澄清已修改",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改澄清失败: {str(e)}")


@router.get("/session/{session_id}", response_model=ClarificationSessionResponse)
async def get_session(
    session_id: str,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    获取澄清会话信息
    
    查询指定会话的详细信息。
    """
    try:
        session = service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        
        clarification_result = None
        if session.clarification_result:
            clarification_result = ClarificationResultResponse(
                clarification_needed=session.clarification_result.clarification_needed,
                questions=[
                    ClarificationQuestionResponse(
                        question=q.question,
                        options=q.options,
                        question_type=q.question_type,
                        reasoning=q.reasoning,
                        importance=q.importance
                    )
                    for q in session.clarification_result.questions
                ],
                summary=session.clarification_result.summary,
                confidence=session.clarification_result.confidence,
                reasoning=session.clarification_result.reasoning
            )
        
        return ClarificationSessionResponse(
            session_id=session.session_id,
            original_question=session.original_question,
            clarification_result=clarification_result,
            user_responses=session.user_responses,
            status=session.status,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    获取会话历史
    
    查询指定会话的完整历史记录。
    """
    try:
        history = service.get_session_history(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话历史失败: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    获取统计信息
    
    查询意图澄清服务的统计数据。
    """
    try:
        stats = service.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/health")
async def health_check(
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    健康检查
    
    检查意图澄清服务的运行状态。
    """
    try:
        stats = service.get_statistics()
        
        return {
            "status": "healthy",
            "service": "intent_clarification",
            "active_sessions": stats.get("active_sessions", 0),
            "total_clarifications": stats.get("total_clarifications", 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "intent_clarification",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/process-feedback")
async def process_clarification_feedback(
    request: IntentUpdateRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    处理澄清反馈
    
    处理用户的澄清反馈，生成结构化反馈和意图更新。
    """
    try:
        feedbacks, intent_updates = service.process_clarification_feedback(
            session_id=request.session_id,
            user_feedbacks=request.user_feedbacks
        )
        
        return {
            "success": True,
            "message": "反馈处理完成",
            "data": {
                "feedbacks": [
                    {
                        "question_id": f.question_id,
                        "user_response": f.user_response,
                        "response_type": f.response_type,
                        "confidence": f.confidence,
                        "timestamp": f.timestamp.isoformat()
                    }
                    for f in feedbacks
                ],
                "intent_updates": [
                    {
                        "type": u.update_type.value,
                        "original_value": u.original_value,
                        "updated_value": u.updated_value,
                        "reasoning": u.reasoning,
                        "confidence": u.confidence,
                        "timestamp": u.timestamp.isoformat()
                    }
                    for u in intent_updates
                ]
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理反馈失败: {str(e)}")


@router.post("/update-intent")
async def update_intent(
    request: IntentUpdateRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    更新意图
    
    根据用户反馈更新原始意图。
    """
    try:
        # 先处理反馈生成意图更新
        _, intent_updates = service.process_clarification_feedback(
            session_id=request.session_id,
            user_feedbacks=request.user_feedbacks
        )
        
        # 应用意图更新
        updated_intent = service.update_intent(
            session_id=request.session_id,
            intent_updates=intent_updates
        )
        
        return {
            "success": True,
            "message": "意图更新完成",
            "data": {
                "updated_intent": updated_intent,
                "intent_updates": [
                    {
                        "type": u.update_type.value,
                        "original_value": u.original_value,
                        "updated_value": u.updated_value,
                        "reasoning": u.reasoning,
                        "confidence": u.confidence
                    }
                    for u in intent_updates
                ]
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新意图失败: {str(e)}")


@router.get("/session/{session_id}/clarification-history")
async def get_clarification_history(
    session_id: str,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    获取澄清历史记录
    
    查询指定会话的完整澄清历史，包括所有轮次的澄清和意图更新。
    """
    try:
        history = service.get_clarification_history(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "total_rounds": len(history),
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取澄清历史失败: {str(e)}")


@router.post("/rollback")
async def rollback_to_round(
    request: RollbackRequest,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    回溯到指定轮次
    
    将会话状态回溯到指定的澄清轮次。
    """
    try:
        result = service.rollback_to_round(
            session_id=request.session_id,
            round_number=request.round_number
        )
        
        return {
            "success": True,
            "message": f"已回溯到第 {request.round_number} 轮",
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回溯失败: {str(e)}")


@router.get("/session/{session_id}/optimize")
async def optimize_clarification_strategy(
    session_id: str,
    service: IntentClarificationService = Depends(get_clarification_service)
):
    """
    优化澄清策略
    
    分析会话历史，提供澄清策略优化建议。
    """
    try:
        result = service.optimize_clarification_strategy(session_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化策略失败: {str(e)}")
