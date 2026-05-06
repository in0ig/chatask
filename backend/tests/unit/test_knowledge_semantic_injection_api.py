"""
知识库语义注入API测试

测试知识库语义注入API的所有端点，包括语义注入、知识查询、批量处理、
搜索、缓存管理和健康检查等功能。
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.main import app
from src.services.knowledge_semantic_injection import (
    KnowledgeSemanticInjectionService,
    SemanticInjectionResult,
    KnowledgeSemanticInfo,
    TermKnowledge,
    LogicKnowledge,
    EventKnowledge
)


class TestKnowledgeSemanticInjectionAPI:
    """知识库语义注入API测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_injection_result(self):
        """示例语义注入结果"""
        terms = [TermKnowledge(
            id="term_001",
            name="客户",
            explanation="购买产品的个人或企业",
            example_question="有多少客户？",
            scope="GLOBAL",
            table_id=None,
            relevance_score=2.0
        )]
        
        logics = [LogicKnowledge(
            id="logic_001",
            explanation="VIP客户消费超过10000元",
            example_question="哪些是VIP客户？",
            scope="TABLE",
            table_id="table_001",
            relevance_score=1.5
        )]
        
        events = [EventKnowledge(
            id="event_001",
            explanation="双十一促销活动",
            event_date_start=datetime(2024, 11, 11),
            event_date_end=datetime(2024, 11, 11, 23, 59, 59),
            scope="GLOBAL",
            table_id=None,
            relevance_score=1.0,
            is_active=False
        )]
        
        knowledge_info = KnowledgeSemanticInfo(
            terms=terms,
            logics=logics,
            events=events,
            total_relevance_score=4.5
        )
        
        return SemanticInjectionResult(
            enhanced_context="用户问题: 查询客户数据\n业务术语:\n- 客户: 购买产品的个人或企业",
            knowledge_info=knowledge_info,
            injection_summary={
                "total_knowledge_items": 3,
                "terms_count": 1,
                "logics_count": 1,
                "events_count": 1,
                "active_events_count": 0,
                "total_relevance_score": 4.5,
                "average_relevance_score": 1.5
            }
        )
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_inject_knowledge_semantics_success(self, mock_service_class, client, sample_injection_result):
        """测试知识库语义注入成功"""
        # 模拟服务
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.return_value = sample_injection_result
        mock_service_class.return_value = mock_service
        
        # 请求数据
        request_data = {
            "user_question": "查询客户购买记录",
            "table_ids": ["table_001"],
            "include_global": True,
            "max_terms": 10,
            "max_logics": 5,
            "max_events": 3
        }
        
        # 发送请求
        response = client.post("/api/knowledge-semantic/inject", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "知识库语义注入成功" in data["message"]
        
        # 验证响应数据结构
        response_data = data["data"]
        assert "enhanced_context" in response_data
        assert "knowledge_info" in response_data
        assert "injection_summary" in response_data
        
        # 验证知识信息
        knowledge_info = response_data["knowledge_info"]
        assert len(knowledge_info["terms"]) == 1
        assert len(knowledge_info["logics"]) == 1
        assert len(knowledge_info["events"]) == 1
        assert knowledge_info["total_relevance_score"] == 4.5
        
        # 验证术语信息
        term = knowledge_info["terms"][0]
        assert term["id"] == "term_001"
        assert term["name"] == "客户"
        assert term["explanation"] == "购买产品的个人或企业"
        assert term["scope"] == "GLOBAL"
        assert term["relevance_score"] == 2.0
        
        # 验证逻辑信息
        logic = knowledge_info["logics"][0]
        assert logic["id"] == "logic_001"
        assert logic["explanation"] == "VIP客户消费超过10000元"
        assert logic["scope"] == "TABLE"
        assert logic["table_id"] == "table_001"
        assert logic["relevance_score"] == 1.5
        
        # 验证事件信息
        event = knowledge_info["events"][0]
        assert event["id"] == "event_001"
        assert event["explanation"] == "双十一促销活动"
        assert event["scope"] == "GLOBAL"
        assert event["is_active"] is False
        assert event["relevance_score"] == 1.0
        
        # 验证服务调用
        mock_service.inject_knowledge_semantics.assert_called_once_with(
            user_question="查询客户购买记录",
            table_ids=["table_001"],
            include_global=True,
            max_terms=10,
            max_logics=5,
            max_events=3
        )
    
    def test_inject_knowledge_semantics_missing_question(self, client):
        """测试知识库语义注入缺少问题参数"""
        request_data = {
            "table_ids": ["table_001"],
            "include_global": True
        }
        
        response = client.post("/api/knowledge-semantic/inject", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_inject_knowledge_semantics_invalid_parameters(self, client):
        """测试知识库语义注入无效参数"""
        request_data = {
            "user_question": "查询数据",
            "max_terms": 0,  # 无效值，应该 >= 1
            "max_logics": 25,  # 无效值，应该 <= 20
            "max_events": -1  # 无效值，应该 >= 1
        }
        
        response = client.post("/api/knowledge-semantic/inject", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_inject_knowledge_semantics_service_error(self, mock_service_class, client):
        """测试知识库语义注入服务错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        request_data = {
            "user_question": "查询数据"
        }
        
        response = client.post("/api/knowledge-semantic/inject", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "知识库语义注入失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_get_knowledge_by_table_success(self, mock_service_class, client):
        """测试获取表级知识成功"""
        # 模拟服务
        mock_service = Mock()
        knowledge_info = KnowledgeSemanticInfo(
            terms=[TermKnowledge(id="1", name="术语", explanation="解释", relevance_score=1.0)],
            logics=[],
            events=[],
            total_relevance_score=1.0
        )
        mock_service.get_knowledge_by_table.return_value = knowledge_info
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/table/table_001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "获取表级知识成功" in data["message"]
        
        # 验证知识信息
        knowledge_data = data["data"]
        assert len(knowledge_data["terms"]) == 1
        assert len(knowledge_data["logics"]) == 0
        assert len(knowledge_data["events"]) == 0
        assert knowledge_data["total_relevance_score"] == 1.0
        
        # 验证服务调用
        mock_service.get_knowledge_by_table.assert_called_once_with("table_001")
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_get_knowledge_by_table_error(self, mock_service_class, client):
        """测试获取表级知识错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.get_knowledge_by_table.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/table/table_001")
        
        assert response.status_code == 500
        data = response.json()
        assert "获取表级知识失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_get_global_knowledge_success(self, mock_service_class, client):
        """测试获取全局知识成功"""
        # 模拟服务
        mock_service = Mock()
        knowledge_info = KnowledgeSemanticInfo(
            terms=[],
            logics=[LogicKnowledge(id="1", explanation="逻辑", relevance_score=1.5)],
            events=[],
            total_relevance_score=1.5
        )
        mock_service.get_global_knowledge.return_value = knowledge_info
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/global")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "获取全局知识成功" in data["message"]
        
        # 验证知识信息
        knowledge_data = data["data"]
        assert len(knowledge_data["terms"]) == 0
        assert len(knowledge_data["logics"]) == 1
        assert len(knowledge_data["events"]) == 0
        assert knowledge_data["total_relevance_score"] == 1.5
        
        # 验证服务调用
        mock_service.get_global_knowledge.assert_called_once()
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_get_global_knowledge_error(self, mock_service_class, client):
        """测试获取全局知识错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.get_global_knowledge.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/global")
        
        assert response.status_code == 500
        data = response.json()
        assert "获取全局知识失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_batch_inject_knowledge_semantics_success(self, mock_service_class, client, sample_injection_result):
        """测试批量知识库语义注入成功"""
        # 模拟服务
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.return_value = sample_injection_result
        mock_service_class.return_value = mock_service
        
        # 请求数据
        request_data = [
            {
                "user_question": "查询客户数据",
                "include_global": True
            },
            {
                "user_question": "分析销售趋势",
                "table_ids": ["sales_table"],
                "max_terms": 5
            }
        ]
        
        response = client.post("/api/knowledge-semantic/batch-inject", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "批量知识库语义注入成功" in data["message"]
        
        # 验证返回了两个结果
        results = data["data"]
        assert len(results) == 2
        
        # 验证服务被调用了两次
        assert mock_service.inject_knowledge_semantics.call_count == 2
    
    def test_batch_inject_knowledge_semantics_too_many_requests(self, client):
        """测试批量知识库语义注入请求过多"""
        # 创建超过限制的请求
        request_data = [
            {"user_question": f"问题{i}"} for i in range(11)  # 超过10个限制
        ]
        
        response = client.post("/api/knowledge-semantic/batch-inject", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "批量处理数量不能超过10个" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_batch_inject_knowledge_semantics_service_error(self, mock_service_class, client):
        """测试批量知识库语义注入服务错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        request_data = [{"user_question": "查询数据"}]
        
        response = client.post("/api/knowledge-semantic/batch-inject", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "批量知识库语义注入失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_search_knowledge_success(self, mock_service_class, client, sample_injection_result):
        """测试搜索知识库成功"""
        # 模拟服务
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.return_value = sample_injection_result
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/search?keywords=客户购买&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "搜索知识库成功" in data["message"]
        
        # 验证知识信息
        knowledge_data = data["data"]
        assert "terms" in knowledge_data
        assert "logics" in knowledge_data
        assert "events" in knowledge_data
        assert "total_relevance_score" in knowledge_data
        
        # 验证服务调用
        mock_service.inject_knowledge_semantics.assert_called_once()
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_search_knowledge_with_filters(self, mock_service_class, client, sample_injection_result):
        """测试带过滤条件的搜索知识库"""
        # 模拟服务
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.return_value = sample_injection_result
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/knowledge-semantic/search"
            "?keywords=客户"
            "&knowledge_type=TERM"
            "&scope=GLOBAL"
            "&table_id=table_001"
            "&limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证服务调用参数
        call_args = mock_service.inject_knowledge_semantics.call_args
        assert call_args[1]["user_question"] == "客户"
        assert call_args[1]["table_ids"] == ["table_001"]
        assert call_args[1]["include_global"] is True  # scope不是TABLE时包含全局
        assert call_args[1]["max_terms"] == 5  # 只搜索TERM类型
        assert call_args[1]["max_logics"] == 0
        assert call_args[1]["max_events"] == 0
    
    def test_search_knowledge_missing_keywords(self, client):
        """测试搜索知识库缺少关键词"""
        response = client.get("/api/knowledge-semantic/search")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_knowledge_invalid_limit(self, client):
        """测试搜索知识库无效限制"""
        response = client.get("/api/knowledge-semantic/search?keywords=test&limit=0")
        
        assert response.status_code == 422  # Validation error
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_search_knowledge_error(self, mock_service_class, client):
        """测试搜索知识库错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.inject_knowledge_semantics.side_effect = Exception("Search error")
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/search?keywords=test")
        
        assert response.status_code == 500
        data = response.json()
        assert "搜索知识库失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_clear_cache_success(self, mock_service_class, client):
        """测试清空缓存成功"""
        # 模拟服务
        mock_service = Mock()
        mock_service.clear_cache.return_value = None
        mock_service_class.return_value = mock_service
        
        response = client.delete("/api/knowledge-semantic/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "知识库语义注入缓存清空成功" in data["message"]
        assert data["data"]["status"] == "cache_cleared"
        
        # 验证服务调用
        mock_service.clear_cache.assert_called_once()
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_clear_cache_error(self, mock_service_class, client):
        """测试清空缓存错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.clear_cache.side_effect = Exception("Cache error")
        mock_service_class.return_value = mock_service
        
        response = client.delete("/api/knowledge-semantic/cache")
        
        assert response.status_code == 500
        data = response.json()
        assert "清空知识库语义注入缓存失败" in data["detail"]
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_health_check_success(self, mock_service_class, client):
        """测试健康检查成功"""
        # 模拟服务
        mock_service = Mock()
        knowledge_info = KnowledgeSemanticInfo(
            terms=[TermKnowledge(id="1", name="术语", explanation="", relevance_score=1.0)],
            logics=[],
            events=[],
            total_relevance_score=1.0
        )
        mock_service.get_global_knowledge.return_value = knowledge_info
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "知识库语义注入服务健康" in data["message"]
        
        # 验证健康信息
        health_data = data["data"]
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "knowledge_semantic_injection"
        assert health_data["global_knowledge_count"] == 1
        assert health_data["database_connection"] == "ok"
        
        # 验证服务调用
        mock_service.get_global_knowledge.assert_called_once()
    
    @patch('src.api.knowledge_semantic_injection_api.KnowledgeSemanticInjectionService')
    def test_health_check_error(self, mock_service_class, client):
        """测试健康检查错误"""
        # 模拟服务错误
        mock_service = Mock()
        mock_service.get_global_knowledge.side_effect = Exception("Health check failed")
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/knowledge-semantic/health")
        
        assert response.status_code == 500
        data = response.json()
        assert "健康检查失败" in data["detail"]
    
    def test_api_endpoints_exist(self, client):
        """测试API端点存在性"""
        # 测试所有端点都能响应（即使可能返回错误）
        endpoints = [
            ("/api/knowledge-semantic/inject", "POST"),
            ("/api/knowledge-semantic/table/test", "GET"),
            ("/api/knowledge-semantic/global", "GET"),
            ("/api/knowledge-semantic/batch-inject", "POST"),
            ("/api/knowledge-semantic/search?keywords=test", "GET"),
            ("/api/knowledge-semantic/cache", "DELETE"),
            ("/api/knowledge-semantic/health", "GET")
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            # 端点应该存在（不是404）
            assert response.status_code != 404, f"Endpoint {method} {endpoint} not found"