"""
双层历史记录管理系统 - 基于Gemini语义影子模式
实现云端历史记录（仅SQL和状态）和本地历史记录（完整数据）的分离管理
"""

import json
import time
import hashlib
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    USER_QUESTION = "user_question"
    ASSISTANT_SQL = "assistant_sql"
    ASSISTANT_ANALYSIS = "assistant_analysis"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


class HistoryLevel(Enum):
    """历史记录级别"""
    CLOUD = "cloud"  # 云端历史：仅SQL和状态描述
    LOCAL = "local"  # 本地历史：完整数据和分析


@dataclass
class CloudHistoryMessage:
    """云端历史记录消息 - 不包含业务数据"""
    message_id: str
    session_id: str
    timestamp: datetime
    message_type: MessageType
    content: str  # 仅包含SQL、状态描述、用户问题
    metadata: Dict[str, Any]  # 不包含查询结果数据
    token_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        # 🔥 根据 message_type 推断 role
        role = 'user' if self.message_type == MessageType.USER_QUESTION else 'assistant'
        
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "role": role,  # 🔥 新增 role 字段
            "content": self.content,
            "metadata": self.metadata,
            "token_count": self.token_count
        }


@dataclass
class LocalHistoryMessage:
    """本地历史记录消息 - 包含完整数据"""
    message_id: str
    session_id: str
    timestamp: datetime
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    query_result: Optional[Dict[str, Any]] = None  # 完整查询结果
    analysis_data: Optional[Dict[str, Any]] = None  # 分析数据
    token_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        # 🔥 根据 message_type 推断 role
        role = 'user' if self.message_type == MessageType.USER_QUESTION else 'assistant'
        
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "role": role,  # 🔥 新增 role 字段
            "content": self.content,
            "metadata": self.metadata,
            "query_result": self.query_result,
            "analysis_data": self.analysis_data,
            "token_count": self.token_count
        }


@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    cloud_messages: List[CloudHistoryMessage]
    local_messages: List[LocalHistoryMessage]
    compressed_context: Optional[str] = None
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "cloud_messages": [msg.to_dict() for msg in self.cloud_messages],
            "local_messages": [msg.to_dict() for msg in self.local_messages],
            "compressed_context": self.compressed_context,
            "total_tokens": self.total_tokens
        }


class DataSanitizer:
    """数据消毒器 - 清洗敏感数据"""
    
    def __init__(self):
        # 敏感数据模式 - 按优先级排序，避免重复替换
        # 注意：更具体的模式应该放在前面，避免被通用模式覆盖
        self.sensitive_patterns = [
            (r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', '[EMAIL]'),  # 邮箱
            (r'\d{4}-\d{2}-\d{2}', '[DATE]'),  # 日期格式 YYYY-MM-DD
            (r'\d+\.\d+', '[NUMBER]'),  # 小数
            (r'\d{11,}', '[ID]'),  # 长数字（11位以上，可能是ID或手机号）
            (r"'[^']*'", '[VALUE]'),  # 单引号字符串值
            (r'"[^"]*"', '[VALUE]'),  # 双引号字符串值
            # 匹配独立的整数，但避免匹配已经被替换的占位符和表名中的数字
            (r'(?<![A-Za-z_\[\]])\d+(?![A-Za-z_\[\]])', '[COUNT]'),  # 独立的整数
        ]
    
    def sanitize_for_cloud(self, content: str, query_result: Optional[Dict[str, Any]] = None) -> str:
        """为云端清洗内容，移除业务数据"""
        sanitized_content = content
        
        # 按优先级顺序应用敏感数据模式，确保所有敏感数据都被替换
        for pattern, replacement in self.sensitive_patterns:
            matches = list(re.finditer(pattern, sanitized_content))
            if matches:
                logger.debug(f"Detected sensitive data pattern {pattern}, found {len(matches)} matches")
                # 替换为占位符
                sanitized_content = re.sub(pattern, replacement, sanitized_content)
        
        return sanitized_content
    
    def extract_sql_metadata(self, query_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从查询结果中提取元数据（不包含实际数据值）"""
        if not query_result:
            return {}
        
        metadata = {}
        
        # 提取列信息
        if 'columns' in query_result:
            metadata['columns'] = query_result['columns']
            metadata['column_count'] = len(query_result['columns'])
        
        # 提取行数信息
        if 'data' in query_result:
            metadata['row_count'] = len(query_result['data'])
            metadata['has_data'] = len(query_result['data']) > 0
        
        # 提取查询状态
        if 'status' in query_result:
            metadata['query_status'] = query_result['status']
        
        # 提取执行时间
        if 'execution_time' in query_result:
            metadata['execution_time'] = query_result['execution_time']
        
        return metadata
    
    def create_cloud_summary(self, local_message: LocalHistoryMessage) -> str:
        """为本地消息创建云端摘要"""
        if local_message.message_type == MessageType.ASSISTANT_SQL:
            # 对于SQL消息，只保留SQL语句
            return local_message.content
        elif local_message.message_type == MessageType.ASSISTANT_ANALYSIS:
            # 对于分析消息，创建不包含具体数值的摘要
            return self._create_analysis_summary(local_message)
        else:
            # 其他消息类型直接清洗
            return self.sanitize_for_cloud(local_message.content)
    
    def _create_analysis_summary(self, message: LocalHistoryMessage) -> str:
        """创建分析摘要，不包含具体数值"""
        content = message.content
        
        # 按优先级顺序移除具体数值，保留分析逻辑
        summary = content
        for pattern, replacement in self.sensitive_patterns:
            summary = re.sub(pattern, replacement, summary)
        
        # 保留分析结构和逻辑
        return f"Analysis completed: {summary[:200]}..."


class ContextCompressor:
    """上下文压缩器 - 智能压缩和Token管理"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.compression_ratio = 0.7  # 压缩目标比例
    
    def compress_context(self, messages: List[Union[CloudHistoryMessage, LocalHistoryMessage]]) -> str:
        """压缩上下文消息"""
        if not messages:
            return ""
        
        # 计算当前Token总数
        total_tokens = sum(msg.token_count for msg in messages)
        
        if total_tokens <= self.max_tokens:
            return self._format_messages(messages)
        
        # 需要压缩
        target_tokens = int(self.max_tokens * self.compression_ratio)
        compressed_messages = self._select_important_messages(messages, target_tokens)
        
        return self._format_compressed_messages(compressed_messages)
    
    def _select_important_messages(self, messages: List[Union[CloudHistoryMessage, LocalHistoryMessage]], 
                                 target_tokens: int) -> List[Union[CloudHistoryMessage, LocalHistoryMessage]]:
        """选择重要消息"""
        # 按重要性排序：最近的消息 + SQL消息 + 错误消息
        scored_messages = []
        
        for i, msg in enumerate(messages):
            score = 0
            
            # 时间权重（越新越重要）
            time_weight = (i + 1) / len(messages)
            score += time_weight * 0.4
            
            # 类型权重
            if msg.message_type == MessageType.ASSISTANT_SQL:
                score += 0.3
            elif msg.message_type == MessageType.ERROR:
                score += 0.2
            elif msg.message_type == MessageType.USER_QUESTION:
                score += 0.1
            
            scored_messages.append((score, msg))
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # 选择消息直到达到Token限制
        selected = []
        current_tokens = 0
        
        for score, msg in scored_messages:
            if current_tokens + msg.token_count <= target_tokens:
                selected.append(msg)
                current_tokens += msg.token_count
            else:
                break
        
        # 按时间顺序重新排列
        selected.sort(key=lambda x: x.timestamp)
        return selected
    
    def _format_messages(self, messages: List[Union[CloudHistoryMessage, LocalHistoryMessage]]) -> str:
        """格式化消息为文本"""
        formatted = []
        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            formatted.append(f"[{timestamp}] {msg.message_type.value}: {msg.content[:100]}...")
        
        return "\n".join(formatted)
    
    def _format_compressed_messages(self, messages: List[Union[CloudHistoryMessage, LocalHistoryMessage]]) -> str:
        """格式化压缩后的消息"""
        if not messages:
            return "[Context compressed - no messages retained]"
        
        formatted = [f"[Compressed context with {len(messages)} key messages]"]
        formatted.extend(self._format_messages(messages).split('\n'))
        
        return "\n".join(formatted)
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的Token数量"""
        # 简单估算：1 token ≈ 4 characters for Chinese, 1 token ≈ 4 characters for English
        return len(text) // 4


class ContextManager:
    """双层上下文管理器"""
    
    def __init__(self, max_sessions: int = 1000, session_timeout_hours: int = 24):
        self.sessions: Dict[str, SessionContext] = {}
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.sanitizer = DataSanitizer()
        self.compressor = ContextCompressor()
        self.db_session = None  # 数据库会话，用于持久化
    
    def set_db_session(self, db_session):
        """设置数据库会话用于持久化"""
        self.db_session = db_session
    
    def create_session(self, session_id: str) -> SessionContext:
        """创建新会话"""
        now = datetime.now()
        session = SessionContext(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            cloud_messages=[],
            local_messages=[],
            total_tokens=0
        )
        
        self.sessions[session_id] = session
        self._cleanup_old_sessions()
        
        logger.info(f"Created new session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session
    
    async def load_session_from_db(self, session_id: str) -> Optional[SessionContext]:
        """
        从数据库加载会话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话上下文或None
        """
        try:
            if not self.db_session:
                logger.warning("数据库会话未设置，无法加载历史")
                return None
            
            from src.services.session_service import get_session_service
            service = get_session_service()
            
            history_data = await service.load_context_manager_history(self.db_session, session_id)
            
            if not history_data:
                logger.info(f"会话 {session_id} 无历史数据")
                return None
            
            # 重建会话上下文
            session = SessionContext(
                session_id=session_id,
                created_at=datetime.fromisoformat(history_data["created_at"]) if history_data.get("created_at") else datetime.now(),
                last_activity=datetime.fromisoformat(history_data["last_activity_at"]) if history_data.get("last_activity_at") else datetime.now(),
                cloud_messages=[],
                local_messages=[],
                total_tokens=history_data.get("total_tokens", 0)
            )
            
            # 重建云端消息
            for msg_dict in history_data.get("cloud_messages", []):
                cloud_msg = CloudHistoryMessage(
                    message_id=msg_dict.get("message_id", ""),
                    session_id=session_id,
                    timestamp=datetime.fromisoformat(msg_dict["timestamp"]) if isinstance(msg_dict.get("timestamp"), str) else msg_dict.get("timestamp", datetime.now()),
                    message_type=MessageType(msg_dict.get("message_type", "user_question")),
                    content=msg_dict.get("content", ""),
                    metadata=msg_dict.get("metadata", {}),
                    token_count=msg_dict.get("token_count", 0)
                )
                session.cloud_messages.append(cloud_msg)
            
            # 重建本地消息
            for msg_dict in history_data.get("local_messages", []):
                local_msg = LocalHistoryMessage(
                    message_id=msg_dict.get("message_id", ""),
                    session_id=session_id,
                    timestamp=datetime.fromisoformat(msg_dict["timestamp"]) if isinstance(msg_dict.get("timestamp"), str) else msg_dict.get("timestamp", datetime.now()),
                    message_type=MessageType(msg_dict.get("message_type", "user_question")),
                    content=msg_dict.get("content", ""),
                    metadata=msg_dict.get("metadata", {}),
                    query_result=msg_dict.get("query_result"),
                    analysis_data=msg_dict.get("analysis_data"),
                    token_count=msg_dict.get("token_count", 0)
                )
                session.local_messages.append(local_msg)
            
            # 缓存到内存
            self.sessions[session_id] = session
            
            logger.info(f"✅ 从数据库加载会话成功: {session_id}, 云端消息={len(session.cloud_messages)}, 本地消息={len(session.local_messages)}")
            return session
            
        except Exception as e:
            logger.error(f"从数据库加载会话失败: {str(e)}", exc_info=True)
            return None
    
    async def persist_session_to_db(self, session_id: str) -> bool:
        """
        持久化会话到数据库
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        try:
            session = self.get_session(session_id)
            if not session:
                logger.warning(f"会话 {session_id} 不存在")
                return False
            
            if not self.db_session:
                logger.warning("数据库会话未设置，无法持久化")
                return False
            
            from src.services.session_service import get_session_service
            service = get_session_service()
            
            # 转换消息为字典格式
            cloud_messages = [msg.to_dict() for msg in session.cloud_messages]
            local_messages = [msg.to_dict() for msg in session.local_messages]
            
            success = await service.persist_context_manager_history(
                self.db_session,
                session_id,
                cloud_messages,
                local_messages,
                session.total_tokens
            )
            
            if success:
                logger.info(f"✅ 持久化会话成功: {session_id}")
            else:
                logger.error(f"持久化会话失败: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"持久化会话失败: {str(e)}", exc_info=True)
            return False
    
    def add_user_message(self, session_id: str, content: str) -> str:
        """添加用户消息"""
        session = self.get_session(session_id) or self.create_session(session_id)
        message_id = self._generate_message_id(session_id, content)
        now = datetime.now()
        
        # 用户消息同时添加到云端和本地历史
        cloud_msg = CloudHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.USER_QUESTION,
            content=content,
            metadata={},
            token_count=self.compressor.estimate_tokens(content)
        )
        
        local_msg = LocalHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.USER_QUESTION,
            content=content,
            metadata={},
            token_count=self.compressor.estimate_tokens(content)
        )
        
        session.cloud_messages.append(cloud_msg)
        session.local_messages.append(local_msg)
        session.total_tokens += cloud_msg.token_count
        
        logger.debug(f"Added user message to session {session_id}")
        return message_id
    
    def add_sql_response(self, session_id: str, sql_content: str, 
                        query_result: Optional[Dict[str, Any]] = None) -> str:
        """添加SQL响应"""
        session = self.get_session(session_id) or self.create_session(session_id)
        message_id = self._generate_message_id(session_id, sql_content)
        now = datetime.now()
        
        # 云端消息：仅包含SQL，不包含查询结果
        cloud_content = self.sanitizer.sanitize_for_cloud(sql_content)
        cloud_metadata = self.sanitizer.extract_sql_metadata(query_result)
        
        cloud_msg = CloudHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.ASSISTANT_SQL,
            content=cloud_content,
            metadata=cloud_metadata,
            token_count=self.compressor.estimate_tokens(cloud_content)
        )
        
        # 本地消息：包含完整查询结果
        local_msg = LocalHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.ASSISTANT_SQL,
            content=sql_content,
            metadata=cloud_metadata.copy(),
            query_result=query_result,
            token_count=self.compressor.estimate_tokens(sql_content)
        )
        
        session.cloud_messages.append(cloud_msg)
        session.local_messages.append(local_msg)
        session.total_tokens += cloud_msg.token_count
        
        logger.debug(f"Added SQL response to session {session_id}")
        return message_id
    
    def add_analysis_response(self, session_id: str, analysis_content: str,
                            analysis_data: Optional[Dict[str, Any]] = None) -> str:
        """添加分析响应"""
        session = self.get_session(session_id) or self.create_session(session_id)
        message_id = self._generate_message_id(session_id, analysis_content)
        now = datetime.now()
        
        # 云端消息：创建不包含具体数值的摘要
        local_msg_temp = LocalHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.ASSISTANT_ANALYSIS,
            content=analysis_content,
            metadata={},
            analysis_data=analysis_data
        )
        
        cloud_content = self.sanitizer.create_cloud_summary(local_msg_temp)
        
        cloud_msg = CloudHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.ASSISTANT_ANALYSIS,
            content=cloud_content,
            metadata={"analysis_type": "data_summary"},
            token_count=self.compressor.estimate_tokens(cloud_content)
        )
        
        # 本地消息：包含完整分析数据
        local_msg = LocalHistoryMessage(
            message_id=message_id,
            session_id=session_id,
            timestamp=now,
            message_type=MessageType.ASSISTANT_ANALYSIS,
            content=analysis_content,
            metadata={"analysis_type": "full_analysis"},
            analysis_data=analysis_data,
            token_count=self.compressor.estimate_tokens(analysis_content)
        )
        
        session.cloud_messages.append(cloud_msg)
        session.local_messages.append(local_msg)
        session.total_tokens += cloud_msg.token_count
        
        logger.debug(f"Added analysis response to session {session_id}")
        return message_id
    
    def get_cloud_history(self, session_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """获取云端历史记录（用于发送给云端AI模型）"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        # 获取最近的消息
        recent_messages = session.cloud_messages[-max_messages:] if session.cloud_messages else []
        
        # 转换为适合AI模型的格式
        history = []
        for msg in recent_messages:
            if msg.message_type == MessageType.USER_QUESTION:
                history.append({
                    "role": "user",
                    "content": msg.content
                })
            elif msg.message_type == MessageType.ASSISTANT_SQL:
                history.append({
                    "role": "assistant",
                    "content": msg.content
                })
            elif msg.message_type == MessageType.ASSISTANT_ANALYSIS:
                history.append({
                    "role": "assistant",
                    "content": msg.content
                })
        
        return history
    
    def get_local_history(self, session_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """获取本地历史记录（用于本地AI模型数据分析）"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        # 获取最近的消息
        recent_messages = session.local_messages[-max_messages:] if session.local_messages else []
        
        return [msg.to_dict() for msg in recent_messages]
    
    def get_previous_query_results(self, session_id: str, count: int = 3) -> List[Dict[str, Any]]:
        """获取历史查询结果用于数据对比"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        # 查找包含查询结果的消息
        query_results = []
        for msg in reversed(session.local_messages):
            if msg.message_type == MessageType.ASSISTANT_SQL and msg.query_result:
                query_results.append(msg.query_result)
                if len(query_results) >= count:
                    break
        
        return list(reversed(query_results))
    
    def compress_session_context(self, session_id: str) -> bool:
        """压缩会话上下文"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # 压缩云端历史
        if session.cloud_messages:
            compressed_cloud = self.compressor.compress_context(session.cloud_messages)
            session.compressed_context = compressed_cloud
        
        # 如果Token数量过多，移除较旧的消息
        if session.total_tokens > self.compressor.max_tokens:
            self._trim_session_messages(session)
        
        logger.info(f"Compressed context for session {session_id}")
        return True
    
    def _trim_session_messages(self, session: SessionContext):
        """修剪会话消息"""
        target_tokens = int(self.compressor.max_tokens * 0.8)
        
        # 保留最近的重要消息
        important_cloud = self.compressor._select_important_messages(
            session.cloud_messages, target_tokens // 2
        )
        important_local = self.compressor._select_important_messages(
            session.local_messages, target_tokens // 2
        )
        
        session.cloud_messages = important_cloud
        session.local_messages = important_local
        session.total_tokens = sum(msg.token_count for msg in important_cloud)
    
    def _cleanup_old_sessions(self):
        """清理过期会话"""
        if len(self.sessions) <= self.max_sessions:
            return
        
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        
        # 如果还是太多，删除最旧的会话
        if len(self.sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1].last_activity
            )
            
            excess_count = len(self.sessions) - self.max_sessions
            for i in range(excess_count):
                session_id = sorted_sessions[i][0]
                del self.sessions[session_id]
                logger.info(f"Cleaned up old session: {session_id}")
    
    def _generate_message_id(self, session_id: str, content: str) -> str:
        """生成消息ID"""
        import time
        # 使用更高精度的时间戳确保唯一性
        timestamp = str(int(time.time() * 1000000))  # 微秒级时间戳
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{session_id}_{timestamp}_{content_hash}"
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "cloud_message_count": len(session.cloud_messages),
            "local_message_count": len(session.local_messages),
            "total_tokens": session.total_tokens,
            "has_compressed_context": bool(session.compressed_context)
        }
    
    def get_all_sessions_stats(self) -> Dict[str, Any]:
        """获取所有会话统计信息"""
        return {
            "total_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "session_timeout_hours": self.session_timeout.total_seconds() / 3600,
            "sessions": [self.get_session_stats(sid) for sid in self.sessions.keys()]
        }


# 全局上下文管理器实例
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """获取上下文管理器实例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def init_context_manager(max_sessions: int = 1000, session_timeout_hours: int = 24) -> ContextManager:
    """初始化上下文管理器"""
    global _context_manager
    _context_manager = ContextManager(max_sessions, session_timeout_hours)
    return _context_manager