"""
对话会话管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.services.dialogue_manager import DialogueManager, get_dialogue_manager
from src.schemas.dialogue_session_schema import (
    CreateSessionRequest,
    UpdateSessionStatusRequest,
    MigrateSessionRequest,
    SessionResponse,
    SessionListResponse,
    SessionStatisticsResponse,
    OperationResponse,
    SessionStatusEnum
)
from src.models.dialogue_session_model import SessionStatus


router = APIRouter(prefix="/api/dialogue", tags=["dialogue_session"])


@router.post("/sessions", response_model=OperationResponse)
async def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db)
):
    """
    创建新会话
    
    Args:
        request: 创建会话请求
        db: 数据库会话
        
    Returns:
        创建结果
    """
    manager = get_dialogue_manager(db)
    result = manager.create_session(
        user_id=request.user_id,
        title=request.title,
        description=request.description,
        auto_archive=request.auto_archive,
        archive_after_days=request.archive_after_days
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "创建会话失败"))
    
    return OperationResponse(
        success=True,
        message="会话创建成功",
        data=result
    )


@router.get("/sessions/{session_id}", response_model=OperationResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取会话信息
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        会话信息
    """
    manager = get_dialogue_manager(db)
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return OperationResponse(
        success=True,
        data={"session": session}
    )


@router.put("/sessions/{session_id}/status", response_model=OperationResponse)
async def update_session_status(
    session_id: str,
    request: UpdateSessionStatusRequest,
    db: Session = Depends(get_db)
):
    """
    更新会话状态
    
    Args:
        session_id: 会话ID
        request: 更新请求
        db: 数据库会话
        
    Returns:
        更新结果
    """
    manager = get_dialogue_manager(db)
    
    # 转换枚举
    status_map = {
        SessionStatusEnum.ACTIVE: SessionStatus.ACTIVE,
        SessionStatusEnum.PAUSED: SessionStatus.PAUSED,
        SessionStatusEnum.CLOSED: SessionStatus.CLOSED,
        SessionStatusEnum.ARCHIVED: SessionStatus.ARCHIVED,
        SessionStatusEnum.ERROR: SessionStatus.ERROR
    }
    
    status = status_map[request.status]
    result = manager.update_session_status(session_id, status, request.reason)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "更新状态失败"))
    
    return OperationResponse(
        success=True,
        message="状态更新成功",
        data=result
    )


@router.post("/sessions/{session_id}/pause", response_model=OperationResponse)
async def pause_session(
    session_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    暂停会话
    
    Args:
        session_id: 会话ID
        reason: 暂停原因
        db: 数据库会话
        
    Returns:
        操作结果
    """
    manager = get_dialogue_manager(db)
    result = manager.pause_session(session_id, reason)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "暂停会话失败"))
    
    return OperationResponse(
        success=True,
        message="会话已暂停",
        data=result
    )


@router.post("/sessions/{session_id}/resume", response_model=OperationResponse)
async def resume_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    恢复会话
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    manager = get_dialogue_manager(db)
    result = manager.resume_session(session_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "恢复会话失败"))
    
    return OperationResponse(
        success=True,
        message="会话已恢复",
        data=result
    )


@router.post("/sessions/{session_id}/close", response_model=OperationResponse)
async def close_session(
    session_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    关闭会话
    
    Args:
        session_id: 会话ID
        reason: 关闭原因
        db: 数据库会话
        
    Returns:
        操作结果
    """
    manager = get_dialogue_manager(db)
    result = manager.close_session(session_id, reason)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "关闭会话失败"))
    
    return OperationResponse(
        success=True,
        message="会话已关闭",
        data=result
    )


@router.post("/sessions/{session_id}/persist", response_model=OperationResponse)
async def persist_session_context(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    持久化会话上下文
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        操作结果
    """
    manager = get_dialogue_manager(db)
    result = manager.persist_session_context(session_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "持久化失败"))
    
    return OperationResponse(
        success=True,
        message="上下文已持久化",
        data=result
    )


@router.get("/sessions", response_model=OperationResponse)
async def list_sessions(
    user_id: Optional[str] = Query(None, description="用户ID"),
    status: Optional[SessionStatusEnum] = Query(None, description="会话状态"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    列出会话
    
    Args:
        user_id: 用户ID（可选）
        status: 会话状态（可选）
        limit: 返回数量限制
        offset: 偏移量
        db: 数据库会话
        
    Returns:
        会话列表
    """
    manager = get_dialogue_manager(db)
    
    # 转换枚举
    db_status = None
    if status:
        status_map = {
            SessionStatusEnum.ACTIVE: SessionStatus.ACTIVE,
            SessionStatusEnum.PAUSED: SessionStatus.PAUSED,
            SessionStatusEnum.CLOSED: SessionStatus.CLOSED,
            SessionStatusEnum.ARCHIVED: SessionStatus.ARCHIVED,
            SessionStatusEnum.ERROR: SessionStatus.ERROR
        }
        db_status = status_map[status]
    
    result = manager.list_sessions(
        user_id=user_id,
        status=db_status,
        limit=limit,
        offset=offset
    )
    
    return OperationResponse(
        success=True,
        data=result
    )


@router.get("/sessions/{session_id}/statistics", response_model=SessionStatisticsResponse)
async def get_session_statistics(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取会话统计信息
    
    Args:
        session_id: 会话ID
        db: 数据库会话
        
    Returns:
        统计信息
    """
    manager = get_dialogue_manager(db)
    result = manager.get_session_statistics(session_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "获取统计失败"))
    
    return SessionStatisticsResponse(
        success=True,
        statistics=result.get("statistics")
    )


@router.post("/sessions/{session_id}/migrate", response_model=OperationResponse)
async def migrate_session(
    session_id: str,
    request: MigrateSessionRequest,
    db: Session = Depends(get_db)
):
    """
    迁移会话到另一个用户
    
    Args:
        session_id: 会话ID
        request: 迁移请求
        db: 数据库会话
        
    Returns:
        迁移结果
    """
    manager = get_dialogue_manager(db)
    result = manager.migrate_session(
        session_id,
        request.target_user_id,
        request.reason
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "迁移会话失败"))
    
    return OperationResponse(
        success=True,
        message="会话迁移成功",
        data=result
    )


@router.post("/maintenance/archive", response_model=OperationResponse)
async def archive_old_sessions(
    days: Optional[int] = Query(None, description="归档多少天前的会话"),
    db: Session = Depends(get_db)
):
    """
    归档旧会话
    
    Args:
        days: 归档多少天前的会话
        db: 数据库会话
        
    Returns:
        归档结果
    """
    manager = get_dialogue_manager(db)
    result = manager.archive_old_sessions(days)
    
    return OperationResponse(
        success=True,
        message=f"已归档 {result.get('archived_count', 0)} 个会话",
        data=result
    )


@router.post("/maintenance/cleanup", response_model=OperationResponse)
async def cleanup_archived_sessions(
    days: int = Query(90, description="清理多少天前归档的会话"),
    db: Session = Depends(get_db)
):
    """
    清理已归档的旧会话
    
    Args:
        days: 清理多少天前归档的会话
        db: 数据库会话
        
    Returns:
        清理结果
    """
    manager = get_dialogue_manager(db)
    result = manager.cleanup_archived_sessions(days)
    
    return OperationResponse(
        success=True,
        message=f"已清理 {result.get('deleted_count', 0)} 个归档会话",
        data=result
    )


@router.get("/health", response_model=OperationResponse)
async def health_check():
    """健康检查"""
    return OperationResponse(
        success=True,
        message="对话会话管理服务运行正常"
    )
