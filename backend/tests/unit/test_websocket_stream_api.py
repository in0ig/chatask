"""
WebSocket流式通信API单元测试
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.websocket_stream_api import router
from src.services.websocket_stream_service import StreamMessageType


# 创建测试应用
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestWebSocketStreamAPI:
    """WebSocket流式通信API测试"""
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_stream_message_success(self, mock_get_service):
        """测试成功发送流式消息"""
        # 模拟服务实例
        mock_service = AsyncMock()
        mock_service.send_message = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-message/test_session",
            params={
                "message_type": "thinking",
                "content": "正在思考..."
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "消息发送成功"
        
        # 验证服务调用
        mock_service.send_message.assert_called_once()
        call_args = mock_service.send_message.call_args
        assert call_args[1]["session_id"] == "test_session"
        assert call_args[1]["message_type"] == StreamMessageType.THINKING
        assert call_args[1]["content"] == "正在思考..."
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_stream_message_invalid_type(self, mock_get_service):
        """测试发送无效类型的消息"""
        response = client.post(
            "/api/stream/send-message/test_session",
            params={
                "message_type": "invalid_type",
                "content": "测试内容"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的消息类型" in data["detail"]
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_stream_message_no_connection(self, mock_get_service):
        """测试发送消息到无连接的会话"""
        # 模拟服务实例
        mock_service = AsyncMock()
        mock_service.send_message = AsyncMock(return_value=False)
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-message/test_session",
            params={
                "message_type": "result",
                "content": "测试内容"
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "会话无活跃连接" in data["detail"]
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_thinking_message(self, mock_get_service):
        """测试发送思考消息"""
        mock_service = AsyncMock()
        mock_service.send_thinking_message = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-thinking/test_session",
            params={
                "content": "正在分析数据..."
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "思考消息发送成功"
        
        # 验证服务调用
        mock_service.send_thinking_message.assert_called_once_with(
            "test_session", "正在分析数据...", None
        )
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_result_message(self, mock_get_service):
        """测试发送结果消息"""
        mock_service = AsyncMock()
        mock_service.send_result_message = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-result/test_session",
            params={
                "content": "查询完成"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "结果消息发送成功"
        
        # 验证服务调用
        mock_service.send_result_message.assert_called_once_with(
            "test_session", "查询完成", None
        )
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_chart_message(self, mock_get_service):
        """测试发送图表消息"""
        mock_service = AsyncMock()
        mock_service.send_chart_message = AsyncMock()
        mock_get_service.return_value = mock_service
        
        chart_data = {
            "type": "bar",
            "data": [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
        }
        
        response = client.post(
            "/api/stream/send-chart/test_session",
            json=chart_data  # 直接发送图表数据，不包装在chart_data字段中
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "图表消息发送成功"
        
        # 验证服务调用
        mock_service.send_chart_message.assert_called_once_with(
            "test_session", chart_data
        )
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_error_message(self, mock_get_service):
        """测试发送错误消息"""
        mock_service = AsyncMock()
        mock_service.send_error_message = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-error/test_session",
            params={
                "error": "查询失败",
                "error_code": "SQL_ERROR"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "错误消息发送成功"
        
        # 验证服务调用
        mock_service.send_error_message.assert_called_once_with(
            "test_session", "查询失败", "SQL_ERROR"
        )
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_send_status_message(self, mock_get_service):
        """测试发送状态消息"""
        mock_service = AsyncMock()
        mock_service.send_status_message = AsyncMock()
        mock_get_service.return_value = mock_service
        
        response = client.post(
            "/api/stream/send-status/test_session",
            params={
                "status": "正在处理",
                "progress": 0.7
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "状态消息发送成功"
        
        # 验证服务调用
        mock_service.send_status_message.assert_called_once_with(
            "test_session", "正在处理", 0.7
        )
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_resume_connection_success(self, mock_get_service):
        """测试成功恢复连接"""
        mock_service = AsyncMock()
        mock_service.resume_connection = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service
        
        response = client.post("/api/stream/resume-connection/test_connection_id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "连接恢复成功"
        
        # 验证服务调用
        mock_service.resume_connection.assert_called_once_with("test_connection_id")
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_get_connection_status(self, mock_get_service):
        """测试获取连接状态"""
        mock_status = {
            "session_id": "test_session",
            "connection_count": 1,
            "connections": [
                {
                    "connection_id": "conn_1",
                    "status": "connected",
                    "connected_at": "2024-01-01T00:00:00",
                    "last_heartbeat": 1640995200.0,
                    "message_sequence": 5,
                    "pending_messages": 0
                }
            ]
        }
        mock_service = MagicMock()
        mock_service.get_connection_status.return_value = mock_status
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/stream/status/test_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data == mock_status
        
        # 验证服务调用
        mock_service.get_connection_status.assert_called_once_with("test_session")
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_get_all_connections_status(self, mock_get_service):
        """测试获取所有连接状态"""
        mock_status = {
            "total_connections": 2,
            "total_sessions": 1,
            "sessions": {
                "test_session": {
                    "session_id": "test_session",
                    "connection_count": 2,
                    "connections": []
                }
            }
        }
        mock_service = MagicMock()
        mock_service.get_all_connections_status.return_value = mock_status
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/stream/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data == mock_status
        
        # 验证服务调用
        mock_service.get_all_connections_status.assert_called_once()
    
    @patch('src.api.websocket_stream_api.get_websocket_stream_service')
    def test_health_check(self, mock_get_service):
        """测试健康检查"""
        mock_status = {
            "total_connections": 5,
            "total_sessions": 3
        }
        mock_service = MagicMock()
        mock_service.get_all_connections_status.return_value = mock_status
        mock_get_service.return_value = mock_service
        
        response = client.get("/api/stream/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "WebSocket流式通信服务"
        assert data["total_connections"] == 5
        assert data["total_sessions"] == 3
        assert "timestamp" in data