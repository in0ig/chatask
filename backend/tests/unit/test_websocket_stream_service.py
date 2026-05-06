"""
WebSocket流式通信服务单元测试
"""

import asyncio
import json
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.websocket_stream_service import (
    WebSocketStreamService,
    StreamMessage,
    StreamMessageType,
    ConnectionStatus,
    ConnectionInfo,
    get_websocket_stream_service
)


class MockWebSocket:
    """模拟WebSocket连接"""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        self.accept_called = False
        
    async def accept(self):
        self.accept_called = True
        
    async def send_text(self, data: str):
        if self.closed:
            raise Exception("WebSocket已关闭")
        self.messages.append(data)
        
    async def receive_text(self):
        if self.closed:
            raise Exception("WebSocket已关闭")
        # 模拟接收消息
        await asyncio.sleep(0.1)
        return '{"type": "ping"}'
        
    def close(self):
        self.closed = True


@pytest.fixture
def websocket_service():
    """创建WebSocket服务实例"""
    service = WebSocketStreamService()
    yield service
    # 清理 - 不需要异步清理，因为测试环境下没有实际的后台任务


@pytest.fixture
def mock_websocket():
    """创建模拟WebSocket连接"""
    return MockWebSocket()


class TestWebSocketStreamService:
    """WebSocket流式通信服务测试"""
    
    @pytest.mark.asyncio
    async def test_connect_success(self, websocket_service, mock_websocket):
        """测试成功建立连接"""
        session_id = "test_session_1"
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        
        # 验证连接
        assert connection_id is not None
        assert mock_websocket.accept_called
        assert connection_id in websocket_service.connections
        assert session_id in websocket_service.session_connections
        assert connection_id in websocket_service.session_connections[session_id]
        
        # 验证连接信息
        conn_info = websocket_service.connections[connection_id]
        assert conn_info.session_id == session_id
        assert conn_info.status == ConnectionStatus.CONNECTED
        assert conn_info.websocket == mock_websocket
        
        # 验证发送了连接确认消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "status"
        assert message_data["content"] == "连接已建立"
    
    @pytest.mark.asyncio
    async def test_disconnect(self, websocket_service, mock_websocket):
        """测试断开连接"""
        session_id = "test_session_2"
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        
        # 断开连接
        await websocket_service.disconnect(connection_id, "测试断开")
        
        # 验证连接已清理
        assert connection_id not in websocket_service.connections
        assert session_id not in websocket_service.session_connections
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, websocket_service, mock_websocket):
        """测试成功发送消息"""
        session_id = "test_session_3"
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        
        # 清空之前的消息
        mock_websocket.messages.clear()
        
        # 发送消息
        success = await websocket_service.send_message(
            session_id=session_id,
            message_type=StreamMessageType.THINKING,
            content="正在思考...",
            metadata={"step": 1}
        )
        
        # 验证发送成功
        assert success is True
        assert len(mock_websocket.messages) == 1
        
        # 验证消息内容
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "thinking"
        assert message_data["content"] == "正在思考..."
        assert message_data["metadata"]["step"] == 1
        assert message_data["session_id"] == session_id
        assert "id" in message_data
        assert "timestamp" in message_data
        assert message_data["sequence"] == 2  # 连接确认消息是1，这是第2条消息
    
    @pytest.mark.asyncio
    async def test_send_message_no_connection(self, websocket_service):
        """测试发送消息到不存在的会话"""
        success = await websocket_service.send_message(
            session_id="nonexistent_session",
            message_type=StreamMessageType.RESULT,
            content="测试消息"
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_send_thinking_message(self, websocket_service, mock_websocket):
        """测试发送思考消息"""
        session_id = "test_session_4"
        
        # 建立连接
        await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送思考消息
        await websocket_service.send_thinking_message(
            session_id, 
            "正在分析数据...", 
            {"progress": 0.3}
        )
        
        # 验证消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "thinking"
        assert message_data["content"] == "正在分析数据..."
        assert message_data["metadata"]["progress"] == 0.3
    
    @pytest.mark.asyncio
    async def test_send_result_message(self, websocket_service, mock_websocket):
        """测试发送结果消息"""
        session_id = "test_session_5"
        
        # 建立连接
        await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送结果消息
        await websocket_service.send_result_message(
            session_id, 
            "查询完成", 
            {"rows": 100}
        )
        
        # 验证消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "result"
        assert message_data["content"] == "查询完成"
        assert message_data["metadata"]["rows"] == 100
    
    @pytest.mark.asyncio
    async def test_send_chart_message(self, websocket_service, mock_websocket):
        """测试发送图表消息"""
        session_id = "test_session_6"
        
        # 建立连接
        await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送图表消息
        chart_data = {
            "type": "bar",
            "data": [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
        }
        await websocket_service.send_chart_message(session_id, chart_data)
        
        # 验证消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "chart"
        assert message_data["content"] == "图表数据"
        assert message_data["metadata"]["chart_data"] == chart_data
    
    @pytest.mark.asyncio
    async def test_send_error_message(self, websocket_service, mock_websocket):
        """测试发送错误消息"""
        session_id = "test_session_7"
        
        # 建立连接
        await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送错误消息
        await websocket_service.send_error_message(
            session_id, 
            "查询失败", 
            "SQL_ERROR"
        )
        
        # 验证消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "error"
        assert message_data["content"] == "查询失败"
        assert message_data["metadata"]["error_code"] == "SQL_ERROR"
    
    @pytest.mark.asyncio
    async def test_send_status_message(self, websocket_service, mock_websocket):
        """测试发送状态消息"""
        session_id = "test_session_8"
        
        # 建立连接
        await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送状态消息
        await websocket_service.send_status_message(
            session_id, 
            "正在处理", 
            0.5
        )
        
        # 验证消息
        assert len(mock_websocket.messages) == 1
        message_data = json.loads(mock_websocket.messages[0])
        assert message_data["type"] == "status"
        assert message_data["content"] == "正在处理"
        assert message_data["metadata"]["progress"] == 0.5
    
    @pytest.mark.asyncio
    async def test_multiple_connections_same_session(self, websocket_service):
        """测试同一会话的多个连接"""
        session_id = "test_session_9"
        
        # 建立两个连接
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()
        
        connection_id1 = await websocket_service.connect(mock_ws1, session_id)
        connection_id2 = await websocket_service.connect(mock_ws2, session_id)
        
        # 验证连接
        assert connection_id1 != connection_id2
        assert len(websocket_service.session_connections[session_id]) == 2
        
        # 清空消息
        mock_ws1.messages.clear()
        mock_ws2.messages.clear()
        
        # 发送消息到会话
        await websocket_service.send_message(
            session_id=session_id,
            message_type=StreamMessageType.RESULT,
            content="广播消息"
        )
        
        # 验证两个连接都收到消息
        assert len(mock_ws1.messages) == 1
        assert len(mock_ws2.messages) == 1
        
        message1 = json.loads(mock_ws1.messages[0])
        message2 = json.loads(mock_ws2.messages[0])
        
        assert message1["content"] == "广播消息"
        assert message2["content"] == "广播消息"
        assert message1["id"] == message2["id"]  # 同一消息
    
    @pytest.mark.asyncio
    async def test_send_to_specific_connection(self, websocket_service):
        """测试发送消息到指定连接"""
        session_id = "test_session_10"
        
        # 建立两个连接
        mock_ws1 = MockWebSocket()
        mock_ws2 = MockWebSocket()
        
        connection_id1 = await websocket_service.connect(mock_ws1, session_id)
        connection_id2 = await websocket_service.connect(mock_ws2, session_id)
        
        # 清空消息
        mock_ws1.messages.clear()
        mock_ws2.messages.clear()
        
        # 发送消息到指定连接
        await websocket_service.send_message(
            session_id=session_id,
            message_type=StreamMessageType.RESULT,
            content="指定连接消息",
            connection_id=connection_id1
        )
        
        # 验证只有指定连接收到消息
        assert len(mock_ws1.messages) == 1
        assert len(mock_ws2.messages) == 0
        
        message = json.loads(mock_ws1.messages[0])
        assert message["content"] == "指定连接消息"
    
    def test_get_connection_status(self, websocket_service):
        """测试获取连接状态"""
        session_id = "test_session_11"
        
        # 测试不存在的会话
        status = websocket_service.get_connection_status(session_id)
        assert status["session_id"] == session_id
        assert status["connection_count"] == 0
        assert status["connections"] == []
    
    @pytest.mark.asyncio
    async def test_get_connection_status_with_connections(self, websocket_service, mock_websocket):
        """测试获取有连接的会话状态"""
        session_id = "test_session_12"
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        
        # 获取状态
        status = websocket_service.get_connection_status(session_id)
        
        assert status["session_id"] == session_id
        assert status["connection_count"] == 1
        assert len(status["connections"]) == 1
        
        conn_info = status["connections"][0]
        assert conn_info["connection_id"] == connection_id
        assert conn_info["status"] == "connected"
        assert "connected_at" in conn_info
        assert "last_heartbeat" in conn_info
        assert conn_info["message_sequence"] == 1  # 连接确认消息
        assert conn_info["pending_messages"] == 0
    
    def test_get_all_connections_status(self, websocket_service):
        """测试获取所有连接状态"""
        status = websocket_service.get_all_connections_status()
        
        assert "total_connections" in status
        assert "total_sessions" in status
        assert "sessions" in status
        assert isinstance(status["sessions"], dict)
    
    @pytest.mark.asyncio
    async def test_resume_connection_not_exists(self, websocket_service):
        """测试恢复不存在的连接"""
        success = await websocket_service.resume_connection("nonexistent_connection")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_message_sequence(self, websocket_service, mock_websocket):
        """测试消息序号"""
        session_id = "test_session_13"
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        mock_websocket.messages.clear()
        
        # 发送多条消息
        for i in range(3):
            await websocket_service.send_message(
                session_id=session_id,
                message_type=StreamMessageType.THINKING,
                content=f"消息 {i+1}"
            )
        
        # 验证消息序号
        assert len(mock_websocket.messages) == 3
        
        for i, message_json in enumerate(mock_websocket.messages):
            message_data = json.loads(message_json)
            assert message_data["sequence"] == i + 2  # +1 for connection message, +1 for 1-based
            assert message_data["content"] == f"消息 {i+1}"
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_exception(self, websocket_service):
        """测试WebSocket断开异常处理"""
        session_id = "test_session_14"
        
        # 创建会抛出异常的模拟WebSocket
        mock_websocket = MockWebSocket()
        
        # 建立连接
        connection_id = await websocket_service.connect(mock_websocket, session_id)
        
        # 模拟WebSocket断开
        mock_websocket.close()
        
        # 尝试发送消息（应该处理异常）
        success = await websocket_service.send_message(
            session_id=session_id,
            message_type=StreamMessageType.RESULT,
            content="测试消息"
        )
        
        # 验证发送失败，连接被清理
        assert success is False
        assert connection_id not in websocket_service.connections


class TestStreamMessage:
    """StreamMessage类测试"""
    
    def test_stream_message_creation(self):
        """测试创建流式消息"""
        message = StreamMessage(
            id="test_id",
            session_id="test_session",
            type=StreamMessageType.THINKING,
            content="测试内容",
            metadata={"key": "value"}
        )
        
        assert message.id == "test_id"
        assert message.session_id == "test_session"
        assert message.type == StreamMessageType.THINKING
        assert message.content == "测试内容"
        assert message.metadata == {"key": "value"}
        assert message.timestamp is not None
        assert message.sequence == 0
    
    def test_stream_message_to_dict(self):
        """测试消息转换为字典"""
        message = StreamMessage(
            id="test_id",
            session_id="test_session",
            type=StreamMessageType.RESULT,
            content="测试内容"
        )
        
        data = message.to_dict()
        
        assert data["id"] == "test_id"
        assert data["session_id"] == "test_session"
        assert data["type"] == "result"  # 枚举值
        assert data["content"] == "测试内容"
        assert "timestamp" in data
    
    def test_stream_message_to_json(self):
        """测试消息转换为JSON"""
        message = StreamMessage(
            id="test_id",
            session_id="test_session",
            type=StreamMessageType.CHART,
            content="图表数据",
            metadata={"chart_type": "bar"}
        )
        
        json_str = message.to_json()
        data = json.loads(json_str)
        
        assert data["id"] == "test_id"
        assert data["type"] == "chart"
        assert data["metadata"]["chart_type"] == "bar"


class TestConnectionInfo:
    """ConnectionInfo类测试"""
    
    def test_connection_info_creation(self):
        """测试创建连接信息"""
        mock_websocket = MockWebSocket()
        
        conn_info = ConnectionInfo(
            session_id="test_session",
            websocket=mock_websocket,
            status=ConnectionStatus.CONNECTED,
            connected_at=datetime.now(),
            last_heartbeat=time.time()
        )
        
        assert conn_info.session_id == "test_session"
        assert conn_info.websocket == mock_websocket
        assert conn_info.status == ConnectionStatus.CONNECTED
        assert conn_info.message_sequence == 0
        assert conn_info.pending_messages == []
    
    def test_connection_info_with_pending_messages(self):
        """测试带待发送消息的连接信息"""
        mock_websocket = MockWebSocket()
        pending_messages = [
            StreamMessage("1", "session", StreamMessageType.THINKING, "msg1"),
            StreamMessage("2", "session", StreamMessageType.RESULT, "msg2")
        ]
        
        conn_info = ConnectionInfo(
            session_id="test_session",
            websocket=mock_websocket,
            status=ConnectionStatus.DISCONNECTED,
            connected_at=datetime.now(),
            last_heartbeat=time.time(),
            pending_messages=pending_messages
        )
        
        assert len(conn_info.pending_messages) == 2
        assert conn_info.pending_messages[0].content == "msg1"
        assert conn_info.pending_messages[1].content == "msg2"