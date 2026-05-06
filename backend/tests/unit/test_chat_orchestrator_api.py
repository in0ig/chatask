"""
对话流程编排引擎API单元测试
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.chat_orchestrator_api import router
from src.services.chat_orchestrator import ChatStage, ChatIntent


# 创建测试应用
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestChatOrchestratorAPI:
    """对话编排引擎API测试"""
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_start_chat_success(self, mock_get_orchestrator):
        """测试成功开始对话"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.start_chat = AsyncMock(return_value={
            "success": True,
            "session_id": "test_session",
            "intent": "smart_query",
            "tables": ["products"],
            "sql": "SELECT * FROM products",
            "result": {"columns": ["id"], "rows": [[1]]},
            "analysis": "分析结果",
            "stage": "completed"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/start/test_session",
            params={
                "user_question": "查询产品信息",
                "data_source_id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "对话开始成功"
        assert data["data"]["session_id"] == "test_session"
        assert data["data"]["intent"] == "smart_query"
        
        # 验证服务调用
        mock_orchestrator.start_chat.assert_called_once_with("test_session", "查询产品信息", 1)
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_start_chat_failure(self, mock_get_orchestrator):
        """测试开始对话失败"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.start_chat = AsyncMock(return_value={
            "success": False,
            "error": "意图识别失败",
            "session_id": "test_session"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/start/test_session",
            params={"user_question": "查询产品信息"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "对话开始失败"
        assert "意图识别失败" in data["data"]["error"]
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_start_chat_exception(self, mock_get_orchestrator):
        """测试开始对话异常"""
        # 模拟编排器抛出异常
        mock_orchestrator = AsyncMock()
        mock_orchestrator.start_chat = AsyncMock(side_effect=Exception("测试异常"))
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/start/test_session",
            params={"user_question": "查询产品信息"}
        )
        
        assert response.status_code == 500
        assert "开始对话失败" in response.json()["detail"]
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_continue_chat_success(self, mock_get_orchestrator):
        """测试成功继续对话"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.continue_chat = AsyncMock(return_value={
            "success": True,
            "session_id": "test_session",
            "answer": "澄清处理结果"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/continue/test_session",
            params={"user_response": "是的，请继续"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "对话继续成功"
        assert data["data"]["answer"] == "澄清处理结果"
        
        # 验证服务调用
        mock_orchestrator.continue_chat.assert_called_once_with("test_session", "是的，请继续")
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_continue_chat_failure(self, mock_get_orchestrator):
        """测试继续对话失败"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.continue_chat = AsyncMock(return_value={
            "success": False,
            "error": "会话不存在",
            "session_id": "test_session"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/continue/test_session",
            params={"user_response": "是的，请继续"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "对话继续失败"
        assert "会话不存在" in data["data"]["error"]
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_handle_followup_success(self, mock_get_orchestrator):
        """测试成功处理追问"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.continue_chat = AsyncMock(return_value={
            "success": True,
            "session_id": "test_session",
            "answer": "追问答案",
            "type": "followup"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/followup/test_session",
            params={"followup_question": "为什么是这个结果？"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "追问处理成功"
        assert data["data"]["answer"] == "追问答案"
        assert data["data"]["type"] == "followup"
        
        # 验证服务调用
        mock_orchestrator.continue_chat.assert_called_once_with("test_session", "为什么是这个结果？")
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_get_session_status_exists(self, mock_get_orchestrator):
        """测试获取存在的会话状态"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": "test_session",
            "exists": True,
            "current_stage": "completed",
            "intent": "smart_query",
            "selected_tables": ["products"],
            "error_count": 0,
            "retry_count": 0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:05:00",
            "has_result": True,
            "previous_data_count": 1
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/status/test_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "获取会话状态成功"
        assert data["data"]["exists"] is True
        assert data["data"]["current_stage"] == "completed"
        assert data["data"]["intent"] == "smart_query"
        
        # 验证服务调用
        mock_orchestrator.get_session_status.assert_called_once_with("test_session")
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_get_session_status_not_exists(self, mock_get_orchestrator):
        """测试获取不存在的会话状态"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": "nonexistent_session",
            "exists": False
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/status/nonexistent_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["exists"] is False
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_get_all_sessions_status(self, mock_get_orchestrator):
        """测试获取所有会话状态"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_all_sessions_status.return_value = {
            "total_sessions": 2,
            "sessions": {
                "session1": {
                    "current_stage": "completed",
                    "intent": "smart_query",
                    "error_count": 0,
                    "updated_at": "2024-01-01T00:00:00"
                },
                "session2": {
                    "current_stage": "sql_generation",
                    "intent": "report_generation",
                    "error_count": 1,
                    "updated_at": "2024-01-01T00:05:00"
                }
            }
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "获取所有会话状态成功"
        assert data["data"]["total_sessions"] == 2
        assert "session1" in data["data"]["sessions"]
        assert "session2" in data["data"]["sessions"]
        
        # 验证服务调用
        mock_orchestrator.get_all_sessions_status.assert_called_once()
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_cleanup_session_success(self, mock_get_orchestrator):
        """测试成功清理会话"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.cleanup_session.return_value = True
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.delete("/api/chat/session/test_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "会话清理成功"
        assert data["data"]["session_id"] == "test_session"
        assert data["data"]["cleaned"] is True
        
        # 验证服务调用
        mock_orchestrator.cleanup_session.assert_called_once_with("test_session")
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_cleanup_session_not_exists(self, mock_get_orchestrator):
        """测试清理不存在的会话"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.cleanup_session.return_value = False
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.delete("/api/chat/session/nonexistent_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "会话不存在或已清理"
        assert data["data"]["cleaned"] is False
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_batch_start_chats_success(self, mock_get_orchestrator):
        """测试批量开始对话成功"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.start_chat = AsyncMock(side_effect=[
            {"success": True, "session_id": "session1", "intent": "smart_query"},
            {"success": True, "session_id": "session2", "intent": "report_generation"},
            {"success": False, "session_id": "session3", "error": "测试错误"}
        ])
        mock_get_orchestrator.return_value = mock_orchestrator
        
        requests = [
            {"session_id": "session1", "user_question": "查询产品", "data_source_id": 1},
            {"session_id": "session2", "user_question": "生成报告", "data_source_id": 2},
            {"session_id": "session3", "user_question": "测试问题"}
        ]
        
        response = client.post("/api/chat/batch-start", json=requests)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 3
        assert data["data"]["success_count"] == 2
        assert data["data"]["failed_count"] == 1
        assert len(data["data"]["results"]) == 3
        
        # 验证服务调用次数
        assert mock_orchestrator.start_chat.call_count == 3
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_batch_start_chats_invalid_request(self, mock_get_orchestrator):
        """测试批量开始对话 - 无效请求"""
        mock_orchestrator = AsyncMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        
        requests = [
            {"session_id": "session1"},  # 缺少 user_question
            {"user_question": "查询产品"},  # 缺少 session_id
            {"session_id": "session3", "user_question": "正常请求"}
        ]
        
        response = client.post("/api/chat/batch-start", json=requests)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 3
        assert data["data"]["failed_count"] == 2  # 前两个请求失败
        
        # 验证只调用了一次有效请求
        mock_orchestrator.start_chat.assert_called_once()
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_retry_chat_success(self, mock_get_orchestrator):
        """测试重试对话成功"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": "test_session",
            "exists": True,
            "current_stage": "error_handling"
        }
        mock_orchestrator.continue_chat = AsyncMock(return_value={
            "success": True,
            "session_id": "test_session",
            "stage": "completed"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post("/api/chat/retry/test_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "重试成功"
        
        # 验证服务调用
        mock_orchestrator.get_session_status.assert_called_once_with("test_session")
        mock_orchestrator.continue_chat.assert_called_once_with("test_session", "重试")
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_retry_chat_session_not_exists(self, mock_get_orchestrator):
        """测试重试不存在的会话"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": "nonexistent_session",
            "exists": False
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post("/api/chat/retry/nonexistent_session")
        
        assert response.status_code == 404
        assert "会话不存在" in response.json()["detail"]
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_get_chat_stages(self, mock_get_orchestrator):
        """测试获取对话阶段列表"""
        response = client.get("/api/chat/stages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "获取对话阶段成功"
        assert "stages" in data["data"]
        
        stages = data["data"]["stages"]
        assert len(stages) == len(ChatStage)
        
        # 验证包含所有阶段
        stage_values = [stage["value"] for stage in stages]
        for chat_stage in ChatStage:
            assert chat_stage.value in stage_values
        
        # 验证阶段信息完整
        for stage in stages:
            assert "value" in stage
            assert "name" in stage
            assert "description" in stage
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_get_chat_intents(self, mock_get_orchestrator):
        """测试获取对话意图列表"""
        response = client.get("/api/chat/intents")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "获取对话意图成功"
        assert "intents" in data["data"]
        
        intents = data["data"]["intents"]
        assert len(intents) == len(ChatIntent)
        
        # 验证包含所有意图
        intent_values = [intent["value"] for intent in intents]
        for chat_intent in ChatIntent:
            assert chat_intent.value in intent_values
        
        # 验证意图信息完整
        for intent in intents:
            assert "value" in intent
            assert "name" in intent
            assert "description" in intent
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_health_check(self, mock_get_orchestrator):
        """测试健康检查"""
        # 模拟编排器实例
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_all_sessions_status.return_value = {
            "total_sessions": 5
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "服务运行正常"
        assert data["data"]["status"] == "healthy"
        assert data["data"]["service"] == "对话流程编排引擎"
        assert data["data"]["total_sessions"] == 5
        assert "timestamp" in data["data"]
        
        # 验证服务调用
        mock_orchestrator.get_all_sessions_status.assert_called_once()
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_health_check_exception(self, mock_get_orchestrator):
        """测试健康检查异常"""
        # 模拟编排器抛出异常
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_all_sessions_status.side_effect = Exception("测试异常")
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/health")
        
        assert response.status_code == 500
        assert "健康检查失败" in response.json()["detail"]


class TestChatOrchestratorAPIEdgeCases:
    """对话编排引擎API边界情况测试"""
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_start_chat_empty_question(self, mock_get_orchestrator):
        """测试开始对话 - 空问题"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.start_chat = AsyncMock(return_value={
            "success": False,
            "error": "问题不能为空",
            "session_id": "test_session"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/start/test_session",
            params={"user_question": ""}
        )
        
        # 应该接受空字符串，由业务逻辑处理
        assert response.status_code == 200
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_start_chat_missing_question(self, mock_get_orchestrator):
        """测试开始对话 - 缺少问题参数"""
        response = client.post("/api/chat/start/test_session")
        
        assert response.status_code == 422  # 参数验证失败
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_continue_chat_empty_response(self, mock_get_orchestrator):
        """测试继续对话 - 空回复"""
        # 模拟编排器实例
        mock_orchestrator = AsyncMock()
        mock_orchestrator.continue_chat = AsyncMock(return_value={
            "success": False,
            "error": "回复不能为空",
            "session_id": "test_session"
        })
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.post(
            "/api/chat/continue/test_session",
            params={"user_response": ""}
        )
        
        # 应该接受空字符串，由业务逻辑处理
        assert response.status_code == 200
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_batch_start_empty_requests(self, mock_get_orchestrator):
        """测试批量开始对话 - 空请求列表"""
        response = client.post("/api/chat/batch-start", json=[])
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["success_count"] == 0
        assert data["data"]["failed_count"] == 0
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_session_id_special_characters(self, mock_get_orchestrator):
        """测试会话ID包含特殊字符"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": "test-session_123",
            "exists": False
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get("/api/chat/status/test-session_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["session_id"] == "test-session_123"
    
    @patch('src.api.chat_orchestrator_api.get_chat_orchestrator')
    def test_long_session_id(self, mock_get_orchestrator):
        """测试长会话ID"""
        long_session_id = "a" * 100
        mock_orchestrator = MagicMock()
        mock_orchestrator.get_session_status.return_value = {
            "session_id": long_session_id,
            "exists": False
        }
        mock_get_orchestrator.return_value = mock_orchestrator
        
        response = client.get(f"/api/chat/status/{long_session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["session_id"] == long_session_id