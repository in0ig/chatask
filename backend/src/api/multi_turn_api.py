from fastapi import APIRouter, HTTPException, Path, Depends
from typing import Dict, Any, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.services.multi_turn_handler import multi_turn_handler
from src.database import get_db
from src.models.database_models import SessionContext, ConversationMessage
import datetime

# 创建API路由器
router = APIRouter(tags=["Multi-Turn Conversation"])

class MessageRequest(BaseModel):
    content: str
    parent_message_id: str = None

class ConversationHistoryResponse(BaseModel):
    messages: List[Dict]

class MessageResponse(BaseModel):
    message: Dict
    conversation_history: List[Dict]

class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_active: str

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]

# POST /api/sessions/{session_id}/message - 添加消息
@router.post("/{session_id}/message", response_model=MessageResponse)
def add_message(
    session_id: str = Path(..., description="会话ID"),
    request: MessageRequest = None
):
    """
    添加用户消息到指定会话的对话历史
    
    Args:
        session_id: 会话ID
        content: 用户输入的内容
        parent_message_id: 父消息ID（用于构建对话树）
        
    Returns:
        包含新消息和完整对话历史的响应
    """
    try:
        if not request:
            raise HTTPException(status_code=400, detail="Request body is required")
        
        # 添加用户消息
        user_message = multi_turn_handler.add_message(session_id, {
            "role": "user",
            "content": request.content,
            "parent_message_id": request.parent_message_id
        })
        
        # 这里应该调用NLU服务和SQL生成服务来处理用户查询
        # 但根据需求，我们只关注对话管理，所以这里返回模拟的助手回复
        assistant_response = {
            "role": "assistant",
            "content": "我理解了您的查询，正在为您分析数据...",
            "parent_message_id": user_message["id"]
        }
        
        # 添加助手消息
        assistant_message = multi_turn_handler.add_message(session_id, assistant_response)
        
        # 获取完整的对话历史
        conversation_history = multi_turn_handler.get_conversation_history(session_id)
        
        return MessageResponse(
            message={"user": user_message, "assistant": assistant_message},
            conversation_history=conversation_history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

# GET /api/sessions/{session_id}/conversation-history - 获取对话历史
@router.get("/{session_id}/conversation-history", response_model=ConversationHistoryResponse)
def get_conversation_history(
    session_id: str = Path(..., description="会话ID"),
    limit: int = 100
):
    """
    获取指定会话的完整对话历史
    
    Args:
        session_id: 会话ID
        limit: 最大消息数量，默认100
        
    Returns:
        消息列表
    """
    try:
        conversation_history = multi_turn_handler.get_conversation_history(session_id, limit)
        return ConversationHistoryResponse(messages=conversation_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")

# GET /api/sessions/{session_id}/last-message - 获取最后一条消息
@router.get("/{session_id}/last-message", response_model=Dict)
def get_last_message(
    session_id: str = Path(..., description="会话ID")
):
    """
    获取指定会话的最后一条消息
    
    Args:
        session_id: 会话ID
        
    Returns:
        最后一条消息
    """
    try:
        last_message = multi_turn_handler.get_last_message(session_id)
        if not last_message:
            raise HTTPException(status_code=404, detail="No messages found for this session")
        return last_message
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get last message: {str(e)}")

# GET /api/sessions/{session_id}/messages-by-parent/{parent_id} - 获取指定父消息的子消息
@router.get("/{session_id}/messages-by-parent/{parent_message_id}", response_model=List[Dict])
def get_messages_by_parent(
    session_id: str = Path(..., description="会话ID"),
    parent_message_id: str = Path(..., description="父消息ID")
):
    """
    获取指定父消息的所有子消息
    
    Args:
        session_id: 会话ID
        parent_message_id: 父消息ID
        
    Returns:
        子消息列表
    """
    try:
        child_messages = multi_turn_handler.get_messages_by_parent(session_id, parent_message_id)
        return child_messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages by parent: {str(e)}")

# GET /api/sessions/ - 获取会话列表
@router.get("/", response_model=SessionListResponse)
def get_session_list():
    """
    获取所有会话的列表
    
    Returns:
        包含所有会话信息的列表
    """
    try:
        db: Session = next(get_db())
        sessions = db.query(SessionContext).order_by(SessionContext.last_summary_at.desc()).all()
        
        session_list = [
            SessionResponse(
                session_id=session.session_id,
                created_at=session.created_at.isoformat(),
                last_active=session.last_summary_at.isoformat()
            )
            for session in sessions
        ]
        
        return SessionListResponse(sessions=session_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session list: {str(e)}")

# POST /api/sessions/ - 创建新会话
@router.post("/", response_model=SessionResponse)
def create_session():
    """
    创建一个新会话
    
    Returns:
        新创建的会话信息
    """
    try:
        db: Session = next(get_db())
        
        # 生成唯一的会话ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # 创建新的会话记录
        new_session = SessionContext(
            session_id=session_id,
            last_summary_at=datetime.now(),
            created_at=datetime.now()
        )
        
        db.add(new_session)
        db.commit()
        
        return SessionResponse(
            session_id=new_session.session_id,
            created_at=new_session.created_at.isoformat(),
            last_active=new_session.last_summary_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

# DELETE /api/sessions/{session_id} - 删除会话
@router.delete("/{session_id}", response_model=Dict)
def delete_session(
    session_id: str = Path(..., description="会话ID")
):
    """
    删除指定会话及其所有消息
    
    Args:
        session_id: 会话ID
        
    Returns:
        删除状态信息
    """
    try:
        db: Session = next(get_db())
        
        # 查找会话
        session = db.query(SessionContext).filter(SessionContext.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 删除所有相关消息
        db.query(ConversationMessage).filter(ConversationMessage.session_id == session_id).delete()
        
        # 删除会话
        db.delete(session)
        db.commit()
        
        return {"status": "deleted", "session_id": session_id}
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 删除所有相关消息
        db.query(ConversationMessage).filter(ConversationMessage.session_id == session_id).delete()
        
        # 删除会话
        db.delete(session)
        db.commit()
        
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")