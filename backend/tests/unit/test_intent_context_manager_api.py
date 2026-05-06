"""
意图识别上下文管理 API 单元测试 - 任务 5.1.2
测试意图上下文管理的API接口
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.intent_context_manager_api import router
from src.services.intent_context_manager import (
    IntentContextManager,
    ContextualIntentResult,
    ClarificationRequest,
    IntentAdjustment,
    ConfidenceLevel,
    ClarificationReason
)
from src.services.intent_recognition_service import IntentResult, IntentType


# 创建测试应用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestIntentContextManagerAPI:
    """意图上下文管理API测试类"""
    
    @pytest.fixture
    def mock_manager(self):
        """模拟意图上下文管理器"""
        mock = Mock(spec=IntentContextManager)
        mock.identify_intent_with_context = AsyncMock()
        mock.confirm_intent_adjustment = AsyncMock()
        mock.get_session_intent_stats = Mock()
        mock._get_adjustment_history = Mock()
        mock.session_states = {}
        mock.confidence_thresholds = {
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.LOW: 0.0
        }
        mock.context_weight = 0.3
        mock.history_window = 5
        mock.intent_service = Mock()
        mock.context_manager = Mock()
        mock.ai_service = Mock()
        return mock
    
    @pytest.fixture
    def sample_contextual_result(self):
        """示例上下文意图识别结果"""
        intent_result = IntentResult(
            intent=IntentType.INTELLIGENT_QUERY,
            confidence=0.75,
            reasoning="用户询问具体数据",
            original_question="今天的销售额是多少？",
            metadata={"keywords": ["销售额", "今天"]}
        )
        
        return ContextualIntentResult(
            intent_result=intent_result,
            confidence_level=ConfidenceLevel.MEDIUM,
            context_influence={
                'historical_pattern': 'consistent',
                'conversation_flow': 'natural_progression',
                'question_similarity': 0.3,
                'context_score': 0.1
            },
            adjustment_history=[],
            clarification_needed=False,
            clarification_request=None
        )
    
    @pytest.fixture
    def sample_clarification_result(self):
        """示例需要澄清的结果"""
        intent_result = IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.3,
            reasoning="意图不明确",
            original_question="这个怎么样？",
            metadata={}
        )
        
        clarification_request = ClarificationRequest(
            session_id="test_session",
            original_question="这个怎么样？",
            detected_intent=IntentType.UNKNOWN,
            confidence=0.3,
            reason=ClarificationReason.LOW_CONFIDENCE,
            clarification_questions=["您是想要查询具体的数据结果，还是需要生成一份分析报告？"],
            suggested_intents=[
                (IntentType.INTELLIGENT_QUERY, 0.6),
                (IntentType.REPORT_GENERATION, 0.4)
            ],
            timestamp=datetime.now()
        )
        
        return ContextualIntentResult(
            intent_result=intent_result,
            confidence_level=ConfidenceLevel.LOW,
            context_influence={'context_score': 0.0},
            adjustment_history=[],
            clarification_needed=True,
            clarification_request=clarification_request
        )

    def test_identify_intent_with_context_success(self, mock_manager, sample_contextual_result):
        """测试成功的上下文意图识别"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.identify_intent_with_context.return_value = sample_contextual_result
            
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session_123",
                "user_question": "今天的销售额是多少？",
                "force_clarification": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "上下文意图识别成功"
            
            result_data = data["data"]
            assert result_data["intent_type"] == "intelligent_query"
            assert result_data["confidence"] == 0.75
            assert result_data["confidence_level"] == "medium"
            assert result_data["reasoning"] == "用户询问具体数据"
            assert result_data["clarification_needed"] is False
            assert result_data["clarification_request"] is None
            
            # 验证调用参数
            mock_manager.identify_intent_with_context.assert_called_once_with(
                session_id="test_session_123",
                user_question="今天的销售额是多少？",
                force_clarification=False
            )
    
    def test_identify_intent_with_clarification(self, mock_manager, sample_clarification_result):
        """测试需要澄清的意图识别"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.identify_intent_with_context.return_value = sample_clarification_result
            
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session",
                "user_question": "这个怎么样？",
                "force_clarification": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            result_data = data["data"]
            
            assert result_data["intent_type"] == "unknown"
            assert result_data["confidence"] == 0.3
            assert result_data["confidence_level"] == "low"
            assert result_data["clarification_needed"] is True
            
            # 验证澄清请求
            clarification = result_data["clarification_request"]
            assert clarification is not None
            assert clarification["session_id"] == "test_session"
            assert clarification["original_question"] == "这个怎么样？"
            assert clarification["detected_intent"] == "unknown"
            assert clarification["reason"] == "low_confidence"
            assert len(clarification["clarification_questions"]) > 0
            assert len(clarification["suggested_intents"]) > 0
    
    def test_identify_intent_with_force_clarification(self, mock_manager, sample_contextual_result):
        """测试强制澄清"""
        # 修改结果以包含澄清
        sample_contextual_result.clarification_needed = True
        sample_contextual_result.clarification_request = ClarificationRequest(
            session_id="test_session",
            original_question="今天的销售额是多少？",
            detected_intent=IntentType.INTELLIGENT_QUERY,
            confidence=0.75,
            reason=ClarificationReason.LOW_CONFIDENCE,
            clarification_questions=["请确认您的查询需求"],
            suggested_intents=[(IntentType.INTELLIGENT_QUERY, 0.75)],
            timestamp=datetime.now()
        )
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.identify_intent_with_context.return_value = sample_contextual_result
            
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session",
                "user_question": "今天的销售额是多少？",
                "force_clarification": True
            })
            
            assert response.status_code == 200
            data = response.json()
            
            result_data = data["data"]
            assert result_data["clarification_needed"] is True
            
            # 验证调用参数
            mock_manager.identify_intent_with_context.assert_called_once_with(
                session_id="test_session",
                user_question="今天的销售额是多少？",
                force_clarification=True
            )
    
    def test_identify_intent_with_adjustment_history(self, mock_manager):
        """测试包含调整历史的意图识别"""
        # 创建包含调整历史的结果
        intent_result = IntentResult(
            intent=IntentType.INTELLIGENT_QUERY,
            confidence=0.8,
            reasoning="调整后的意图",
            original_question="分析数据",
            metadata={"context_adjusted": True}
        )
        
        adjustment = IntentAdjustment(
            original_intent=IntentType.REPORT_GENERATION,
            adjusted_intent=IntentType.INTELLIGENT_QUERY,
            reason="上下文调整",
            confidence_change=0.2,
            timestamp=datetime.now(),
            user_confirmed=False
        )
        
        result = ContextualIntentResult(
            intent_result=intent_result,
            confidence_level=ConfidenceLevel.HIGH,
            context_influence={'context_score': 0.2},
            adjustment_history=[adjustment],
            clarification_needed=False
        )
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.identify_intent_with_context.return_value = result
            
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session",
                "user_question": "分析数据"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            result_data = data["data"]
            assert len(result_data["adjustment_history"]) == 1
            
            adjustment_data = result_data["adjustment_history"][0]
            assert adjustment_data["original_intent"] == "report_generation"
            assert adjustment_data["adjusted_intent"] == "intelligent_query"
            assert adjustment_data["reason"] == "上下文调整"
            assert adjustment_data["confidence_change"] == 0.2
            assert adjustment_data["user_confirmed"] is False
    
    def test_identify_intent_error(self, mock_manager):
        """测试意图识别错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.identify_intent_with_context.side_effect = Exception("AI服务错误")
            
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session",
                "user_question": "测试问题"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "上下文意图识别失败" in data["detail"]
    
    def test_confirm_intent_adjustment_success(self, mock_manager):
        """测试成功的意图调整确认"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.confirm_intent_adjustment.return_value = True
            
            response = client.post("/api/intent-context/confirm", json={
                "session_id": "test_session",
                "confirmed_intent": "intelligent_query",
                "user_feedback": "是的，我想查询数据"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["data"] is True
            assert data["message"] == "意图调整确认成功"
            
            # 验证调用参数
            mock_manager.confirm_intent_adjustment.assert_called_once_with(
                session_id="test_session",
                confirmed_intent=IntentType.INTELLIGENT_QUERY,
                user_feedback="是的，我想查询数据"
            )
    
    def test_confirm_intent_adjustment_failure(self, mock_manager):
        """测试意图调整确认失败"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.confirm_intent_adjustment.return_value = False
            
            response = client.post("/api/intent-context/confirm", json={
                "session_id": "test_session",
                "confirmed_intent": "intelligent_query"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is False
            assert data["data"] is False
            assert data["message"] == "意图调整确认失败"
    
    def test_confirm_intent_invalid_intent_type(self, mock_manager):
        """测试无效的意图类型"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.post("/api/intent-context/confirm", json={
                "session_id": "test_session",
                "confirmed_intent": "invalid_intent_type"
            })
            
            assert response.status_code == 400
            data = response.json()
            assert "无效的意图类型" in data["detail"]
    
    def test_confirm_intent_error(self, mock_manager):
        """测试意图确认错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.confirm_intent_adjustment.side_effect = Exception("确认失败")
            
            response = client.post("/api/intent-context/confirm", json={
                "session_id": "test_session",
                "confirmed_intent": "intelligent_query"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "意图确认失败" in data["detail"]
    
    def test_get_session_intent_stats_success(self, mock_manager):
        """测试成功获取会话意图统计"""
        mock_stats = {
            "session_id": "test_session",
            "total_intents": 5,
            "intent_distribution": {
                "intelligent_query": 0.6,
                "report_generation": 0.4
            },
            "last_intent": IntentType.INTELLIGENT_QUERY,
            "last_confidence": 0.85,
            "last_update": datetime.now(),
            "adjustment_count": 2
        }
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.get_session_intent_stats.return_value = mock_stats
            
            response = client.get("/api/intent-context/session/test_session/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "会话意图统计获取成功"
            
            stats_data = data["data"]
            assert stats_data["session_id"] == "test_session"
            assert stats_data["total_intents"] == 5
            assert stats_data["last_intent"] == "intelligent_query"
            assert stats_data["last_confidence"] == 0.85
            assert stats_data["adjustment_count"] == 2
            assert "intent_distribution" in stats_data
    
    def test_get_session_intent_stats_error(self, mock_manager):
        """测试获取会话统计错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager.get_session_intent_stats.side_effect = Exception("统计错误")
            
            response = client.get("/api/intent-context/session/test_session/stats")
            
            assert response.status_code == 500
            data = response.json()
            assert "获取会话意图统计失败" in data["detail"]
    
    def test_get_session_adjustments_success(self, mock_manager):
        """测试成功获取会话调整历史"""
        mock_adjustments = [
            IntentAdjustment(
                original_intent=IntentType.REPORT_GENERATION,
                adjusted_intent=IntentType.INTELLIGENT_QUERY,
                reason="上下文调整",
                confidence_change=0.2,
                timestamp=datetime.now(),
                user_confirmed=True
            )
        ]
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager._get_adjustment_history.return_value = mock_adjustments
            
            response = client.get("/api/intent-context/session/test_session/adjustments")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "意图调整历史获取成功"
            
            adjustments_data = data["data"]
            assert len(adjustments_data) == 1
            
            adjustment = adjustments_data[0]
            assert adjustment["original_intent"] == "report_generation"
            assert adjustment["adjusted_intent"] == "intelligent_query"
            assert adjustment["reason"] == "上下文调整"
            assert adjustment["confidence_change"] == 0.2
            assert adjustment["user_confirmed"] is True
    
    def test_get_session_adjustments_error(self, mock_manager):
        """测试获取调整历史错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            mock_manager._get_adjustment_history.side_effect = Exception("历史错误")
            
            response = client.get("/api/intent-context/session/test_session/adjustments")
            
            assert response.status_code == 500
            data = response.json()
            assert "获取意图调整历史失败" in data["detail"]
    
    def test_clear_session_context_success(self, mock_manager):
        """测试成功清除会话上下文"""
        mock_manager.session_states = {"test_session": {"some": "data"}}
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.delete("/api/intent-context/session/test_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["data"] is True
            assert data["message"] == "会话上下文清除成功"
            
            # 验证会话状态已清除
            assert "test_session" not in mock_manager.session_states
    
    def test_clear_session_context_nonexistent(self, mock_manager):
        """测试清除不存在的会话上下文"""
        mock_manager.session_states = {}
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.delete("/api/intent-context/session/nonexistent_session")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["data"] is True
    
    def test_clear_session_context_error(self, mock_manager):
        """测试清除会话上下文错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            # 模拟删除操作错误
            def side_effect(*args):
                raise Exception("清除错误")
            
            mock_manager.session_states.__delitem__ = side_effect
            mock_manager.session_states.__contains__ = lambda self, key: True
            
            response = client.delete("/api/intent-context/session/test_session")
            
            assert response.status_code == 500
            data = response.json()
            assert "清除会话上下文失败" in data["detail"]
    
    def test_get_confidence_levels(self, mock_manager):
        """测试获取置信度级别配置"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.get("/api/intent-context/confidence-levels")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "置信度级别配置获取成功"
            
            config_data = data["data"]
            assert "high" in config_data
            assert "medium" in config_data
            assert "low" in config_data
            assert config_data["high"] == 0.8
            assert config_data["medium"] == 0.5
            assert config_data["low"] == 0.0
    
    def test_get_clarification_reasons(self):
        """测试获取澄清原因列表"""
        response = client.get("/api/intent-context/clarification-reasons")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "澄清原因列表获取成功"
        
        reasons = data["data"]
        assert isinstance(reasons, list)
        assert "low_confidence" in reasons
        assert "ambiguous_intent" in reasons
        assert "context_conflict" in reasons
        assert "missing_information" in reasons
    
    def test_health_check(self, mock_manager):
        """测试健康检查"""
        mock_manager.session_states = {"session1": {}, "session2": {}}
        
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.get("/api/intent-context/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["message"] == "意图上下文管理器健康检查成功"
            
            health_data = data["data"]
            assert health_data["status"] == "healthy"
            assert health_data["active_sessions"] == 2
            assert "dependencies" in health_data
            assert "configuration" in health_data
            assert "timestamp" in health_data
            
            # 验证依赖状态
            dependencies = health_data["dependencies"]
            assert "intent_service" in dependencies
            assert "context_manager" in dependencies
            assert "ai_service" in dependencies
            
            # 验证配置信息
            config = health_data["configuration"]
            assert config["context_weight"] == 0.3
            assert config["history_window"] == 5
            assert "confidence_thresholds" in config
    
    def test_health_check_error(self, mock_manager):
        """测试健康检查错误"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            # 模拟获取会话状态错误
            mock_manager.session_states = Mock()
            mock_manager.session_states.__len__.side_effect = Exception("健康检查错误")
            
            response = client.get("/api/intent-context/health")
            
            assert response.status_code == 500
            data = response.json()
            assert "健康检查失败" in data["detail"]
    
    def test_invalid_request_data(self, mock_manager):
        """测试无效的请求数据"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            # 缺少必需字段
            response = client.post("/api/intent-context/identify", json={
                "session_id": "test_session"
                # 缺少 user_question
            })
            
            assert response.status_code == 422  # Validation error
    
    def test_empty_request_data(self, mock_manager):
        """测试空请求数据"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager', return_value=mock_manager):
            response = client.post("/api/intent-context/identify", json={})
            
            assert response.status_code == 422  # Validation error


class TestIntentContextManagerAPIIntegration:
    """API集成测试"""
    
    def test_full_api_workflow(self):
        """测试完整的API工作流程"""
        with patch('src.api.intent_context_manager_api.get_intent_context_manager') as mock_get_manager:
            mock_manager = Mock(spec=IntentContextManager)
            mock_get_manager.return_value = mock_manager
            
            # 设置模拟返回值
            intent_result = IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.2,
                reasoning="意图不明确",
                original_question="这个怎么办？",
                metadata={}
            )
            
            clarification_request = ClarificationRequest(
                session_id="workflow_test",
                original_question="这个怎么办？",
                detected_intent=IntentType.UNKNOWN,
                confidence=0.2,
                reason=ClarificationReason.LOW_CONFIDENCE,
                clarification_questions=["请明确您的需求"],
                suggested_intents=[(IntentType.INTELLIGENT_QUERY, 0.6)],
                timestamp=datetime.now()
            )
            
            contextual_result = ContextualIntentResult(
                intent_result=intent_result,
                confidence_level=ConfidenceLevel.LOW,
                context_influence={'context_score': 0.0},
                adjustment_history=[],
                clarification_needed=True,
                clarification_request=clarification_request
            )
            
            mock_manager.identify_intent_with_context.return_value = contextual_result
            mock_manager.confirm_intent_adjustment.return_value = True
            mock_manager.get_session_intent_stats.return_value = {
                "session_id": "workflow_test",
                "total_intents": 1,
                "intent_distribution": {"unknown": 1.0},
                "last_intent": IntentType.UNKNOWN,
                "last_confidence": 0.2,
                "last_update": datetime.now(),
                "adjustment_count": 0
            }
            
            # 1. 识别意图（需要澄清）
            response1 = client.post("/api/intent-context/identify", json={
                "session_id": "workflow_test",
                "user_question": "这个怎么办？"
            })
            
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["data"]["clarification_needed"] is True
            
            # 2. 确认意图
            response2 = client.post("/api/intent-context/confirm", json={
                "session_id": "workflow_test",
                "confirmed_intent": "intelligent_query",
                "user_feedback": "我想查询数据"
            })
            
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["data"] is True
            
            # 3. 获取会话统计
            response3 = client.get("/api/intent-context/session/workflow_test/stats")
            
            assert response3.status_code == 200
            data3 = response3.json()
            assert data3["data"]["session_id"] == "workflow_test"
            
            # 4. 清除会话
            mock_manager.session_states = {"workflow_test": {}}
            response4 = client.delete("/api/intent-context/session/workflow_test")
            
            assert response4.status_code == 200
            data4 = response4.json()
            assert data4["data"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])