"""
对话管理服务 - 基于Gemini语义影子模式
实现会话状态管理和持久化
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.dialogue_session_model import DialogueSession, SessionStatus
from src.services.context_manager import (
    ContextManager, 
    get_context_manager,
    SessionContext,
    CloudHistoryMessage,
    LocalHistoryMessage
)
from src.database import get_db


logger = logging.getLogger(__name__)


class DialogueManager:
    """对话管理服务"""
    
    def __init__(self, db: Session, context_manager: Optional[ContextManager] = None):
        self.db = db
        self.context_manager = context_manager or get_context_manager()
        self.default_archive_days = 30
        self.default_cleanup_days = 90
    
    def create_session(
        self, 
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        auto_archive: bool = True,
        archive_after_days: int = 30
    ) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            title: 会话标题
            description: 会话描述
            auto_archive: 是否自动归档
            archive_after_days: 多少天后归档
            
        Returns:
            会话信息
        """
        try:
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 在内存中创建会话上下文
            context = self.context_manager.create_session(session_id)
            
            # 在数据库中创建会话记录
            db_session = DialogueSession(
                session_id=session_id,
                user_id=user_id,
                status=SessionStatus.ACTIVE,
                title=title or f"会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description=description,
                context_data={},
                cloud_messages=[],
                local_messages=[],
                message_count=0,
                total_tokens=0,
                error_count=0,
                auto_archive=auto_archive,
                archive_after_days=archive_after_days
            )
            
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            
            logger.info(f"创建新会话: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "session": db_session.to_dict()
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息
        """
        try:
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return None
            
            # 更新最后活动时间
            db_session.last_activity_at = datetime.now()
            self.db.commit()
            
            return db_session.to_dict()
            
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}")
            return None
    
    def update_session_status(
        self, 
        session_id: str, 
        status: SessionStatus,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新会话状态
        
        Args:
            session_id: 会话ID
            status: 新状态
            reason: 状态变更原因
            
        Returns:
            更新结果
        """
        try:
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return {
                    "success": False,
                    "error": "会话不存在"
                }
            
            old_status = db_session.status
            db_session.status = status
            db_session.updated_at = datetime.now()
            
            # 根据状态更新时间戳
            if status == SessionStatus.CLOSED:
                db_session.closed_at = datetime.now()
            elif status == SessionStatus.ARCHIVED:
                db_session.archived_at = datetime.now()
            
            # 记录状态变更
            if not db_session.context_data:
                db_session.context_data = {}
            
            if 'status_history' not in db_session.context_data:
                db_session.context_data['status_history'] = []
            
            db_session.context_data['status_history'].append({
                'from': old_status.value,
                'to': status.value,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            
            self.db.commit()
            
            logger.info(f"会话 {session_id} 状态更新: {old_status.value} -> {status.value}")
            
            return {
                "success": True,
                "session_id": session_id,
                "old_status": old_status.value,
                "new_status": status.value
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新会话状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def pause_session(self, session_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        暂停会话
        
        Args:
            session_id: 会话ID
            reason: 暂停原因
            
        Returns:
            操作结果
        """
        return self.update_session_status(session_id, SessionStatus.PAUSED, reason)
    
    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """
        恢复会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            操作结果
        """
        try:
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return {
                    "success": False,
                    "error": "会话不存在"
                }
            
            if db_session.status != SessionStatus.PAUSED:
                return {
                    "success": False,
                    "error": f"只能恢复暂停的会话，当前状态: {db_session.status.value}"
                }
            
            # 恢复内存中的会话上下文
            self._restore_session_context(session_id, db_session)
            
            # 更新状态
            return self.update_session_status(session_id, SessionStatus.ACTIVE, "用户恢复会话")
            
        except Exception as e:
            logger.error(f"恢复会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_session(self, session_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            reason: 关闭原因
            
        Returns:
            操作结果
        """
        try:
            # 持久化会话上下文
            self.persist_session_context(session_id)
            
            # 更新状态
            result = self.update_session_status(session_id, SessionStatus.CLOSED, reason)
            
            # 从内存中移除会话上下文
            if session_id in self.context_manager.sessions:
                del self.context_manager.sessions[session_id]
            
            return result
            
        except Exception as e:
            logger.error(f"关闭会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def persist_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        持久化会话上下文到数据库
        
        Args:
            session_id: 会话ID
            
        Returns:
            操作结果
        """
        try:
            # 获取内存中的会话上下文
            context = self.context_manager.get_session(session_id)
            if not context:
                return {
                    "success": False,
                    "error": "会话上下文不存在"
                }
            
            # 获取数据库会话记录
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return {
                    "success": False,
                    "error": "数据库会话记录不存在"
                }
            
            # 持久化云端消息
            cloud_messages = [msg.to_dict() for msg in context.cloud_messages]
            db_session.cloud_messages = cloud_messages
            
            # 持久化本地消息
            local_messages = [msg.to_dict() for msg in context.local_messages]
            db_session.local_messages = local_messages
            
            # 更新统计信息
            db_session.message_count = len(context.cloud_messages)
            db_session.total_tokens = context.total_tokens
            
            # 持久化上下文数据
            db_session.context_data = {
                'compressed_context': context.compressed_context,
                'created_at': context.created_at.isoformat(),
                'last_activity': context.last_activity.isoformat()
            }
            
            db_session.updated_at = datetime.now()
            self.db.commit()
            
            logger.info(f"持久化会话上下文: {session_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "message_count": db_session.message_count,
                "total_tokens": db_session.total_tokens
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"持久化会话上下文失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _restore_session_context(self, session_id: str, db_session: DialogueSession):
        """
        从数据库恢复会话上下文到内存
        
        Args:
            session_id: 会话ID
            db_session: 数据库会话记录
        """
        try:
            # 创建新的会话上下文
            context = self.context_manager.create_session(session_id)
            
            # 恢复云端消息
            if db_session.cloud_messages:
                for msg_dict in db_session.cloud_messages:
                    # 重建CloudHistoryMessage对象
                    # 这里简化处理，实际应该完整恢复对象
                    pass
            
            # 恢复本地消息
            if db_session.local_messages:
                for msg_dict in db_session.local_messages:
                    # 重建LocalHistoryMessage对象
                    pass
            
            # 恢复上下文数据
            if db_session.context_data:
                context.compressed_context = db_session.context_data.get('compressed_context')
            
            context.total_tokens = db_session.total_tokens
            
            logger.info(f"恢复会话上下文: {session_id}")
            
        except Exception as e:
            logger.error(f"恢复会话上下文失败: {str(e)}")
            raise
    
    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        列出会话
        
        Args:
            user_id: 用户ID（可选）
            status: 会话状态（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            会话列表
        """
        try:
            query = self.db.query(DialogueSession)
            
            # 过滤条件
            if user_id:
                query = query.filter(DialogueSession.user_id == user_id)
            
            if status:
                query = query.filter(DialogueSession.status == status)
            
            # 排序和分页
            query = query.order_by(DialogueSession.last_activity_at.desc())
            total = query.count()
            sessions = query.limit(limit).offset(offset).all()
            
            return {
                "success": True,
                "total": total,
                "limit": limit,
                "offset": offset,
                "sessions": [s.to_dict() for s in sessions]
            }
            
        except Exception as e:
            logger.error(f"列出会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sessions": []
            }
    
    def archive_old_sessions(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        归档旧会话
        
        Args:
            days: 归档多少天前的会话（默认使用会话配置）
            
        Returns:
            归档结果
        """
        try:
            archived_count = 0
            
            # 查找需要归档的会话
            query = self.db.query(DialogueSession).filter(
                and_(
                    DialogueSession.status == SessionStatus.CLOSED,
                    DialogueSession.auto_archive == True
                )
            )
            
            sessions = query.all()
            
            for session in sessions:
                # 使用会话配置的归档天数
                archive_days = days or session.archive_after_days
                cutoff_date = datetime.now() - timedelta(days=archive_days)
                
                if session.closed_at and session.closed_at < cutoff_date:
                    # 持久化上下文（如果还没有）
                    if session.session_id in self.context_manager.sessions:
                        self.persist_session_context(session.session_id)
                    
                    # 更新状态为已归档
                    session.status = SessionStatus.ARCHIVED
                    session.archived_at = datetime.now()
                    archived_count += 1
            
            self.db.commit()
            
            logger.info(f"归档了 {archived_count} 个会话")
            
            return {
                "success": True,
                "archived_count": archived_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"归档会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "archived_count": 0
            }
    
    def cleanup_archived_sessions(self, days: int = 90) -> Dict[str, Any]:
        """
        清理已归档的旧会话
        
        Args:
            days: 清理多少天前归档的会话
            
        Returns:
            清理结果
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 查找需要清理的会话
            sessions = self.db.query(DialogueSession).filter(
                and_(
                    DialogueSession.status == SessionStatus.ARCHIVED,
                    DialogueSession.archived_at < cutoff_date
                )
            ).all()
            
            deleted_count = len(sessions)
            
            # 删除会话
            for session in sessions:
                self.db.delete(session)
            
            self.db.commit()
            
            logger.info(f"清理了 {deleted_count} 个归档会话")
            
            return {
                "success": True,
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理归档会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            统计信息
        """
        try:
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return {
                    "success": False,
                    "error": "会话不存在"
                }
            
            # 获取内存中的会话统计
            memory_stats = self.context_manager.get_session_stats(session_id)
            
            # 合并数据库和内存统计
            stats = {
                "session_id": session_id,
                "status": db_session.status.value,
                "message_count": db_session.message_count,
                "total_tokens": db_session.total_tokens,
                "error_count": db_session.error_count,
                "created_at": db_session.created_at.isoformat(),
                "last_activity_at": db_session.last_activity_at.isoformat(),
                "duration_hours": (datetime.now() - db_session.created_at).total_seconds() / 3600,
                "memory_stats": memory_stats
            }
            
            return {
                "success": True,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"获取会话统计失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def migrate_session(
        self, 
        session_id: str, 
        target_user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        迁移会话到另一个用户
        
        Args:
            session_id: 会话ID
            target_user_id: 目标用户ID
            reason: 迁移原因
            
        Returns:
            迁移结果
        """
        try:
            db_session = self.db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not db_session:
                return {
                    "success": False,
                    "error": "会话不存在"
                }
            
            old_user_id = db_session.user_id
            db_session.user_id = target_user_id
            db_session.updated_at = datetime.now()
            
            # 记录迁移历史
            if not db_session.context_data:
                db_session.context_data = {}
            
            if 'migration_history' not in db_session.context_data:
                db_session.context_data['migration_history'] = []
            
            db_session.context_data['migration_history'].append({
                'from_user': old_user_id,
                'to_user': target_user_id,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })
            
            self.db.commit()
            
            logger.info(f"会话 {session_id} 从用户 {old_user_id} 迁移到 {target_user_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "old_user_id": old_user_id,
                "new_user_id": target_user_id
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"迁移会话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def get_dialogue_manager(db: Session) -> DialogueManager:
    """获取对话管理器实例"""
    return DialogueManager(db)
