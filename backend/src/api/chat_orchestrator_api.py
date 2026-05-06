"""
对话流程编排引擎API
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from src.services.chat_orchestrator import get_chat_orchestrator, ChatStage, ChatIntent
from src.schemas.base_schema import BaseResponse
from src.utils.request_logger import request_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["对话编排"])


class HistoryMessage(BaseModel):
    """历史消息模型"""
    role: str  # 'user' 或 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """对话请求模型"""
    user_question: str
    data_source_id: Optional[str] = None
    selected_tables: Optional[List[str]] = None  # 🆕 用户选择的表 ID 列表
    history_messages: Optional[List[HistoryMessage]] = None
    response_language: Optional[str] = None  # 🆕 AI 回复语言，'en' 或 'zh'（默认 'zh'）


@router.post("/start/{session_id}")
async def start_chat(
    session_id: str,
    request: Optional[ChatRequest] = Body(None),
    user_question: Optional[str] = Query(None, description="用户问题（兼容旧版）"),
    data_source_id: Optional[str] = Query(None, description="数据源ID（UUID，兼容旧版）")
) -> BaseResponse:
    """
    开始对话流程（支持历史消息上下文）
    
    Args:
        session_id: 会话ID
        request: 对话请求体（包含用户问题、数据源ID、历史消息）
        user_question: 用户问题（Query参数，兼容旧版）
        data_source_id: 数据源ID（Query参数，兼容旧版）
        
    Returns:
        对话结果
    """
    try:
        # 兼容两种调用方式：Body 和 Query
        if request:
            question = request.user_question
            source_id = request.data_source_id
            selected_tables = request.selected_tables  # 🆕 获取选择的表 ID
            history = request.history_messages
            response_language = request.response_language or 'zh'  # 🆕 获取回复语言
        else:
            question = user_question
            source_id = data_source_id
            selected_tables = None  # Query 方式不支持传递表 ID
            history = None
            response_language = 'zh'  # 默认中文
        
        # 📝 记录 API 请求
        request_logger.log_api_request(
            endpoint=f"POST /api/chat/start/{session_id}",
            method="POST",
            body={
                "session_id": session_id,
                "user_question": question,
                "data_source_id": source_id,
                "selected_tables": selected_tables,  # 🆕 记录选择的表
                "history_messages_count": len(history) if history else 0
            }
        )
        
        logger.info(f"=== 开始对话请求 ===")
        logger.info(f"会话ID: {session_id}")
        logger.info(f"用户问题: {question}")
        logger.info(f"数据源ID: {source_id}")
        logger.info(f"选择的表: {selected_tables}")  # 🆕 记录选择的表
        logger.info(f"历史消息数量: {len(history) if history else 0}")
        
        orchestrator = get_chat_orchestrator()
        logger.info(f"获取 ChatOrchestrator 实例成功")
        
        # 将 Pydantic 模型转换为字典列表
        history_dicts = None
        if history:
            history_dicts = [msg.dict() for msg in history]
            logger.info(f"历史消息: {history_dicts}")
        
        result = await orchestrator.start_chat(
            session_id, 
            question, 
            source_id,
            history_messages=history_dicts,
            selected_tables=selected_tables,  # 🆕 传递选择的表 ID
            response_language=response_language  # 🆕 传递回复语言
        )
        logger.info(f"对话处理完成，结果: {result}")
        
        # 📝 记录 API 响应
        request_logger.log_api_response(
            endpoint=f"POST /api/chat/start/{session_id}",
            status_code=200,
            response={
                "success": result["success"],
                "has_analysis": "analysis" in result,
                "has_sql": "sql" in result,
                "stage": result.get("stage", "unknown")
            }
        )
        
        return BaseResponse(
            success=result["success"],
            data=result,
            message="对话开始成功" if result["success"] else "对话开始失败"
        )
        
    except Exception as e:
        logger.error(f"开始对话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"开始对话失败: {str(e)}")


@router.post("/continue/{session_id}")
async def continue_chat(
    session_id: str,
    user_response: str = Query(..., description="用户回复")
) -> BaseResponse:
    """
    继续对话（处理用户回复）
    
    Args:
        session_id: 会话ID
        user_response: 用户回复
        
    Returns:
        对话结果
    """
    try:
        orchestrator = get_chat_orchestrator()
        result = await orchestrator.continue_chat(session_id, user_response)
        
        return BaseResponse(
            success=result["success"],
            data=result,
            message="对话继续成功" if result["success"] else "对话继续失败"
        )
        
    except Exception as e:
        logger.error(f"继续对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"继续对话失败: {str(e)}")


@router.post("/followup/{session_id}")
async def handle_followup(
    session_id: str,
    followup_question: str = Query(..., description="追问问题")
) -> BaseResponse:
    """
    处理数据追问
    
    Args:
        session_id: 会话ID
        followup_question: 追问问题
        
    Returns:
        追问结果
    """
    try:
        orchestrator = get_chat_orchestrator()
        result = await orchestrator.continue_chat(session_id, followup_question)
        
        return BaseResponse(
            success=result["success"],
            data=result,
            message="追问处理成功" if result["success"] else "追问处理失败"
        )
        
    except Exception as e:
        logger.error(f"处理追问失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理追问失败: {str(e)}")


@router.get("/status/{session_id}")
async def get_session_status(session_id: str) -> BaseResponse:
    """
    获取会话状态
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话状态信息
    """
    try:
        orchestrator = get_chat_orchestrator()
        status = orchestrator.get_session_status(session_id)
        
        return BaseResponse(
            success=True,
            data=status,
            message="获取会话状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取会话状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话状态失败: {str(e)}")


@router.get("/status")
async def get_all_sessions_status() -> BaseResponse:
    """
    获取所有会话状态
    
    Returns:
        所有会话状态信息
    """
    try:
        orchestrator = get_chat_orchestrator()
        status = orchestrator.get_all_sessions_status()
        
        return BaseResponse(
            success=True,
            data=status,
            message="获取所有会话状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取所有会话状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取所有会话状态失败: {str(e)}")


@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str) -> BaseResponse:
    """
    清理会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        清理结果
    """
    try:
        orchestrator = get_chat_orchestrator()
        success = orchestrator.cleanup_session(session_id)
        
        return BaseResponse(
            success=success,
            data={"session_id": session_id, "cleaned": success},
            message="会话清理成功" if success else "会话不存在或已清理"
        )
        
    except Exception as e:
        logger.error(f"清理会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理会话失败: {str(e)}")


@router.post("/batch-start")
async def batch_start_chats(
    requests: list[Dict[str, Any]] = Body(..., description="批量对话请求")
) -> BaseResponse:
    """
    批量开始对话
    
    Args:
        requests: 批量对话请求列表，每个请求包含session_id, user_question, data_source_id
        
    Returns:
        批量对话结果
    """
    try:
        orchestrator = get_chat_orchestrator()
        results = []
        
        for request in requests:
            session_id = request.get("session_id")
            user_question = request.get("user_question")
            data_source_id = request.get("data_source_id")
            
            if not session_id or not user_question:
                results.append({
                    "session_id": session_id,
                    "success": False,
                    "error": "缺少必要参数"
                })
                continue
            
            try:
                result = await orchestrator.start_chat(session_id, user_question, data_source_id)
                results.append(result)
            except Exception as e:
                results.append({
                    "session_id": session_id,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get("success", False))
        
        return BaseResponse(
            success=True,
            data={
                "total": len(requests),
                "success_count": success_count,
                "failed_count": len(requests) - success_count,
                "results": results
            },
            message=f"批量对话处理完成，成功 {success_count}/{len(requests)} 个"
        )
        
    except Exception as e:
        logger.error(f"批量开始对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量开始对话失败: {str(e)}")


@router.post("/retry/{session_id}")
async def retry_chat(
    session_id: str,
    stage: Optional[str] = Query(None, description="重试阶段")
) -> BaseResponse:
    """
    重试对话流程
    
    Args:
        session_id: 会话ID
        stage: 重试阶段（可选）
        
    Returns:
        重试结果
    """
    try:
        orchestrator = get_chat_orchestrator()
        
        # 获取会话状态
        status = orchestrator.get_session_status(session_id)
        if not status["exists"]:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 发送重试指令
        result = await orchestrator.continue_chat(session_id, "重试")
        
        return BaseResponse(
            success=result["success"],
            data=result,
            message="重试成功" if result["success"] else "重试失败"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重试对话失败: {str(e)}")


@router.get("/stages")
async def get_chat_stages() -> BaseResponse:
    """
    获取对话阶段列表
    
    Returns:
        对话阶段信息
    """
    try:
        stages = [
            {
                "value": stage.value,
                "name": stage.name,
                "description": {
                    "intent_recognition": "意图识别",
                    "table_selection": "智能选表",
                    "intent_clarification": "意图澄清",
                    "sql_generation": "SQL生成",
                    "sql_execution": "SQL执行",
                    "data_analysis": "数据分析",
                    "result_presentation": "结果展示",
                    "error_handling": "错误处理",
                    "completed": "完成"
                }.get(stage.value, stage.value)
            }
            for stage in ChatStage
        ]
        
        return BaseResponse(
            success=True,
            data={"stages": stages},
            message="获取对话阶段成功"
        )
        
    except Exception as e:
        logger.error(f"获取对话阶段失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话阶段失败: {str(e)}")


@router.get("/intents")
async def get_chat_intents() -> BaseResponse:
    """
    获取对话意图列表
    
    Returns:
        对话意图信息
    """
    try:
        intents = [
            {
                "value": intent.value,
                "name": intent.name,
                "description": {
                    "smart_query": "智能问数",
                    "report_generation": "生成报告",
                    "data_followup": "数据追问",
                    "clarification": "澄清确认",
                    "unknown": "未知意图"
                }.get(intent.value, intent.value)
            }
            for intent in ChatIntent
        ]
        
        return BaseResponse(
            success=True,
            data={"intents": intents},
            message="获取对话意图成功"
        )
        
    except Exception as e:
        logger.error(f"获取对话意图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取对话意图失败: {str(e)}")


@router.get("/health")
async def health_check() -> BaseResponse:
    """
    健康检查
    
    Returns:
        服务健康状态
    """
    try:
        orchestrator = get_chat_orchestrator()
        status = orchestrator.get_all_sessions_status()
        
        return BaseResponse(
            success=True,
            data={
                "status": "healthy",
                "service": "对话流程编排引擎",
                "total_sessions": status["total_sessions"],
                "timestamp": "2024-01-01T00:00:00Z"
            },
            message="服务运行正常"
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")