"""
WebSocket流式通信服务

实现WebSocket的流式消息推送机制，支持分阶段内容推送、断点续传和连接恢复功能。
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from fastapi import WebSocket, WebSocketDisconnect
import weakref

logger = logging.getLogger(__name__)


class StreamMessageType(Enum):
    """流式消息类型"""
    THINKING = "thinking"  # 思考过程（灰色显示）
    RESULT = "result"      # 最终结果（黑色显示）
    CHART = "chart"        # 图表数据
    ERROR = "error"        # 错误信息
    STATUS = "status"      # 状态更新
    HEARTBEAT = "heartbeat"  # 心跳消息
    STAGE_START = "stage_start"  # 阶段开始
    STAGE_UPDATE = "stage_update"  # 阶段更新
    STAGE_COMPLETE = "stage_complete"  # 阶段完成
    COMPLETE = "complete"  # 流程完成


class ConnectionStatus(Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class StreamMessage:
    """流式消息数据结构"""
    id: str
    session_id: str
    type: StreamMessageType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = None
    sequence: int = 0
    # 可折叠相关字段
    stage_id: Optional[str] = None  # 阶段ID
    stage_name: Optional[str] = None  # 阶段名称
    stage_status: Optional[str] = None  # 阶段状态: in_progress, completed, error
    collapsible: bool = False  # 是否可折叠
    collapsed: bool = False  # 是否默认折叠
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ConnectionInfo:
    """连接信息"""
    session_id: str
    websocket: WebSocket
    status: ConnectionStatus
    connected_at: datetime
    last_heartbeat: float
    message_sequence: int = 0
    pending_messages: List[StreamMessage] = None
    
    def __post_init__(self):
        if self.pending_messages is None:
            self.pending_messages = []


class WebSocketStreamService:
    """WebSocket流式通信服务"""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.session_connections: Dict[str, Set[str]] = {}  # session_id -> connection_ids
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.message_timeout = 60  # 消息超时（秒）
        self.max_pending_messages = 100  # 最大待发送消息数
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
        
        # 消息处理回调
        self.message_handlers: Dict[str, Callable] = {}
    
    def _start_background_tasks(self):
        """启动后台任务"""
        if not self._initialized:
            try:
                # 检查是否有运行的事件循环
                asyncio.get_running_loop()
                self._initialized = True
            except RuntimeError:
                # 没有运行的事件循环，延迟初始化
                return
        
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def connect(self, websocket: WebSocket, session_id: str) -> str:
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            session_id: 会话ID
            
        Returns:
            连接ID
        """
        await websocket.accept()
        
        # 确保后台任务已启动
        self._start_background_tasks()
        
        connection_id = str(uuid.uuid4())
        connection_info = ConnectionInfo(
            session_id=session_id,
            websocket=websocket,
            status=ConnectionStatus.CONNECTED,
            connected_at=datetime.now(),
            last_heartbeat=time.time()
        )
        
        self.connections[connection_id] = connection_info
        
        # 维护会话到连接的映射
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
        
        logger.info(f"WebSocket连接已建立: connection_id={connection_id}, session_id={session_id}")
        
        # 发送连接确认消息
        await self.send_message(
            session_id=session_id,
            message_type=StreamMessageType.STATUS,
            content="连接已建立",
            metadata={"connection_id": connection_id}
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str, reason: str = "正常断开"):
        """
        断开WebSocket连接
        
        Args:
            connection_id: 连接ID
            reason: 断开原因
        """
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        session_id = connection_info.session_id
        
        # 更新连接状态
        connection_info.status = ConnectionStatus.DISCONNECTED
        
        # 从会话映射中移除
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        # 移除连接
        del self.connections[connection_id]
        
        logger.info(f"WebSocket连接已断开: connection_id={connection_id}, session_id={session_id}, reason={reason}")
    
    async def send_message(
        self,
        session_id: str,
        message_type: StreamMessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        connection_id: Optional[str] = None
    ) -> bool:
        """
        发送流式消息
        
        Args:
            session_id: 会话ID
            message_type: 消息类型
            content: 消息内容
            metadata: 元数据
            connection_id: 指定连接ID（可选）
            
        Returns:
            是否发送成功
        """
        message = StreamMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=message_type,
            content=content,
            metadata=metadata or {}
        )
        
        # 如果指定了连接ID，只发送给该连接
        if connection_id:
            return await self._send_to_connection(connection_id, message)
        
        # 发送给会话的所有连接
        if session_id not in self.session_connections:
            logger.warning(f"会话无活跃连接: session_id={session_id}")
            return False
        
        success_count = 0
        total_connections = len(self.session_connections[session_id])
        
        for conn_id in list(self.session_connections[session_id]):
            if await self._send_to_connection(conn_id, message):
                success_count += 1
        
        return success_count > 0
    
    async def _send_to_connection(self, connection_id: str, message: StreamMessage) -> bool:
        """
        发送消息到指定连接
        
        Args:
            connection_id: 连接ID
            message: 消息对象
            
        Returns:
            是否发送成功
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        if connection_info.status != ConnectionStatus.CONNECTED:
            # 连接不可用，添加到待发送队列
            if len(connection_info.pending_messages) < self.max_pending_messages:
                connection_info.pending_messages.append(message)
            return False
        
        try:
            # 设置消息序号
            connection_info.message_sequence += 1
            message.sequence = connection_info.message_sequence
            
            # 发送消息
            await connection_info.websocket.send_text(message.to_json())
            
            logger.debug(f"消息已发送: connection_id={connection_id}, message_id={message.id}, type={message.type.value}")
            return True
            
        except WebSocketDisconnect:
            logger.info(f"连接已断开: connection_id={connection_id}")
            await self.disconnect(connection_id, "客户端断开连接")
            return False
        except Exception as e:
            logger.error(f"发送消息失败: connection_id={connection_id}, error={str(e)}")
            connection_info.status = ConnectionStatus.ERROR
            # 如果是WebSocket连接问题，清理连接
            if "WebSocket" in str(e) or "已关闭" in str(e):
                await self.disconnect(connection_id, f"发送失败: {str(e)}")
            return False
    
    async def send_thinking_message(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """发送思考过程消息（灰色显示）"""
        await self.send_message(session_id, StreamMessageType.THINKING, content, metadata)
    
    async def send_result_message(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """发送最终结果消息（黑色显示）"""
        await self.send_message(session_id, StreamMessageType.RESULT, content, metadata)
    
    async def send_chart_message(self, session_id: str, chart_data: Dict[str, Any]):
        """发送图表消息"""
        await self.send_message(
            session_id, 
            StreamMessageType.CHART, 
            "图表数据", 
            {"chart_data": chart_data}
        )
    
    async def send_error_message(self, session_id: str, error: str, error_code: Optional[str] = None):
        """发送错误消息"""
        metadata = {"error_code": error_code} if error_code else None
        await self.send_message(session_id, StreamMessageType.ERROR, error, metadata)
    
    async def send_status_message(self, session_id: str, status: str, progress: Optional[float] = None):
        """发送状态更新消息"""
        metadata = {"progress": progress} if progress is not None else None
        await self.send_message(session_id, StreamMessageType.STATUS, status, metadata)
    
    async def send_stage_start(
        self,
        session_id: str,
        stage_id: str,
        stage_name: str,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        发送阶段开始消息
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            stage_name: 阶段名称
            content: 阶段内容
            metadata: 元数据
        """
        message = StreamMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=StreamMessageType.STAGE_START,
            content=content,
            metadata=metadata or {},
            stage_id=stage_id,
            stage_name=stage_name,
            stage_status="in_progress",
            collapsible=True,
            collapsed=False  # 进行中的阶段默认展开
        )
        
        # 发送给会话的所有连接
        if session_id in self.session_connections:
            for conn_id in list(self.session_connections[session_id]):
                await self._send_to_connection(conn_id, message)
    
    async def send_stage_update(
        self,
        session_id: str,
        stage_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        发送阶段更新消息
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            content: 更新内容
            metadata: 元数据
        """
        message = StreamMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=StreamMessageType.STAGE_UPDATE,
            content=content,
            metadata=metadata or {},
            stage_id=stage_id,
            stage_status="in_progress",
            collapsible=False
        )
        
        # 发送给会话的所有连接
        if session_id in self.session_connections:
            for conn_id in list(self.session_connections[session_id]):
                await self._send_to_connection(conn_id, message)
    
    async def send_stage_complete(
        self,
        session_id: str,
        stage_id: str,
        stage_name: str,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        发送阶段完成消息
        
        Args:
            session_id: 会话ID
            stage_id: 阶段ID
            stage_name: 阶段名称
            content: 完成内容
            metadata: 元数据
        """
        message = StreamMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=StreamMessageType.STAGE_COMPLETE,
            content=content,
            metadata=metadata or {},
            stage_id=stage_id,
            stage_name=stage_name,
            stage_status="completed",
            collapsible=True,
            collapsed=False  # 🔥 修复：已完成的阶段默认展开，用户可以手动折叠
        )
        
        # 发送给会话的所有连接
        if session_id in self.session_connections:
            for conn_id in list(self.session_connections[session_id]):
                await self._send_to_connection(conn_id, message)
    
    async def send_stage_reset(
        self,
        session_id: str,
        stage_id: str,
        stage_name: str,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        重置阶段内容（用于 SQL 执行失败后重新生成时，清空旧内容重新流式输出）
        前端收到此消息后应清空对应 stage 的内容并重置为 in_progress 状态
        """
        message = StreamMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=StreamMessageType.STAGE_START,  # 复用 stage_start 类型，前端通过 stage_id 匹配已有 stage
            content=content,
            metadata={**(metadata or {}), "reset": True},  # reset=True 标记前端清空旧内容
            stage_id=stage_id,
            stage_name=stage_name,
            stage_status="in_progress",
            collapsible=True,
            collapsed=False
        )

        if session_id in self.session_connections:
            for conn_id in list(self.session_connections[session_id]):
                await self._send_to_connection(conn_id, message)

    async def resume_connection(self, connection_id: str) -> bool:
        """
        恢复连接并发送待发送消息
        
        Args:
            connection_id: 连接ID
            
        Returns:
            是否恢复成功
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        if connection_info.status == ConnectionStatus.CONNECTED:
            return True
        
        # 更新连接状态
        connection_info.status = ConnectionStatus.CONNECTED
        connection_info.last_heartbeat = time.time()
        
        # 发送待发送消息
        pending_messages = connection_info.pending_messages.copy()
        connection_info.pending_messages.clear()
        
        success_count = 0
        for message in pending_messages:
            if await self._send_to_connection(connection_id, message):
                success_count += 1
        
        logger.info(f"连接已恢复: connection_id={connection_id}, 发送待发送消息: {success_count}/{len(pending_messages)}")
        
        return True
    
    def get_connection_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话连接状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            连接状态信息
        """
        if session_id not in self.session_connections:
            return {
                "session_id": session_id,
                "connection_count": 0,
                "connections": []
            }
        
        connections = []
        for connection_id in self.session_connections[session_id]:
            if connection_id in self.connections:
                conn_info = self.connections[connection_id]
                connections.append({
                    "connection_id": connection_id,
                    "status": conn_info.status.value,
                    "connected_at": conn_info.connected_at.isoformat(),
                    "last_heartbeat": conn_info.last_heartbeat,
                    "message_sequence": conn_info.message_sequence,
                    "pending_messages": len(conn_info.pending_messages)
                })
        
        return {
            "session_id": session_id,
            "connection_count": len(connections),
            "connections": connections
        }
    
    def get_all_connections_status(self) -> Dict[str, Any]:
        """获取所有连接状态"""
        return {
            "total_connections": len(self.connections),
            "total_sessions": len(self.session_connections),
            "sessions": {
                session_id: self.get_connection_status(session_id)
                for session_id in self.session_connections
            }
        }
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环错误: {str(e)}")
    
    async def _send_heartbeats(self):
        """发送心跳消息"""
        current_time = time.time()
        
        for connection_id, connection_info in list(self.connections.items()):
            if connection_info.status == ConnectionStatus.CONNECTED:
                try:
                    # 检查是否需要发送心跳
                    if current_time - connection_info.last_heartbeat > self.heartbeat_interval:
                        await connection_info.websocket.send_text(
                            json.dumps({
                                "type": StreamMessageType.HEARTBEAT.value,
                                "timestamp": current_time
                            })
                        )
                        connection_info.last_heartbeat = current_time
                        
                except WebSocketDisconnect:
                    await self.disconnect(connection_id, "心跳检测失败")
                except Exception as e:
                    logger.error(f"发送心跳失败: connection_id={connection_id}, error={str(e)}")
                    connection_info.status = ConnectionStatus.ERROR
    
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                await self._cleanup_expired_messages()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理循环错误: {str(e)}")
    
    async def _cleanup_expired_messages(self):
        """清理过期消息"""
        current_time = time.time()
        
        for connection_info in self.connections.values():
            # 清理过期的待发送消息
            connection_info.pending_messages = [
                msg for msg in connection_info.pending_messages
                if current_time - msg.timestamp < self.message_timeout
            ]
    
    async def shutdown(self):
        """关闭服务"""
        logger.info("正在关闭WebSocket流式通信服务...")
        
        # 取消后台任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # 断开所有连接
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id, "服务关闭")
        
        logger.info("WebSocket流式通信服务已关闭")


# 全局服务实例 - 延迟初始化
_websocket_stream_service: Optional[WebSocketStreamService] = None

def get_websocket_stream_service() -> WebSocketStreamService:
    """获取WebSocket流式通信服务实例"""
    global _websocket_stream_service
    if _websocket_stream_service is None:
        _websocket_stream_service = WebSocketStreamService()
    return _websocket_stream_service