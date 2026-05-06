"""
会话管理API
提供会话的CRUD操作接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from sqlalchemy.orm import Session
from src.database import get_db
from src.services.session_service import get_session_service
from src.models.dialogue_session_model import SessionStatus
from src.schemas.base_schema import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    session_id: str
    user_id: Optional[str] = None
    title: Optional[str] = None


class GenerateTitleRequest(BaseModel):
    """生成标题请求"""
    session_id: str
    first_message: str
    language: Optional[str] = "zh"  # 语言：'zh' 或 'en'


class AddMessageRequest(BaseModel):
    """添加消息请求"""
    role: str
    content: str
    message_type: str = "cloud"
    stages: Optional[List[Dict[str, Any]]] = None


@router.post("/create")
async def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    创建新会话
    
    Args:
        request: 创建会话请求（包含 session_id, user_id, title）
        db: 数据库会话
        
    Returns:
        创建的会话信息
    """
    try:
        service = get_session_service()
        session = await service.create_session(db, request.session_id, request.user_id, request.title)
        
        return BaseResponse(
            success=True,
            data=session.to_dict(),
            message="创建会话成功"
        )
        
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.post("/generate-title")
async def generate_session_title(
    request: GenerateTitleRequest,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    生成会话标题
    
    Args:
        request: 生成标题请求（包含 session_id, first_message）
        db: 数据库会话
        
    Returns:
        生成的标题
    """
    try:
        service = get_session_service()
        title = await service.generate_session_title(db, request.session_id, request.first_message, request.language or "zh")
        
        return BaseResponse(
            success=True,
            data={"title": title},
            message="生成标题成功"
        )
        
    except Exception as e:
        logger.error(f"生成标题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成标题失败: {str(e)}")


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    获取会话详情（包含历史消息）
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        会话详情（包含消息）
    """
    try:
        service = get_session_service()
        session = service.get_session(db, session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return BaseResponse(
            success=True,
            data=session.to_dict(include_messages=True),  # 包含消息内容
            message="获取会话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@router.get("/")
async def list_sessions(
    user_id: Optional[str] = Query(None, description="用户ID"),
    status: Optional[str] = Query(None, description="会话状态"),
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取会话列表
    
    Args:
        user_id: 用户ID（可选）
        status: 会话状态（可选）
        limit: 返回数量限制
        offset: 偏移量
        db: 数据库会话
        
    Returns:
        会话列表
    """
    try:
        service = get_session_service()
        
        # 转换状态字符串为枚举
        status_enum = None
        if status:
            try:
                status_enum = SessionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")
        
        sessions = service.list_sessions(db, user_id, status_enum, limit, offset)
        sessions_dict = [s.to_dict() for s in sessions]
        
        result = {
            "success": True,
            "message": "获取会话列表成功",
            "data": {
                "sessions": sessions_dict,
                "total": len(sessions),
                "limit": limit,
                "offset": offset
            }
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    title: Optional[str] = Query(None, description="新标题"),
    status: Optional[str] = Query(None, description="新状态"),
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    更新会话
    
    Args:
        session_id: 会话ID
        title: 新标题（可选）
        status: 新状态（可选）
        db: 数据库会话
        
    Returns:
        更新后的会话信息
    """
    try:
        service = get_session_service()
        
        # 转换状态字符串为枚举
        status_enum = None
        if status:
            try:
                status_enum = SessionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态值: {status}")
        
        session = await service.update_session(db, session_id, title, status_enum)
        
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return BaseResponse(
            success=True,
            data=session.to_dict(),
            message="更新会话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新会话失败: {str(e)}")


@router.post("/{session_id}/messages")
async def add_message(
    session_id: str,
    request: AddMessageRequest,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    添加消息到会话
    
    Args:
        session_id: 会话ID
        request: 添加消息请求（包含 role, content, message_type）
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = get_session_service()
        success = await service.add_message_to_session(
            db, session_id, request.role, request.content, request.message_type, request.stages
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return BaseResponse(
            success=True,
            data={"session_id": session_id},
            message="添加消息成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加消息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加消息失败: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    删除会话
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = get_session_service()
        success = await service.delete_session(db, session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return BaseResponse(
            success=True,
            data={"session_id": session_id},
            message="删除会话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.post("/archive-old")
async def archive_old_sessions(
    days: int = Query(30, description="多少天前的会话"),
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    归档旧会话
    
    Args:
        days: 多少天前的会话
        db: 数据库会话
        
    Returns:
        归档的会话数量
    """
    try:
        service = get_session_service()
        count = await service.archive_old_sessions(db, days)
        
        return BaseResponse(
            success=True,
            data={"archived_count": count},
            message=f"归档了 {count} 个旧会话"
        )
        
    except Exception as e:
        logger.error(f"归档旧会话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档旧会话失败: {str(e)}")


class PersistHistoryRequest(BaseModel):
    """持久化历史对话请求"""
    cloud_messages: List[Dict[str, Any]]
    local_messages: List[Dict[str, Any]]
    total_tokens: int = 0


@router.post("/{session_id}/persist-history")
async def persist_history(
    session_id: str,
    request: PersistHistoryRequest,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    持久化历史对话到数据库
    
    Args:
        session_id: 会话ID
        request: 持久化请求（包含 cloud_messages, local_messages, total_tokens）
        db: 数据库会话
        
    Returns:
        操作结果
    """
    try:
        service = get_session_service()
        success = await service.persist_context_manager_history(
            db, session_id, request.cloud_messages, request.local_messages, request.total_tokens
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="持久化失败")
        
        return BaseResponse(
            success=True,
            data={"session_id": session_id},
            message="持久化历史对话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"持久化历史对话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"持久化历史对话失败: {str(e)}")


@router.get("/{session_id}/load-history")
async def load_history(
    session_id: str,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    从数据库加载历史对话
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        历史对话数据
    """
    try:
        service = get_session_service()
        history_data = await service.load_context_manager_history(db, session_id)
        
        if history_data is None:
            raise HTTPException(status_code=404, detail="会话不存在或无历史数据")
        
        return BaseResponse(
            success=True,
            data=history_data,
            message="加载历史对话成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"加载历史对话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"加载历史对话失败: {str(e)}")


@router.get("/{session_id}/history-display")
async def get_history_for_display(
    session_id: str,
    message_type: str = Query("cloud", description="消息类型（cloud/local）"),
    db: Session = Depends(get_db)
) -> BaseResponse:
    """
    获取会话历史用于前端展示
    
    Args:
        session_id: 会话ID
        message_type: 消息类型（cloud/local）
        db: 数据库会话
        
    Returns:
        消息列表
    """
    try:
        service = get_session_service()
        messages = await service.get_session_history_for_display(db, session_id, message_type)
        
        return BaseResponse(
            success=True,
            data={"messages": messages, "count": len(messages)},
            message="获取会话历史成功"
        )
        
    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话历史失败: {str(e)}")
