"""
本地数据分析引擎API单元测试
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app
from src.services.local_data_analyzer import AnalysisResult


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_analysis_request():
    """示例分析请求"""
    return {
        "session_id": "session_001",
        "query_result": {
            "query_id": "query_001",
            "sql": "SELECT * FROM sales",
            "data": [
                {"date": "2024-01-01", "amount": 1000},
                {"date": "2024-01-02", "amount": 1500}
            ],
            "columns": ["date", "amount"],
            "row_count": 2,
            "executed_at": "2024-01-01T10:00:00"
        },
        "previous_results": [],
        "conversation_history": [],
        "user_question": "这些数据显示了什么？",
        "stream": False
    }


@pytest.fixture
def sample_comparison_request():
    """示例对比请求"""
    return {
        "session_id": "session_001",
        "current_result": {
            "query_id": "query_002",
            "sql": "SELECT * FROM sales WHERE month = 2",
            "data": [{"amount": 2000}],
            "columns": ["amount"],
            "row_count": 1,
            "executed_at": "2024-02-01T10:00:00"
        },
        "previous_result": {
            "query_id": "query_001",
            "sql": "SELECT * FROM sales WHERE month = 1",
            "data": [{"amount": 1500}],
            "columns": ["amount"],
            "row_count": 1,
            "executed_at": "2024-01-01T10:00:00"
        },
        "comparison_question": "销售额有什么变化？"
    }


@pytest.fixture
def mock_analyzer():
    """Mock分析器"""
    with patch('src.api.local_data_analyzer_api.get_analyzer') as mock:
        analyzer = MagicMock()
        mock.return_value = analyzer
        yield analyzer


class TestAnalyzeDataEndpoint:
    """测试数据分析端点"""
    
    def test_analyze_data_success(self, client, sample_analysis_request, mock_analyzer):
        """测试成功分析数据"""
        mock_result = AnalysisResult(
            analysis_id="analysis_001",
            question="这些数据显示了什么？",
            answer="数据显示销售额在增长。",
            insights=["销售额增长了50%"],
            data_points=[],
            created_at=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        mock_analyzer.analyze_data = AsyncMock(return_value=mock_result)
        
        response = client.post("/api/local-analyzer/analyze", json=sample_analysis_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == "analysis_001"
        assert "增长" in data["answer"]
        assert len(data["insights"]) > 0
    
    def test_analyze_data_invalid_request(self, client):
        """测试无效请求"""
        invalid_request = {"session_id": "session_001"}
        
        response = client.post("/api/local-analyzer/analyze", json=invalid_request)
        
        assert response.status_code == 422
    
    def test_analyze_data_service_error(self, client, sample_analysis_request, mock_analyzer):
        """测试服务错误"""
        mock_analyzer.analyze_data = AsyncMock(side_effect=Exception("分析失败"))
        
        response = client.post("/api/local-analyzer/analyze", json=sample_analysis_request)
        
        assert response.status_code == 500
        assert "分析失败" in response.json()["detail"]


class TestStatsEndpoints:
    """测试统计端点"""
    
    def test_get_stats_success(self, client, mock_analyzer):
        """测试成功获取统计"""
        mock_analyzer.get_stats.return_value = {
            "total_analyses": 100,
            "successful_analyses": 95,
            "failed_analyses": 5,
            "total_tokens_used": 15000,
            "average_response_time": 2.5
        }
        
        response = client.get("/api/local-analyzer/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_analyses"] == 100
        assert data["successful_analyses"] == 95
        assert data["success_rate"] == 95.0
    
    def test_reset_stats_success(self, client, mock_analyzer):
        """测试成功重置统计"""
        mock_analyzer.reset_stats.return_value = None
        
        response = client.post("/api/local-analyzer/stats/reset")
        
        assert response.status_code == 200
        assert response.json()["message"] == "统计信息已重置"
