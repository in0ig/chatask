"""
意图澄清API扩展功能测试

测试Task 5.3.2新增的API端点：
- 处理澄清反馈
- 更新意图
- 获取澄清历史
- 回溯到指定轮次
- 优化澄清策略
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from src.main import app
from src.services.intent_clarification_service import (
    IntentClarificationService,
    ClarificationResult,
    ClarificationQuestion,
    ClarificationFeedback,
    IntentUpdate,
    IntentUpdateType,
    ClarificationHistory
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_service():
    """创建Mock服务"""
    service = Mock(spec=IntentClarificationService)
    return service


@pytest.fixture
def sample_session_id():
    """示例会话ID"""
    return "test_session_001"


class TestProcessClarificationFeedback:
    """测试处理澄清反馈端点"""
    
    def test_process_feedback_success(self, client, mock_service, sample_session_id):
        """测试成功处理反馈"""
        # Mock返回值
        mock_feedbacks = [
            ClarificationFeedback(
                question_id=0,
                user_response="本月",
                response_type="single_choice",
                confidence=1.0
            )
        ]
        
        mock_updates = [
            IntentUpdate(
                update_type=IntentUpdateType.TIME_RANGE,
                original_value=None,
                updated_value="本月",
                reasoning="用户选择了本月",
                confidence=1.0
            )
        ]
        
        mock_service.process_clarification_feedback.return_value = (mock_feedbacks, mock_updates)
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/process-feedback",
                json={
                    "session_id": sample_session_id,
                    "user_feedbacks": [
                        {
                            "response": "本月",
                            "type": "single_choice",
                            "confidence": 1.0
                        }
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "feedbacks" in data["data"]
        assert "intent_updates" in data["data"]
        assert len(data["data"]["feedbacks"]) == 1
        assert len(data["data"]["intent_updates"]) == 1
    
    def test_process_feedback_session_not_found(self, client, mock_service):
        """测试会话不存在"""
        mock_service.process_clarification_feedback.side_effect = ValueError("Session not found")
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/process-feedback",
                json={
                    "session_id": "nonexistent",
                    "user_feedbacks": []
                }
            )
        
        assert response.status_code == 404


class TestUpdateIntent:
    """测试更新意图端点"""
    
    def test_update_intent_success(self, client, mock_service, sample_session_id):
        """测试成功更新意图"""
        # Mock返回值
        mock_feedbacks = [
            ClarificationFeedback(
                question_id=0,
                user_response="本月",
                response_type="single_choice",
                confidence=1.0
            )
        ]
        
        mock_updates = [
            IntentUpdate(
                update_type=IntentUpdateType.TIME_RANGE,
                original_value=None,
                updated_value="本月",
                reasoning="用户选择了本月",
                confidence=1.0
            )
        ]
        
        mock_updated_intent = {
            "selected_tables": ["sales"],
            "time_range": "本月"
        }
        
        mock_service.process_clarification_feedback.return_value = (mock_feedbacks, mock_updates)
        mock_service.update_intent.return_value = mock_updated_intent
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/update-intent",
                json={
                    "session_id": sample_session_id,
                    "user_feedbacks": [
                        {
                            "response": "本月",
                            "type": "single_choice",
                            "confidence": 1.0
                        }
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "updated_intent" in data["data"]
        assert "intent_updates" in data["data"]
        assert data["data"]["updated_intent"]["time_range"] == "本月"
    
    def test_update_intent_session_not_found(self, client, mock_service):
        """测试会话不存在"""
        mock_service.process_clarification_feedback.side_effect = ValueError("Session not found")
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/update-intent",
                json={
                    "session_id": "nonexistent",
                    "user_feedbacks": []
                }
            )
        
        assert response.status_code == 404


class TestGetClarificationHistory:
    """测试获取澄清历史端点"""
    
    def test_get_history_success(self, client, mock_service, sample_session_id):
        """测试成功获取历史"""
        mock_history = [
            {
                "round_number": 1,
                "clarification_result": {
                    "clarification_needed": True,
                    "questions": [],
                    "summary": "理解您的问题",
                    "confidence": 0.8
                },
                "user_feedbacks": [],
                "intent_updates": [],
                "effectiveness_score": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        mock_service.get_clarification_history.return_value = mock_history
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.get(
                f"/api/intent-clarification/session/{sample_session_id}/clarification-history"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == sample_session_id
        assert data["total_rounds"] == 1
        assert len(data["history"]) == 1
    
    def test_get_history_empty(self, client, mock_service, sample_session_id):
        """测试空历史"""
        mock_service.get_clarification_history.return_value = []
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.get(
                f"/api/intent-clarification/session/{sample_session_id}/clarification-history"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_rounds"] == 0
        assert len(data["history"]) == 0


class TestRollback:
    """测试回溯端点"""
    
    def test_rollback_success(self, client, mock_service, sample_session_id):
        """测试成功回溯"""
        mock_result = {
            "session_id": sample_session_id,
            "round_number": 1,
            "clarification_result": {
                "clarification_needed": True,
                "questions": [],
                "summary": "理解您的问题"
            },
            "updated_intent": {
                "selected_tables": ["sales"]
            },
            "message": "已回溯到第 1 轮澄清"
        }
        
        mock_service.rollback_to_round.return_value = mock_result
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/rollback",
                json={
                    "session_id": sample_session_id,
                    "round_number": 1
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["round_number"] == 1
    
    def test_rollback_invalid_round(self, client, mock_service, sample_session_id):
        """测试无效轮次"""
        mock_service.rollback_to_round.side_effect = ValueError("Invalid round number")
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/rollback",
                json={
                    "session_id": sample_session_id,
                    "round_number": 99
                }
            )
        
        assert response.status_code == 400
    
    def test_rollback_session_not_found(self, client, mock_service):
        """测试会话不存在"""
        mock_service.rollback_to_round.side_effect = ValueError("Session not found")
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/rollback",
                json={
                    "session_id": "nonexistent",
                    "round_number": 1
                }
            )
        
        assert response.status_code == 400


class TestOptimizeClarificationStrategy:
    """测试优化澄清策略端点"""
    
    def test_optimize_with_recommendations(self, client, mock_service, sample_session_id):
        """测试有优化建议"""
        mock_result = {
            "session_id": sample_session_id,
            "avg_effectiveness": 0.5,
            "total_rounds": 3,
            "recommendations": [
                {
                    "type": "low_effectiveness",
                    "message": "澄清效果较低，建议简化问题",
                    "priority": "high"
                },
                {
                    "type": "too_many_rounds",
                    "message": "澄清轮次过多，建议在首轮提出更全面的问题",
                    "priority": "medium"
                }
            ]
        }
        
        mock_service.optimize_clarification_strategy.return_value = mock_result
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.get(
                f"/api/intent-clarification/session/{sample_session_id}/optimize"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "recommendations" in data["data"]
        assert len(data["data"]["recommendations"]) == 2
    
    def test_optimize_no_history(self, client, mock_service, sample_session_id):
        """测试无历史数据"""
        mock_result = {
            "session_id": sample_session_id,
            "recommendations": [],
            "message": "暂无历史数据，无法提供优化建议"
        }
        
        mock_service.optimize_clarification_strategy.return_value = mock_result
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.get(
                f"/api/intent-clarification/session/{sample_session_id}/optimize"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["recommendations"]) == 0
    
    def test_optimize_session_not_found(self, client, mock_service):
        """测试会话不存在"""
        mock_service.optimize_clarification_strategy.side_effect = ValueError("Session not found")
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.get(
                "/api/intent-clarification/session/nonexistent/optimize"
            )
        
        assert response.status_code == 404


class TestIntegration:
    """集成测试"""
    
    def test_complete_clarification_flow_with_updates(self, client, mock_service, sample_session_id):
        """测试完整的澄清流程（包含意图更新）"""
        # 1. 生成澄清问题
        mock_result = ClarificationResult(
            clarification_needed=True,
            questions=[
                ClarificationQuestion(
                    question="请确认时间范围",
                    options=["今天", "本周", "本月"],
                    question_type="single_choice",
                    reasoning="需要明确时间范围",
                    importance=0.8
                )
            ],
            summary="理解您想查询销售数据",
            confidence=0.8,
            reasoning="需要澄清时间范围"
        )
        
        mock_session = Mock()
        mock_session.session_id = sample_session_id
        mock_session.clarification_result = mock_result
        
        mock_service.generate_clarification.return_value = mock_result
        mock_service.create_session.return_value = mock_session
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/generate",
                json={
                    "original_question": "查询销售数据",
                    "table_selection": {
                        "selected_tables": [
                            {
                                "table_name": "sales",
                                "relevance_score": 0.9,
                                "reasoning": "销售表",
                                "relevant_fields": ["amount", "date"]
                            }
                        ],
                        "overall_reasoning": "选择销售表"
                    }
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["clarification_needed"] is True
        
        # 2. 处理用户反馈并更新意图
        mock_feedbacks = [
            ClarificationFeedback(
                question_id=0,
                user_response="本月",
                response_type="single_choice",
                confidence=1.0
            )
        ]
        
        mock_updates = [
            IntentUpdate(
                update_type=IntentUpdateType.TIME_RANGE,
                original_value=None,
                updated_value="本月",
                reasoning="用户选择了本月",
                confidence=1.0
            )
        ]
        
        mock_updated_intent = {
            "selected_tables": ["sales"],
            "time_range": "本月"
        }
        
        mock_service.process_clarification_feedback.return_value = (mock_feedbacks, mock_updates)
        mock_service.update_intent.return_value = mock_updated_intent
        
        with patch('src.api.intent_clarification_api.get_clarification_service', return_value=mock_service):
            response = client.post(
                "/api/intent-clarification/update-intent",
                json={
                    "session_id": sample_session_id,
                    "user_feedbacks": [
                        {
                            "response": "本月",
                            "type": "single_choice",
                            "confidence": 1.0
                        }
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["updated_intent"]["time_range"] == "本月"
