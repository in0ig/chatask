"""
语义上下文聚合引擎API测试

测试语义上下文聚合引擎的API端点：聚合请求、批量聚合、模块信息查询、
缓存管理、健康检查等功能。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from src.main import app
from src.services.semantic_context_aggregator import (
    SemanticContextAggregator,
    TokenBudget,
    ModuleType,
    ContextPriority,
    AggregationResult
)


class TestSemanticContextAggregatorAPI:
    """语义上下文聚合引擎API测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_aggregation_result(self):
        """模拟聚合结果"""
        return AggregationResult(
            enhanced_context="用户问题: 测试问题\n\nTable Structure:\n表结构语义信息",
            modules_used=["table_structure", "dictionary"],
            total_tokens_used=500,
            token_budget_remaining=1500,
            relevance_scores={
                "table_structure": 0.9,
                "dictionary": 0.8,
                "data_source": 0.7,
                "table_relation": 0.6,
                "knowledge": 0.5
            },
            optimization_summary={
                "total_modules_available": 5,
                "modules_selected": 2,
                "token_budget_used": 500,
                "token_budget_total": 2000,
                "token_utilization_rate": 0.25,
                "modules_by_priority": {
                    "critical": 1,
                    "high": 1,
                    "medium": 0,
                    "low": 0
                },
                "average_relevance_score": 0.85
            }
        )
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_aggregate_semantic_context_success(self, mock_aggregator_class, client, mock_aggregation_result):
        """测试语义上下文聚合成功"""
        # 设置mock
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_aggregation_result)
        mock_aggregator_class.return_value = mock_aggregator
        
        # 准备请求数据
        request_data = {
            "user_question": "查询用户订单信息",
            "table_ids": ["users", "orders"],
            "include_global": True,
            "token_budget": {
                "total_budget": 2000,
                "reserved_for_response": 500
            },
            "module_priorities": {
                "table_structure": "critical",
                "dictionary": "high",
                "data_source": "medium"
            }
        }
        
        # 发送请求
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "语义上下文聚合成功"
        assert "data" in data
        
        result_data = data["data"]
        assert result_data["enhanced_context"] == mock_aggregation_result.enhanced_context
        assert result_data["modules_used"] == mock_aggregation_result.modules_used
        assert result_data["total_tokens_used"] == mock_aggregation_result.total_tokens_used
        assert result_data["token_budget_remaining"] == mock_aggregation_result.token_budget_remaining
        assert result_data["relevance_scores"] == mock_aggregation_result.relevance_scores
        assert result_data["optimization_summary"] == mock_aggregation_result.optimization_summary
        
        # 验证服务调用
        mock_aggregator.aggregate_semantic_context.assert_called_once()
        call_args = mock_aggregator.aggregate_semantic_context.call_args
        assert call_args.kwargs["user_question"] == "查询用户订单信息"
        assert call_args.kwargs["table_ids"] == ["users", "orders"]
        assert call_args.kwargs["include_global"] is True
        assert isinstance(call_args.kwargs["token_budget"], TokenBudget)
        assert call_args.kwargs["token_budget"].total_budget == 2000
        assert call_args.kwargs["token_budget"].reserved_for_response == 500
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_aggregate_semantic_context_minimal_request(self, mock_aggregator_class, client, mock_aggregation_result):
        """测试最小请求参数的语义上下文聚合"""
        # 设置mock
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_aggregation_result)
        mock_aggregator_class.return_value = mock_aggregator
        
        # 最小请求数据
        request_data = {
            "user_question": "简单查询"
        }
        
        # 发送请求
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证服务调用使用默认参数
        mock_aggregator.aggregate_semantic_context.assert_called_once()
        call_args = mock_aggregator.aggregate_semantic_context.call_args
        assert call_args.kwargs["user_question"] == "简单查询"
        assert call_args.kwargs["table_ids"] is None
        assert call_args.kwargs["include_global"] is True
        assert call_args.kwargs["token_budget"] is None
        assert call_args.kwargs["module_priorities"] is None
    
    def test_aggregate_semantic_context_invalid_request(self, client):
        """测试无效请求参数"""
        # 缺少必需参数
        request_data = {}
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        assert response.status_code == 422  # Validation error
        
        # 无效的Token预算
        request_data = {
            "user_question": "测试",
            "token_budget": {
                "total_budget": 500,  # 太小
                "reserved_for_response": 600  # 超过总预算
            }
        }
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        assert response.status_code == 422
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_aggregate_semantic_context_service_error(self, mock_aggregator_class, client):
        """测试服务异常处理"""
        # 设置mock抛出异常
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(side_effect=Exception("服务异常"))
        mock_aggregator_class.return_value = mock_aggregator
        
        request_data = {
            "user_question": "测试问题"
        }
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        
        # 验证错误响应
        assert response.status_code == 500
        data = response.json()
        assert "语义上下文聚合失败" in data["detail"]
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_batch_aggregate_semantic_context_success(self, mock_aggregator_class, client, mock_aggregation_result):
        """测试批量语义上下文聚合成功"""
        # 设置mock
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_aggregation_result)
        mock_aggregator_class.return_value = mock_aggregator
        
        # 批量请求数据
        request_data = {
            "requests": [
                {
                    "user_question": "查询用户信息",
                    "table_ids": ["users"]
                },
                {
                    "user_question": "查询订单信息",
                    "table_ids": ["orders"]
                }
            ]
        }
        
        # 发送请求
        response = client.post("/api/semantic-context/batch-aggregate", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "处理了2个请求" in data["message"]
        assert len(data["data"]) == 2
        
        # 验证每个结果
        for result in data["data"]:
            assert result["enhanced_context"] == mock_aggregation_result.enhanced_context
            assert result["modules_used"] == mock_aggregation_result.modules_used
        
        # 验证服务被调用了两次
        assert mock_aggregator.aggregate_semantic_context.call_count == 2
    
    def test_batch_aggregate_too_many_requests(self, client):
        """测试批量请求数量限制"""
        # 超过10个请求的批量数据
        requests = [{"user_question": f"问题{i}"} for i in range(11)]
        request_data = {"requests": requests}
        
        response = client.post("/api/semantic-context/batch-aggregate", json=request_data)
        
        # 验证错误响应 - Pydantic验证失败返回422
        assert response.status_code == 422
        data = response.json()
        # 验证错误信息中包含数量限制相关内容
        assert "detail" in data
    
    def test_get_available_modules_success(self, client):
        """测试获取可用模块信息成功"""
        response = client.get("/api/semantic-context/modules")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "获取模块信息成功"
        assert "data" in data
        
        modules_info = data["data"]
        assert "module_types" in modules_info
        assert "priority_levels" in modules_info
        assert "default_priorities" in modules_info
        assert "token_budget_defaults" in modules_info
        
        # 验证模块类型
        expected_module_types = ["data_source", "table_structure", "table_relation", "dictionary", "knowledge"]
        assert set(modules_info["module_types"]) == set(expected_module_types)
        
        # 验证优先级级别
        expected_priorities = ["critical", "high", "medium", "low"]
        assert set(modules_info["priority_levels"]) == set(expected_priorities)
        
        # 验证默认优先级
        default_priorities = modules_info["default_priorities"]
        assert default_priorities["table_structure"] == "critical"
        assert default_priorities["dictionary"] == "high"
        
        # 验证Token预算默认值
        token_defaults = modules_info["token_budget_defaults"]
        assert token_defaults["total_budget"] == 4000
        assert token_defaults["reserved_for_response"] == 1000
        assert token_defaults["available_for_context"] == 3000
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_clear_aggregator_cache_success(self, mock_aggregator_class, client):
        """测试清空聚合器缓存成功"""
        # 设置mock
        mock_aggregator = Mock()
        mock_aggregator.clear_cache = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        
        # 发送请求
        response = client.post("/api/semantic-context/clear-cache")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "聚合器缓存清空成功"
        assert data["data"]["status"] == "cleared"
        
        # 验证服务调用
        mock_aggregator.clear_cache.assert_called_once()
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_clear_cache_service_error(self, mock_aggregator_class, client):
        """测试清空缓存服务异常"""
        # 设置mock抛出异常
        mock_aggregator = Mock()
        mock_aggregator.clear_cache = Mock(side_effect=Exception("清空失败"))
        mock_aggregator_class.return_value = mock_aggregator
        
        response = client.post("/api/semantic-context/clear-cache")
        
        # 验证错误响应
        assert response.status_code == 500
        data = response.json()
        assert "清空缓存失败" in data["detail"]
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_health_check_success(self, mock_aggregator_class, client, mock_aggregation_result):
        """测试健康检查成功"""
        # 设置mock
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_aggregation_result)
        mock_aggregator_class.return_value = mock_aggregator
        
        # 发送请求
        response = client.get("/api/semantic-context/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "语义上下文聚合引擎健康"
        assert "data" in data
        
        health_info = data["data"]
        assert health_info["status"] == "healthy"
        assert health_info["modules_available"] == 5
        assert "test_aggregation" in health_info
        assert health_info["test_aggregation"]["success"] is True
        assert health_info["cache_status"] == "active"
        
        # 验证测试聚合调用
        mock_aggregator.aggregate_semantic_context.assert_called_once()
        call_args = mock_aggregator.aggregate_semantic_context.call_args
        assert call_args.kwargs["user_question"] == "测试问题"
        assert call_args.kwargs["include_global"] is False
    
    @patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator')
    def test_health_check_unhealthy(self, mock_aggregator_class, client):
        """测试健康检查异常"""
        # 设置mock抛出异常
        mock_aggregator = Mock()
        mock_aggregator.aggregate_semantic_context = AsyncMock(side_effect=Exception("健康检查失败"))
        mock_aggregator_class.return_value = mock_aggregator
        
        response = client.get("/api/semantic-context/health")
        
        # 验证响应
        assert response.status_code == 200  # 健康检查不应该返回500
        data = response.json()
        
        assert data["success"] is False
        assert data["message"] == "语义上下文聚合引擎异常"
        assert data["data"]["status"] == "unhealthy"
        assert "error" in data["data"]
    
    def test_module_priority_conversion(self, client):
        """测试模块优先级转换"""
        # 这个测试验证API正确转换优先级枚举
        with patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator') as mock_class:
            mock_aggregator = Mock()
            mock_result = AggregationResult(
                enhanced_context="test",
                modules_used=[],
                total_tokens_used=0,
                token_budget_remaining=1000,
                relevance_scores={},
                optimization_summary={}
            )
            mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_result)
            mock_class.return_value = mock_aggregator
            
            request_data = {
                "user_question": "测试",
                "module_priorities": {
                    "data_source": "high",
                    "table_structure": "critical",
                    "table_relation": "low",
                    "dictionary": "medium",
                    "knowledge": "low"
                }
            }
            
            response = client.post("/api/semantic-context/aggregate", json=request_data)
            assert response.status_code == 200
            
            # 验证优先级转换
            call_args = mock_aggregator.aggregate_semantic_context.call_args
            module_priorities = call_args.kwargs["module_priorities"]
            
            assert module_priorities[ModuleType.DATA_SOURCE] == ContextPriority.HIGH
            assert module_priorities[ModuleType.TABLE_STRUCTURE] == ContextPriority.CRITICAL
            assert module_priorities[ModuleType.TABLE_RELATION] == ContextPriority.LOW
            assert module_priorities[ModuleType.DICTIONARY] == ContextPriority.MEDIUM
            assert module_priorities[ModuleType.KNOWLEDGE] == ContextPriority.LOW
    
    def test_token_budget_conversion(self, client):
        """测试Token预算转换"""
        with patch('src.api.semantic_context_aggregator_api.SemanticContextAggregator') as mock_class:
            mock_aggregator = Mock()
            mock_result = AggregationResult(
                enhanced_context="test",
                modules_used=[],
                total_tokens_used=0,
                token_budget_remaining=1000,
                relevance_scores={},
                optimization_summary={}
            )
            mock_aggregator.aggregate_semantic_context = AsyncMock(return_value=mock_result)
            mock_class.return_value = mock_aggregator
            
            request_data = {
                "user_question": "测试",
                "token_budget": {
                    "total_budget": 3000,
                    "reserved_for_response": 800
                }
            }
            
            response = client.post("/api/semantic-context/aggregate", json=request_data)
            assert response.status_code == 200
            
            # 验证Token预算转换
            call_args = mock_aggregator.aggregate_semantic_context.call_args
            token_budget = call_args.kwargs["token_budget"]
            
            assert isinstance(token_budget, TokenBudget)
            assert token_budget.total_budget == 3000
            assert token_budget.reserved_for_response == 800
            assert token_budget.available_for_context == 2200
    
    def test_request_validation(self, client):
        """测试请求参数验证"""
        # 测试用户问题长度限制
        request_data = {
            "user_question": "x" * 1001  # 超过1000字符限制
        }
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        assert response.status_code == 422
        
        # 测试Token预算范围限制
        request_data = {
            "user_question": "测试",
            "token_budget": {
                "total_budget": 500,  # 小于最小值1000
                "reserved_for_response": 1000
            }
        }
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        assert response.status_code == 422
        
        # 测试Token预算上限
        request_data = {
            "user_question": "测试",
            "token_budget": {
                "total_budget": 15000,  # 超过最大值10000
                "reserved_for_response": 1000
            }
        }
        
        response = client.post("/api/semantic-context/aggregate", json=request_data)
        assert response.status_code == 422