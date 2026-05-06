"""
会话管理服务
处理会话的创建、更新、查询和删除
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from src.models.dialogue_session_model import DialogueSession, SessionStatus
from src.services.ai_model_service import AIModelService, get_ai_service

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""
    
    def __init__(self):
        """初始化会话服务"""
        try:
            self.ai_service = get_ai_service()
        except RuntimeError:
            logger.warning("全局 AI 服务未初始化，标题生成功能将不可用")
            self.ai_service = None
    
    async def create_session(
        self, 
        db: Session, 
        session_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> DialogueSession:
        """
        创建新会话
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            user_id: 用户ID（可选）
            title: 会话标题（可选）
            
        Returns:
            创建的会话对象
        """
        try:
            # 检查会话是否已存在
            existing_session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if existing_session:
                logger.info(f"会话 {session_id} 已存在，返回现有会话")
                return existing_session
            
            # 创建新会话
            new_session = DialogueSession(
                session_id=session_id,
                user_id=user_id,
                title=title or "新对话",
                status=SessionStatus.ACTIVE,
                context_data={},
                cloud_messages=[],
                local_messages=[],
                message_count=0,
                total_tokens=0,
                error_count=0
            )
            
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            
            logger.info(f"✅ 创建会话成功: {session_id}")
            return new_session
            
        except Exception as e:
            logger.error(f"创建会话失败: {str(e)}", exc_info=True)
            db.rollback()
            raise
    
    async def generate_session_title(
        self,
        db: Session,
        session_id: str,
        first_message: str,
        language: str = "zh"
    ) -> str:
        """
        使用本地AI生成会话标题

        Args:
            db: 数据库会话
            session_id: 会话ID
            first_message: 首条消息内容
            language: 标题语言，'zh' 或 'en'

        Returns:
            生成的标题
        """
        try:
            if not self.ai_service:
                logger.warning("AI 服务不可用，使用默认标题")
                return self._generate_default_title(first_message)

            # 根据语言构建不同的 prompt
            if language == "en":
                prompt = f"""Generate a concise title (10-50 characters) for the following user question:

User question: {first_message}

Requirements:
1. The title should be concise and capture the core of the question
2. Keep it between 10-50 characters
3. Use English
4. Return only the title text, nothing else

Title:"""
            else:
                prompt = f"""请为以下用户问题生成一个简洁的对话标题（10-30个字符）：

用户问题: {first_message}

要求：
1. 标题要简洁明了，概括问题核心
2. 长度控制在10-30个字符
3. 使用中文
4. 只返回标题文本，不要其他内容

标题："""
            
            # 调用模型生成标题（走路由配置）
            response = await self.ai_service.call_model(
                prompt,
                stage="summary",
                session_id=session_id
            )
            
            if response["success"]:
                title = response["content"].strip()
                # 清理标题（移除引号、换行等）
                title = title.replace('"', '').replace("'", '').replace('\n', ' ').strip()
                # 限制长度
                if len(title) > 30:
                    title = title[:27] + "..."
                elif len(title) < 5:
                    title = self._generate_default_title(first_message)
                
                # 更新数据库
                session = db.query(DialogueSession).filter(
                    DialogueSession.session_id == session_id
                ).first()
                
                if session:
                    session.title = title
                    db.commit()
                    logger.info(f"✅ 生成会话标题: {title}")
                
                return title
            else:
                logger.warning(f"AI标题生成失败: {response.get('error')}")
                return self._generate_default_title(first_message)
                
        except Exception as e:
            logger.error(f"生成会话标题失败: {str(e)}", exc_info=True)
            return self._generate_default_title(first_message)
    
    def _generate_default_title(self, message: str) -> str:
        """生成默认标题（基于消息内容）"""
        # 取前20个字符作为标题
        title = message[:20].strip()
        if len(message) > 20:
            title += "..."
        return title or "新对话"
    
    def get_session(
        self,
        db: Session,
        session_id: str
    ) -> Optional[DialogueSession]:
        """
        获取会话
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            
        Returns:
            会话对象或None
        """
        try:
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            return session
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}")
            return None
    
    def list_sessions(
        self,
        db: Session,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DialogueSession]:
        """
        获取会话列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID（可选）
            status: 会话状态（可选）
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            会话列表
        """
        try:
            logger.info(f"🔍 Service: 开始查询会话列表 - user_id={user_id}, status={status}, limit={limit}, offset={offset}")
            query = db.query(DialogueSession)
            
            # 过滤条件
            filters = []
            if user_id:
                filters.append(DialogueSession.user_id == user_id)
                logger.info(f"  添加过滤条件: user_id={user_id}")
            if status:
                filters.append(DialogueSession.status == status)
                logger.info(f"  添加过滤条件: status={status}")
            
            if filters:
                query = query.filter(and_(*filters))
            
            # 排序和分页
            sessions = query.order_by(
                desc(DialogueSession.last_activity_at)
            ).limit(limit).offset(offset).all()
            
            logger.info(f"✅ Service: 查询到 {len(sessions)} 个会话")
            for s in sessions:
                logger.info(f"  - {s.session_id}: {s.title}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
            return []
    
    async def update_session(
        self,
        db: Session,
        session_id: str,
        title: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Optional[DialogueSession]:
        """
        更新会话
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            title: 新标题（可选）
            status: 新状态（可选）
            context_data: 上下文数据（可选）
            
        Returns:
            更新后的会话对象或None
        """
        try:
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return None
            
            # 更新字段
            if title is not None:
                session.title = title
            if status is not None:
                session.status = status
                if status == SessionStatus.CLOSED:
                    session.closed_at = datetime.now()
                elif status == SessionStatus.ARCHIVED:
                    session.archived_at = datetime.now()
            if context_data is not None:
                session.context_data = context_data
            
            session.last_activity_at = datetime.now()
            
            db.commit()
            db.refresh(session)
            
            logger.info(f"✅ 更新会话成功: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"更新会话失败: {str(e)}", exc_info=True)
            db.rollback()
            return None
    
    async def add_message_to_session(
        self,
        db: Session,
        session_id: str,
        role: str,
        content: str,
        message_type: str = "cloud",
        stages: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        添加消息到会话
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            role: 消息角色（user/assistant）
            content: 消息内容
            message_type: 消息类型（cloud/local）
            stages: 流式输出阶段数据（可选）
            
        Returns:
            是否成功
        """
        try:
            from sqlalchemy.orm.attributes import flag_modified
            
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return False
            
            # 构建消息对象
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 如果有 stages 数据，添加到消息中
            if stages is not None:
                message["stages"] = stages
            
            # 添加到对应的消息列表
            if message_type == "cloud":
                if session.cloud_messages is None:
                    session.cloud_messages = []
                session.cloud_messages.append(message)
                # 标记字段已修改，确保 SQLAlchemy 保存更改
                flag_modified(session, "cloud_messages")
            else:
                if session.local_messages is None:
                    session.local_messages = []
                
                # 🔥 修复重复 user 消息：仅在时间戳非常接近时去重（同一次请求的重复保存）
                # 注意：不能按内容去重，因为多轮对话中用户可能发送相同的问题
                # 场景：context_manager 在对话开始时已保存 user 消息，
                #       前端 complete 事件也会保存相同的 user 消息，导致重复
                # 策略：检查最近 5 秒内是否已有相同内容的 user 消息（同一次请求）
                if role == "user":
                    from datetime import timezone
                    now = datetime.now()
                    for m in session.local_messages:
                        if m.get("role") != "user":
                            continue
                        if m.get("content", "").strip() != content.strip():
                            continue
                        # 检查时间戳是否在 5 秒内（同一次请求的重复）
                        try:
                            msg_ts = datetime.fromisoformat(m.get("timestamp", ""))
                            diff = abs((now - msg_ts).total_seconds())
                            if diff < 5:
                                logger.info(f"⏭️ 跳过重复 user 消息（5秒内相同内容）: {content[:50]!r}")
                                return True  # 视为成功，不报错
                        except Exception:
                            pass
                
                session.local_messages.append(message)
                # 标记字段已修改，确保 SQLAlchemy 保存更改
                flag_modified(session, "local_messages")
            
            # 更新统计
            session.message_count += 1
            session.last_activity_at = datetime.now()
            
            db.commit()
            
            logger.info(f"✅ 已添加消息到会话 {session_id}: role={role}, type={message_type}, stages={len(stages) if stages else 0}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    async def delete_session(
        self,
        db: Session,
        session_id: str
    ) -> bool:
        """
        删除会话
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        try:
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return False
            
            db.delete(session)
            db.commit()
            
            logger.info(f"✅ 删除会话成功: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除会话失败: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    async def archive_old_sessions(
        self,
        db: Session,
        days: int = 30
    ) -> int:
        """
        归档旧会话
        
        Args:
            db: 数据库会话
            days: 多少天前的会话
            
        Returns:
            归档的会话数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            sessions = db.query(DialogueSession).filter(
                and_(
                    DialogueSession.last_activity_at < cutoff_date,
                    DialogueSession.status == SessionStatus.ACTIVE,
                    DialogueSession.auto_archive == True
                )
            ).all()
            
            count = 0
            for session in sessions:
                session.status = SessionStatus.ARCHIVED
                session.archived_at = datetime.now()
                count += 1
            
            db.commit()
            
            logger.info(f"✅ 归档了 {count} 个旧会话")
            return count
            
        except Exception as e:
            logger.error(f"归档旧会话失败: {str(e)}", exc_info=True)
            db.rollback()
            return 0
    
    async def persist_context_manager_history(
        self,
        db: Session,
        session_id: str,
        cloud_messages: List[Dict[str, Any]],
        local_messages: List[Dict[str, Any]],
        total_tokens: int = 0
    ) -> bool:
        """
        持久化 ContextManager 的历史对话到数据库
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            cloud_messages: 云端历史消息列表
            local_messages: 本地历史消息列表
            total_tokens: Token总数
            
        Returns:
            是否成功
        """
        try:
            from sqlalchemy.orm.attributes import flag_modified
            
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在，创建新会话")
                session = await self.create_session(db, session_id)
            
            # cloud_messages 直接覆盖（云端消息不含 stages，覆盖安全）
            session.cloud_messages = cloud_messages
            flag_modified(session, "cloud_messages")
            
            # 🔥 修复：local_messages 保护策略
            # 前端在 complete 事件时会保存带完整 stages 的 user + assistant 消息到 local_messages
            # context_manager 的消息没有 stages，如果直接覆盖或追加会破坏已保存的完整数据
            #
            # 策略：检查数据库中是否已有带 stages 的 assistant 消息
            # - 如果有：说明前端已经保存了完整数据，跳过 local_messages 更新，保护已有数据
            # - 如果没有：说明是首次持久化或前端尚未保存，使用 context_manager 的数据
            existing_local = session.local_messages or []
            
            # 检查是否已有带 stages 的 assistant 消息（前端保存的完整消息）
            has_stages_messages = any(
                m.get("role") == "assistant" and m.get("stages") and len(m.get("stages", [])) > 0
                for m in existing_local
            )
            
            if has_stages_messages:
                # 数据库中已有带 stages 的完整消息，跳过 local_messages 更新
                # 避免 context_manager 的无 stages 消息覆盖或追加破坏完整数据
                logger.info(f"✅ 数据库中已有带 stages 的消息，跳过 local_messages 更新，保护完整数据")
                merged_local = existing_local
            else:
                # 数据库中没有带 stages 的消息
                # 只追加数据库中没有的消息
                # 去重策略：对 user 消息，检查时间戳是否在 5 秒内已有相同内容（同一次请求的重复）
                # 注意：不能按内容全局去重，多轮对话中用户可能发送相同的问题
                new_messages = []
                for m in local_messages:
                    if m.get("role") == "user":
                        m_content = m.get("content", "").strip()
                        m_ts_str = m.get("timestamp", "")
                        is_dup = False
                        try:
                            m_ts = datetime.fromisoformat(m_ts_str)
                            for ex in existing_local:
                                if ex.get("role") != "user":
                                    continue
                                if ex.get("content", "").strip() != m_content:
                                    continue
                                ex_ts = datetime.fromisoformat(ex.get("timestamp", ""))
                                if abs((m_ts - ex_ts).total_seconds()) < 5:
                                    is_dup = True
                                    break
                        except Exception:
                            pass
                        if not is_dup:
                            new_messages.append(m)
                    else:
                        new_messages.append(m)
                
                merged_local = existing_local + new_messages
                session.local_messages = merged_local
                flag_modified(session, "local_messages")
                logger.info(f"ℹ️ 数据库中无带 stages 的消息，合并 context_manager 数据（新增 {len(new_messages)} 条）")
            
            # 更新统计信息
            session.message_count = len(cloud_messages)
            session.total_tokens = total_tokens
            session.last_activity_at = datetime.now()
            
            db.commit()
            
            logger.info(f"✅ 持久化历史对话成功: {session_id}, 云端消息={len(cloud_messages)}, 本地消息={len(merged_local)}, tokens={total_tokens}")
            return True
            
        except Exception as e:
            logger.error(f"持久化历史对话失败: {str(e)}", exc_info=True)
            db.rollback()
            return False
    
    async def load_context_manager_history(
        self,
        db: Session,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        从数据库加载历史对话到 ContextManager
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            
        Returns:
            历史对话数据或None
        """
        try:
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return None
            
            history_data = {
                "session_id": session.session_id,
                "cloud_messages": session.cloud_messages or [],
                "local_messages": session.local_messages or [],
                "total_tokens": session.total_tokens or 0,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None
            }
            
            logger.info(f"✅ 加载历史对话成功: {session_id}, 云端消息={len(history_data['cloud_messages'])}, 本地消息={len(history_data['local_messages'])}")
            return history_data
            
        except Exception as e:
            logger.error(f"加载历史对话失败: {str(e)}", exc_info=True)
            return None
    
    async def get_session_history_for_display(
        self,
        db: Session,
        session_id: str,
        message_type: str = "cloud"
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史用于前端展示
        
        Args:
            db: 数据库会话
            session_id: 会话ID
            message_type: 消息类型（cloud/local）
            
        Returns:
            消息列表
        """
        try:
            session = db.query(DialogueSession).filter(
                DialogueSession.session_id == session_id
            ).first()
            
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return []
            
            if message_type == "cloud":
                messages = session.cloud_messages or []
            else:
                messages = session.local_messages or []
            
            logger.info(f"✅ 获取会话历史成功: {session_id}, type={message_type}, count={len(messages)}")
            return messages
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {str(e)}", exc_info=True)
            return []


# 全局实例
_session_service = None

def get_session_service() -> SessionService:
    """获取会话服务实例"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
