"""
意图识别API单元测试
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app
from src.services.intent_recognition_service import (
    IntentResult,
    IntentType,
    IntentRecognitionError
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_intent_service():
    """模拟意图识别服务"""
    mock_service = MagicMock()
    mock_service.identify_intent = AsyncMock()
    mock_service.get_intent_statistics = MagicMock()
    mock_service.reset_statistics = MagicMock()
    return mock_service


class TestIntentRecognitionAPI:
    """意图识别API测试类"""
    
    def test_recognize_intent_success(self, client, mock_intent_service):
        """测试成功的意图识别"""
        # 准备测试数据
        request_data = {
            "user_question": "查询最近一个月的销售数据",
            "context": {
                "conversation_history": [],
                "user_preferences": {"language": "zh-CN"}
            }
        }
        
        # 模拟服务返回
        mock_result = IntentResult(
            intent=IntentType.QUERY,
            confidence=0.95,
            reasoning="用户明确要求查询销售数据",
            original_question=request_data["user_question"],
            metadata={"processing_time": 1.2}
        )
        mock_intent_service.identify_intent.return_value = mock_result
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["intent"] == "query"
        assert response_data["confidence"] == 0.95
        assert response_data["reasoning"] == "用户明确要求查询销售数据"
        assert response_data["original_question"] == request_data["user_question"]
        assert response_data["metadata"]["processing_time"] == 1.2
        
        # 验证服务调用
        mock_intent_service.identify_intent.assert_called_once_with(
            user_question=request_data["user_question"],
            context=request_data["context"]
        )
    
    def test_recognize_intent_report_type(self, client, mock_intent_service):
        """测试报告类型意图识别"""
        # 准备测试数据
        request_data = {
            "user_question": "生成本季度的销售分析报告"
        }
        
        # 模拟服务返回
        mock_result = IntentResult(
            intent=IntentType.REPORT,
            confidence=0.88,
            reasoning="用户要求生成分析报告",
            original_question=request_data["user_question"]
        )
        mock_intent_service.identify_intent.return_value = mock_result
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["intent"] == "report"
        assert response_data["confidence"] == 0.88
    
    def test_recognize_intent_without_context(self, client, mock_intent_service):
        """测试不带上下文的意图识别"""
        # 准备测试数据
        request_data = {
            "user_question": "查询数据"
        }
        
        # 模拟服务返回
        mock_result = IntentResult(
            intent=IntentType.QUERY,
            confidence=0.75,
            reasoning="简单查询请求",
            original_question=request_data["user_question"]
        )
        mock_intent_service.identify_intent.return_value = mock_result
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        
        # 验证服务调用（context应该为None）
        mock_intent_service.identify_intent.assert_called_once_with(
            user_question=request_data["user_question"],
            context=None
        )
    
    def test_recognize_intent_empty_question(self, client):
        """测试空问题"""
        # 准备测试数据
        request_data = {
            "user_question": ""
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_recognize_intent_missing_question(self, client):
        """测试缺少问题字段"""
        # 准备测试数据
        request_data = {
            "context": {"test": "value"}
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_recognize_intent_service_error(self, client, mock_intent_service):
        """测试服务错误"""
        # 准备测试数据
        request_data = {
            "user_question": "查询数据"
        }
        
        # 模拟服务抛出异常
        mock_intent_service.identify_intent.side_effect = IntentRecognitionError(
            "意图识别失败",
            request_data["user_question"]
        )
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应
        assert response.status_code == 400
        
        response_data = response.json()
        assert response_data["detail"]["error"] == "意图识别失败"
        assert response_data["detail"]["original_question"] == request_data["user_question"]
    
    def test_recognize_intent_unexpected_error(self, client, mock_intent_service):
        """测试意外错误"""
        # 准备测试数据
        request_data = {
            "user_question": "查询数据"
        }
        
        # 模拟服务抛出意外异常
        mock_intent_service.identify_intent.side_effect = Exception("意外错误")
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应
        assert response.status_code == 500
        
        response_data = response.json()
        assert response_data["detail"]["error"] == "服务器内部错误"
    
    def test_get_intent_statistics_success(self, client, mock_intent_service):
        """测试获取统计信息成功"""
        # 模拟统计数据
        mock_stats = {
            "total_requests": 100,
            "successful_recognitions": 95,
            "failed_recognitions": 5,
            "success_rate": 0.95,
            "failure_rate": 0.05,
            "avg_confidence": 0.87,
            "avg_response_time": 1.5,
            "intent_distribution": {
                "query": 0.7,
                "report": 0.25,
                "unknown": 0.05
            }
        }
        mock_intent_service.get_intent_statistics.return_value = mock_stats
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.get("/api/intent/statistics")
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["total_requests"] == 100
        assert response_data["success_rate"] == 0.95
        assert response_data["avg_confidence"] == 0.87
        assert response_data["intent_distribution"]["query"] == 0.7
    
    def test_get_intent_statistics_error(self, client, mock_intent_service):
        """测试获取统计信息错误"""
        # 模拟服务抛出异常
        mock_intent_service.get_intent_statistics.side_effect = Exception("统计信息获取失败")
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.get("/api/intent/statistics")
        
        # 验证响应
        assert response.status_code == 500
        
        response_data = response.json()
        assert response_data["detail"]["error"] == "获取统计信息失败"
    
    def test_reset_intent_statistics_success(self, client, mock_intent_service):
        """测试重置统计信息成功"""
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/statistics/reset")
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["success"] is True
        assert "重置" in response_data["message"]
        
        # 验证服务调用
        mock_intent_service.reset_statistics.assert_called_once()
    
    def test_reset_intent_statistics_error(self, client, mock_intent_service):
        """测试重置统计信息错误"""
        # 模拟服务抛出异常
        mock_intent_service.reset_statistics.side_effect = Exception("重置失败")
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/statistics/reset")
        
        # 验证响应
        assert response.status_code == 500
        
        response_data = response.json()
        assert response_data["detail"]["error"] == "重置统计信息失败"
    
    def test_health_check_success(self, client, mock_intent_service):
        """测试健康检查成功"""
        # 模拟统计数据
        mock_stats = {
            "total_requests": 50,
            "success_rate": 0.9,
            "avg_response_time": 1.2
        }
        mock_intent_service.get_intent_statistics.return_value = mock_stats
        mock_intent_service.confidence_threshold = 0.7
        mock_intent_service.max_retries = 3
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.get("/api/intent/health")
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert response_data["service"] == "intent_recognition"
        assert response_data["statistics"]["total_requests"] == 50
        assert response_data["configuration"]["confidence_threshold"] == 0.7
    
    def test_health_check_error(self, client, mock_intent_service):
        """测试健康检查错误"""
        # 模拟服务抛出异常
        mock_intent_service.get_intent_statistics.side_effect = Exception("健康检查失败")
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.get("/api/intent/health")
        
        # 验证响应
        assert response.status_code == 503
        
        response_data = response.json()
        assert response_data["detail"]["status"] == "unhealthy"
    
    def test_batch_recognize_intents_success(self, client, mock_intent_service):
        """测试批量意图识别成功"""
        # 准备测试数据
        request_data = {
            "questions": [
                "查询销售数据",
                "生成报告",
                "显示图表"
            ],
            "context": {
                "user_preferences": {"language": "zh-CN"}
            }
        }
        
        # 模拟服务返回
        mock_results = [
            IntentResult(
                intent=IntentType.QUERY,
                confidence=0.9,
                reasoning="查询请求",
                original_question="查询销售数据"
            ),
            IntentResult(
                intent=IntentType.REPORT,
                confidence=0.85,
                reasoning="报告生成",
                original_question="生成报告"
            ),
            IntentResult(
                intent=IntentType.QUERY,
                confidence=0.8,
                reasoning="图表显示",
                original_question="显示图表"
            )
        ]
        
        # 设置side_effect来模拟多次调用
        mock_intent_service.identify_intent.side_effect = mock_results
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize/batch", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert len(response_data["results"]) == 3
        assert response_data["results"][0]["intent"] == "query"
        assert response_data["results"][1]["intent"] == "report"
        assert response_data["results"][2]["intent"] == "query"
        
        # 验证摘要
        summary = response_data["summary"]
        assert summary["total_questions"] == 3
        assert summary["successful_recognitions"] == 3
        assert summary["failed_recognitions"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["avg_confidence"] == 0.85  # (0.9 + 0.85 + 0.8) / 3
    
    def test_batch_recognize_intents_partial_failure(self, client, mock_intent_service):
        """测试批量意图识别部分失败"""
        # 准备测试数据
        request_data = {
            "questions": [
                "查询销售数据",
                "无效问题"
            ]
        }
        
        # 模拟服务返回 - 第一个成功，第二个失败
        mock_intent_service.identify_intent.side_effect = [
            IntentResult(
                intent=IntentType.QUERY,
                confidence=0.9,
                reasoning="查询请求",
                original_question="查询销售数据"
            ),
            IntentRecognitionError("识别失败", "无效问题")
        ]
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize/batch", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        
        response_data = response.json()
        assert len(response_data["results"]) == 2
        assert response_data["results"][0]["intent"] == "query"
        assert response_data["results"][1]["intent"] == "unknown"
        assert response_data["results"][1]["confidence"] == 0.0
        
        # 验证摘要
        summary = response_data["summary"]
        assert summary["total_questions"] == 2
        assert summary["successful_recognitions"] == 1
        assert summary["failed_recognitions"] == 1
        assert summary["success_rate"] == 0.5
    
    def test_batch_recognize_intents_empty_questions(self, client):
        """测试批量识别空问题列表"""
        # 准备测试数据
        request_data = {
            "questions": []
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize/batch", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_batch_recognize_intents_too_many_questions(self, client):
        """测试批量识别问题过多"""
        # 准备测试数据 - 超过10个问题
        request_data = {
            "questions": [f"问题{i}" for i in range(15)]
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize/batch", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_batch_recognize_intents_service_error(self, client, mock_intent_service):
        """测试批量识别服务错误"""
        # 准备测试数据
        request_data = {
            "questions": ["查询数据"]
        }
        
        # 模拟服务抛出异常
        mock_intent_service.identify_intent.side_effect = Exception("服务不可用")
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize/batch", json=request_data)
        
        # 验证响应
        assert response.status_code == 500
        
        response_data = response.json()
        assert response_data["detail"]["error"] == "批量意图识别失败"


class TestIntentRecognitionAPIValidation:
    """意图识别API验证测试"""
    
    def test_request_validation_question_too_long(self, client):
        """测试问题过长验证"""
        # 准备测试数据 - 超过1000字符
        request_data = {
            "user_question": "查询" * 500  # 1000个字符
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_request_validation_invalid_context_type(self, client):
        """测试无效上下文类型"""
        # 准备测试数据
        request_data = {
            "user_question": "查询数据",
            "context": "这应该是一个字典"  # 错误的类型
        }
        
        # 执行测试
        response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应 - 应该返回422验证错误
        assert response.status_code == 422
    
    def test_response_model_validation(self, client, mock_intent_service):
        """测试响应模型验证"""
        # 准备测试数据
        request_data = {
            "user_question": "查询数据"
        }
        
        # 模拟服务返回
        mock_result = IntentResult(
            intent=IntentType.QUERY,
            confidence=0.95,
            reasoning="测试推理",
            original_question=request_data["user_question"],
            metadata={"test": "value"}
        )
        mock_intent_service.identify_intent.return_value = mock_result
        
        # 执行测试
        with patch('src.api.intent_recognition_api.get_intent_service', return_value=mock_intent_service):
            response = client.post("/api/intent/recognize", json=request_data)
        
        # 验证响应格式
        assert response.status_code == 200
        
        response_data = response.json()
        
        # 验证必需字段
        required_fields = ["intent", "confidence", "reasoning", "original_question"]
        for field in required_fields:
            assert field in response_data
        
        # 验证字段类型
        assert isinstance(response_data["intent"], str)
        assert isinstance(response_data["confidence"], float)
        assert isinstance(response_data["reasoning"], str)
        assert isinstance(response_data["original_question"], str)
        
        # 验证置信度范围
        assert 0.0 <= response_data["confidence"] <= 1.0