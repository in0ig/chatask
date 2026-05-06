import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.database_models import ConversationMessage, SessionContext
from src.utils import get_db_session as get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiTurnHandler:
    """
    多轮对话处理服务，负责消息的保存、检索和对话历史管理
    """
    
    def __init__(self, test_mode: bool = False):
        """
        初始化多轮对话处理器
        
        Args:
            test_mode (bool): 是否在测试模式下运行。在测试模式下，不会访问数据库，而是使用内存存储
        """
        self.test_mode = test_mode
        # 在测试模式下，使用内存存储消息
        self.test_messages = {}
        
    def _get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话消息，支持测试模式"""
        if self.test_mode:
            if session_id not in self.test_messages:
                self.test_messages[session_id] = []
            return self.test_messages[session_id]
        else:
            # 在生产模式下，从数据库获取
            db: Session = next(get_db())
            messages = db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.turn.asc()).all()
            
            return [
                {
                    "id": msg.id,
                    "turn": msg.turn,
                    "role": msg.role.value,
                    "content": msg.content,
                    "parent_message_id": msg.parent_message_id,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                for msg in messages
            ]
    
    def _get_max_turn(self, session_id: str) -> int:
        """获取最大turn值，支持测试模式"""
        if self.test_mode:
            messages = self._get_session_messages(session_id)
            return max([msg["turn"] for msg in messages]) if messages else 0
        else:
            # 在生产模式下，从数据库获取
            db: Session = next(get_db())
            max_turn = db.query(ConversationMessage.turn).filter(
                ConversationMessage.session_id == session_id
            ).order_by(ConversationMessage.turn.desc()).first()
            
            return max_turn[0] if max_turn else 0
    
    def _add_message_to_memory(self, session_id: str, message: Dict) -> Dict:
        """在测试模式下添加消息到内存"""
        if session_id not in self.test_messages:
            self.test_messages[session_id] = []
        
        # 获取当前最大turn值
        max_turn = self._get_max_turn(session_id)
        turn = max_turn + 1
        
        # 创建新消息记录
        new_message = {
            "id": f"mock_{len(self.test_messages[session_id]) + 1}",
            "turn": turn,
            "role": message["role"],
            "content": message["content"],
            "parent_message_id": message.get("parent_message_id"),
            "created_at": datetime.now().isoformat()
        }
        
        self.test_messages[session_id].append(new_message)
        return new_message
    
    def handle_user_input(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入，添加消息到对话历史并返回完整对话历史
        
        Args:
            session_id: 会话ID
            user_input: 用户输入的文本
            
        Returns:
            包含更新后对话历史的字典
        """
        try:
            # 添加用户消息
            user_message = self.add_message(session_id, {
                "role": "user",
                "content": user_input,
                "parent_message_id": None
            })
            
            # 这里应该调用NLU服务和SQL生成服务来处理用户查询
            # 但根据需求，我们只关注对话管理，所以这里返回模拟的助手回复
            assistant_response = {
                "role": "assistant",
                "content": "我理解了您的查询，正在为您分析数据...",
                "parent_message_id": user_message["id"]
            }
            
            # 添加助手消息
            assistant_message = self.add_message(session_id, assistant_response)
            
            # 获取完整的对话历史
            conversation_history = self.get_conversation_history(session_id)
            
            return {
                "user_message": user_message,
                "assistant_message": assistant_message,
                "conversation_history": conversation_history
            }
            
        except Exception as e:
            logger.error(f"Error handling user input for session {session_id}: {str(e)}")
            raise
    
    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        获取指定会话的对话历史
        
        Args:
            session_id: 会话ID
            limit: 最大消息数量，默认100
            
        Returns:
            消息列表，每个消息包含role、content、turn、parent_message_id等信息
        """
        try:
            messages = self._get_session_messages(session_id)
            
            # 应用limit限制，返回前'limit'条消息以保持时间顺序（最早的消息在前）
            if limit < len(messages):
                messages = messages[:limit]
            
            return messages
        except Exception as e:
            logger.error(f"Error getting conversation history for {session_id}: {str(e)}")
            raise
    
    def add_message(self, session_id: str, message: Dict) -> Dict:
        """
        添加一条消息到对话历史
        
        Args:
            session_id: 会话ID
            message: 消息字典，包含role、content、parent_message_id等字段
            
        Returns:
            包含新消息ID的字典
        """
        try:
            if self.test_mode:
                return self._add_message_to_memory(session_id, message)
            else:
                db: Session = next(get_db())
                
                # 获取当前会话的最大turn值
                max_turn = db.query(ConversationMessage.turn).filter(
                    ConversationMessage.session_id == session_id
                ).order_by(ConversationMessage.turn.desc()).first()
                
                turn = (max_turn[0] + 1) if max_turn else 1
                
                # 创建新消息记录
                new_message = ConversationMessage(
                    session_id=session_id,
                    turn=turn,
                    role=message["role"],
                    content=message["content"],
                    parent_message_id=message.get("parent_message_id"),
                    created_at=datetime.now()
                )
                
                db.add(new_message)
                db.commit()
                
                return {
                    "id": new_message.id,
                    "turn": turn,
                    "role": message["role"],
                    "content": message["content"],
                    "parent_message_id": message.get("parent_message_id"),
                    "created_at": new_message.created_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            if not self.test_mode:
                db.rollback()
            raise
    
    def get_last_message(self, session_id: str) -> Optional[Dict]:
        """
        获取指定会话的最后一条消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            最后一条消息的字典，如果不存在则返回None
        """
        try:
            messages = self._get_session_messages(session_id)
            
            if not messages:
                return None
            
            return messages[-1]
            
        except Exception as e:
            logger.error(f"Error getting last message for {session_id}: {str(e)}")
            raise
    
    def get_messages_by_parent(self, session_id: str, parent_message_id: str) -> List[Dict]:
        """
        获取指定父消息的所有子消息
        
        Args:
            session_id: 会话ID
            parent_message_id: 父消息ID
            
        Returns:
            子消息列表
        """
        try:
            messages = self._get_session_messages(session_id)
            
            return [
                msg for msg in messages 
                if msg["parent_message_id"] == parent_message_id
            ]
            
        except Exception as e:
            logger.error(f"Error getting messages by parent {parent_message_id} for session {session_id}: {str(e)}")
            raise

# 创建全局实例
multi_turn_handler = MultiTurnHandler(test_mode=False)