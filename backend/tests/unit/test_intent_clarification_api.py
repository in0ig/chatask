"""
意图澄清API单元测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.main import app
from src.services.intent_clarification_service import (
    IntentClarificationService,
    ClarificationQuestion,
    ClarificationResult,
    ClarificationSession
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Mock意图澄清服务"""
    service = Mock(spec=IntentClarificationService)
    
    # Mock异步方法
    service.generate_clarification = AsyncMock()
    service.confirm_clarification = Mock()
    service.modify_clarification = Mock()
    service.get_session = Mock()
    service.get_session_history = Mock()
    service.get_statistics = Mock()
    service.create_session = Mock()
    
    return service


@pytest.fixture(autouse=True)
def mock_service_dependency(mock_service):
    """自动Mock服务依赖"""
    # 重置全局服务实例
    import src.api.intent_clarification_api as api_module
    api_module._clarification_service = mock_service
    
    yield mock_service
    
    # 清理
    api_module._clarification_service = None


class TestGenerateClarification:
    """测试生成澄清问题端点"""
    
    def test_generate_clarification_success(self, client, mock_service):
        """测试成功生成澄清问题"""
        # 准备mock返回值
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[
                ClarificationQuestion(
                    question="请确认时间范围",
                    options=["今天", "本周", "本月"],
                    question_type="single_choice",
                    reasoning="问题中未明确时间范围",
                    importance=0.8
                )
            ],
            summary="理解您想查询销售数据",
            confidence=0.85,
            reasoning="需要确认时间范围"
        )
        
        mock_service.generate_clarification.return_value = clarification_result
        mock_service.create_session.return_value = Mock()
        
        # 发送请求
        response = client.post(
            "/api/intent-clarification/generate",
            json={
                "original_question": "查询销售数据",
                "table_selection": {
                    "selected_tables": [
                        {
                            "table_name": "sales",
                            "relevance_score": 0.9,
                            "reasoning": "包含销售相关字段",
                            "relevant_fields": ["amount", "date"]
                        }
                    ],
                    "overall_reasoning": "选择了销售表"
                }
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["clarification_needed"] is True
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question"] == "请确认时间范围"
        assert data["confidence"] == 0.85
        assert "session_id" in data["metadata"]
    
    def test_generate_clarification_no_clarification_needed(self, client, mock_service):
        """测试不需要澄清的情况"""
        clarification_result = ClarificationResult(
            clarification_needed=False,
            questions=[],
            summary="理解您想查询2024年1月的销售总额",
            confidence=0.95,
            reasoning="问题明确，无需澄清"
        )
        
        mock_service.generate_clarification.return_value = clarification_result
        mock_service.create_session.return_value = Mock()
        
        response = client.post(
            "/api/intent-clarification/generate",
            json={
                "original_question": "查询2024年1月的销售总额",
                "table_selection": {
                    "selected_tables": [
                        {
                            "table_name": "sales",
                            "relevance_score": 0.9,
                            "reasoning": "包含销售相关字段",
                            "relevant_fields": ["amount"]
                        }
                    ],
                    "overall_reasoning": "选择了销售表"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["clarification_needed"] is False
        assert len(data["questions"]) == 0
        assert data["confidence"] == 0.95
    
    def test_generate_clarification_with_context(self, client, mock_service):
        """测试带上下文的澄清生成"""
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        mock_service.generate_clarification.return_value = clarification_result
        mock_service.create_session.return_value = Mock()
        
        response = client.post(
            "/api/intent-clarification/generate",
            json={
                "original_question": "查询销售数据",
                "table_selection": {
                    "selected_tables": [
                        {
                            "table_name": "sales",
                            "relevance_score": 0.9,
                            "reasoning": "test",
                            "relevant_fields": []
                        }
                    ],
                    "overall_reasoning": "test"
                },
                "context": {"user_preference": "monthly_report"}
            }
        )
        
        assert response.status_code == 200
    
    def test_generate_clarification_service_error(self, client, mock_service):
        """测试服务错误处理"""
        mock_service.generate_clarification.side_effect = Exception("Service error")
        
        response = client.post(
            "/api/intent-clarification/generate",
            json={
                "original_question": "查询销售数据",
                "table_selection": {
                    "selected_tables": [],
                    "overall_reasoning": "test"
                }
            }
        )
        
        assert response.status_code == 500
        assert "生成澄清问题失败" in response.json()["detail"]


class TestConfirmClarification:
    """测试确认澄清端点"""
    
    def test_confirm_clarification_success(self, client, mock_service):
        """测试成功确认澄清"""
        mock_service.confirm_clarification.return_value = {
            "session_id": "test_session",
            "status": "confirmed",
            "responses": [{"question_index": 0, "answer": "本月"}]
        }
        
        response = client.post(
            "/api/intent-clarification/confirm",
            json={
                "session_id": "test_session",
                "user_responses": [{"question_index": 0, "answer": "本月"}]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "澄清已确认"
        assert data["data"]["status"] == "confirmed"
    
    def test_confirm_clarification_session_not_found(self, client, mock_service):
        """测试确认不存在的会话"""
        mock_service.confirm_clarification.side_effect = ValueError("Session not found: nonexistent")
        
        response = client.post(
            "/api/intent-clarification/confirm",
            json={
                "session_id": "nonexistent",
                "user_responses": []
            }
        )
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    def test_confirm_clarification_service_error(self, client, mock_service):
        """测试确认时的服务错误"""
        mock_service.confirm_clarification.side_effect = Exception("Service error")
        
        response = client.post(
            "/api/intent-clarification/confirm",
            json={
                "session_id": "test_session",
                "user_responses": []
            }
        )
        
        assert response.status_code == 500
        assert "确认澄清失败" in response.json()["detail"]


class TestModifyClarification:
    """测试修改澄清端点"""
    
    def test_modify_clarification_success(self, client, mock_service):
        """测试成功修改澄清"""
        mock_service.modify_clarification.return_value = {
            "session_id": "test_session",
            "status": "modified",
            "modifications": {"time_range": "本季度"}
        }
        
        response = client.post(
            "/api/intent-clarification/modify",
            json={
                "session_id": "test_session",
                "modifications": {"time_range": "本季度"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "澄清已修改"
        assert data["data"]["status"] == "modified"
    
    def test_modify_clarification_session_not_found(self, client, mock_service):
        """测试修改不存在的会话"""
        mock_service.modify_clarification.side_effect = ValueError("Session not found: nonexistent")
        
        response = client.post(
            "/api/intent-clarification/modify",
            json={
                "session_id": "nonexistent",
                "modifications": {}
            }
        )
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    def test_modify_clarification_service_error(self, client, mock_service):
        """测试修改时的服务错误"""
        mock_service.modify_clarification.side_effect = Exception("Service error")
        
        response = client.post(
            "/api/intent-clarification/modify",
            json={
                "session_id": "test_session",
                "modifications": {}
            }
        )
        
        assert response.status_code == 500
        assert "修改澄清失败" in response.json()["detail"]


class TestGetSession:
    """测试获取会话端点"""
    
    def test_get_session_success(self, client, mock_service):
        """测试成功获取会话"""
        session = ClarificationSession(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection={"selected_tables": []},
            clarification_result=ClarificationResult(
                clarification_needed=True,
                questions=[
                    ClarificationQuestion(
                        question="测试问题",
                        options=["选项1"],
                        question_type="single_choice"
                    )
                ],
                summary="test",
                confidence=0.8,
                reasoning="test"
            ),
            status="pending"
        )
        
        mock_service.get_session.return_value = session
        
        response = client.get("/api/intent-clarification/session/test_session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test_session"
        assert data["original_question"] == "查询销售数据"
        assert data["status"] == "pending"
        assert data["clarification_result"]["clarification_needed"] is True
    
    def test_get_session_not_found(self, client, mock_service):
        """测试获取不存在的会话"""
        mock_service.get_session.return_value = None
        
        response = client.get("/api/intent-clarification/session/nonexistent")
        
        assert response.status_code == 404
        assert "会话不存在" in response.json()["detail"]
    
    def test_get_session_service_error(self, client, mock_service):
        """测试获取会话时的服务错误"""
        mock_service.get_session.side_effect = Exception("Service error")
        
        response = client.get("/api/intent-clarification/session/test_session")
        
        assert response.status_code == 500
        assert "获取会话失败" in response.json()["detail"]


class TestGetSessionHistory:
    """测试获取会话历史端点"""
    
    def test_get_session_history_success(self, client, mock_service):
        """测试成功获取会话历史"""
        history = [
            {
                "original_question": "查询销售数据",
                "clarification_result": {
                    "clarification_needed": True,
                    "questions": [],
                    "summary": "test"
                },
                "user_responses": [],
                "status": "pending",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]
        
        mock_service.get_session_history.return_value = history
        
        response = client.get("/api/intent-clarification/session/test_session/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == "test_session"
        assert len(data["history"]) == 1
    
    def test_get_session_history_empty(self, client, mock_service):
        """测试获取空历史"""
        mock_service.get_session_history.return_value = []
        
        response = client.get("/api/intent-clarification/session/nonexistent/history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) == 0
    
    def test_get_session_history_service_error(self, client, mock_service):
        """测试获取历史时的服务错误"""
        mock_service.get_session_history.side_effect = Exception("Service error")
        
        response = client.get("/api/intent-clarification/session/test_session/history")
        
        assert response.status_code == 500
        assert "获取会话历史失败" in response.json()["detail"]


class TestGetStatistics:
    """测试获取统计信息端点"""
    
    def test_get_statistics_success(self, client, mock_service):
        """测试成功获取统计信息"""
        stats = {
            "total_clarifications": 10,
            "clarification_needed_count": 7,
            "user_confirmed_count": 5,
            "user_modified_count": 2,
            "active_sessions": 3,
            "clarification_rate": 0.7,
            "confirmation_rate": 0.71,
            "avg_questions_per_clarification": 1.5,
            "avg_response_time_ms": 250.0
        }
        
        mock_service.get_statistics.return_value = stats
        
        response = client.get("/api/intent-clarification/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["statistics"]["total_clarifications"] == 10
        assert data["statistics"]["clarification_rate"] == 0.7
    
    def test_get_statistics_service_error(self, client, mock_service):
        """测试获取统计信息时的服务错误"""
        mock_service.get_statistics.side_effect = Exception("Service error")
        
        response = client.get("/api/intent-clarification/statistics")
        
        assert response.status_code == 500
        assert "获取统计信息失败" in response.json()["detail"]


class TestHealthCheck:
    """测试健康检查端点"""
    
    def test_health_check_healthy(self, client, mock_service):
        """测试健康状态"""
        mock_service.get_statistics.return_value = {
            "active_sessions": 5,
            "total_clarifications": 100
        }
        
        response = client.get("/api/intent-clarification/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "intent_clarification"
        assert data["active_sessions"] == 5
        assert data["total_clarifications"] == 100
        assert "timestamp" in data
    
    def test_health_check_unhealthy(self, client, mock_service):
        """测试不健康状态"""
        mock_service.get_statistics.side_effect = Exception("Service error")
        
        response = client.get("/api/intent-clarification/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "intent_clarification"
        assert "error" in data
        assert "timestamp" in data
