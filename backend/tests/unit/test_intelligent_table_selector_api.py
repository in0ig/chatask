"""
智能表选择算法 API 单元测试

任务 5.2.3 的API测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
from datetime import datetime

from src.api.intelligent_table_selector_api import router
from src.services.intelligent_table_selector import (
    TableSelectionResult,
    TableCandidate,
    TableSelectionConfidence
)


# 创建测试应用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestIntelligentTableSelectorAPI:
    """智能表选择API测试类"""
    
    @pytest.fixture
    def mock_table_selector_service(self):
        """Mock表选择服务"""
        with patch('src.api.intelligent_table_selector_api.table_selector_service') as mock_service:
            yield mock_service
    
    @pytest.fixture
    def sample_table_candidate(self):
        """示例表候选对象"""
        return TableCandidate(
            table_id="tbl_001",
            table_name="products",
            table_comment="产品信息表",
            relevance_score=0.95,
            confidence=TableSelectionConfidence.HIGH,
            selection_reasons=["包含产品相关字段", "与销售查询高度相关"],
            matched_keywords=["产品", "销售"],
            business_meaning="存储产品基本信息和属性",
            relation_paths=[
                {
                    "target_table": "sales",
                    "join_type": "INNER",
                    "join_condition": "products.id = sales.product_id",
                    "confidence": 0.9
                }
            ],
            semantic_context={"data_source_type": "mysql"}
        )
    
    @pytest.fixture
    def sample_selection_result(self, sample_table_candidate):
        """示例表选择结果"""
        related_table = TableCandidate(
            table_id="tbl_002",
            table_name="sales",
            table_comment="销售记录表",
            relevance_score=0.85,
            confidence=TableSelectionConfidence.HIGH,
            selection_reasons=["包含销售金额字段"],
            matched_keywords=["销售", "金额"],
            business_meaning="存储销售交易记录",
            relation_paths=[],
            semantic_context={"data_source_type": "mysql"}
        )
        
        return TableSelectionResult(
            primary_tables=[sample_table_candidate],
            related_tables=[related_table],
            selection_strategy="ai_based",
            total_relevance_score=1.8,
            recommended_joins=[
                {
                    "left_table": "products",
                    "right_table": "sales",
                    "join_type": "INNER",
                    "join_condition": "products.id = sales.product_id",
                    "confidence": 0.9,
                    "reasoning": "基于外键关系推荐的内连接"
                }
            ],
            selection_explanation="基于用户问题选择了产品表作为主表，销售表作为关联表",
            processing_time=1.23,
            ai_reasoning="用户询问产品销售额，需要产品表获取产品信息，销售表获取销售数据"
        )
    
    def test_select_tables_success(self, mock_table_selector_service, sample_selection_result):
        """测试成功的表选择API"""
        # 设置Mock返回值
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        # 准备请求数据
        request_data = {
            "user_question": "查询销售额最高的产品",
            "data_source_id": "ds_001",
            "context": {
                "session_id": "session_123",
                "previous_tables": ["products", "sales"]
            }
        }
        
        # 发送请求
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["primary_tables"]) == 1
        assert len(data["related_tables"]) == 1
        assert data["primary_tables"][0]["table_name"] == "products"
        assert data["related_tables"][0]["table_name"] == "sales"
        assert data["selection_strategy"] == "ai_based"
        assert data["total_relevance_score"] == 1.8
        assert len(data["recommended_joins"]) == 1
        assert data["processing_time"] == 1.23
        
        # 验证服务调用
        mock_table_selector_service.select_tables.assert_called_once_with(
            user_question="查询销售额最高的产品",
            data_source_id="ds_001",
            context={
                "session_id": "session_123",
                "previous_tables": ["products", "sales"]
            }
        )
    
    def test_select_tables_minimal_request(self, mock_table_selector_service, sample_selection_result):
        """测试最小请求参数的表选择API"""
        # 设置Mock返回值
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        # 准备最小请求数据
        request_data = {
            "user_question": "查询销售额最高的产品"
        }
        
        # 发送请求
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert "primary_tables" in data
        assert "related_tables" in data
        assert "selection_strategy" in data
        
        # 验证服务调用
        mock_table_selector_service.select_tables.assert_called_once_with(
            user_question="查询销售额最高的产品",
            data_source_id=None,
            context=None
        )
    
    def test_select_tables_invalid_request(self):
        """测试无效请求参数"""
        # 空的用户问题
        request_data = {
            "user_question": ""
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 422  # 验证错误
        
        # 缺少必需字段
        request_data = {}
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 422  # 验证错误
        
        # 用户问题过长
        request_data = {
            "user_question": "x" * 1001  # 超过最大长度
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 422  # 验证错误
    
    def test_select_tables_service_error(self, mock_table_selector_service):
        """测试服务层错误处理"""
        # 设置Mock抛出异常
        mock_table_selector_service.select_tables = AsyncMock(side_effect=Exception("服务不可用"))
        
        # 准备请求数据
        request_data = {
            "user_question": "查询销售额最高的产品"
        }
        
        # 发送请求
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        
        # 验证错误响应
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "服务不可用" in data["detail"]
    
    def test_batch_select_tables_success(self, mock_table_selector_service, sample_selection_result):
        """测试成功的批量表选择API"""
        # 设置Mock返回值
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        # 准备批量请求数据
        request_data = {
            "requests": [
                {
                    "user_question": "查询销售额最高的产品",
                    "data_source_id": "ds_001"
                },
                {
                    "user_question": "分析客户购买行为",
                    "data_source_id": "ds_001"
                }
            ]
        }
        
        # 发送请求
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 2
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert data["total_processing_time"] > 0
        
        # 验证每个结果
        for result in data["results"]:
            assert "primary_tables" in result
            assert "related_tables" in result
            assert "selection_strategy" in result
        
        # 验证服务调用次数
        assert mock_table_selector_service.select_tables.call_count == 2
    
    def test_batch_select_tables_partial_failure(self, mock_table_selector_service, sample_selection_result):
        """测试批量表选择部分失败"""
        # 设置Mock：第一个成功，第二个失败
        mock_table_selector_service.select_tables = AsyncMock(
            side_effect=[sample_selection_result, Exception("第二个请求失败")]
        )
        
        # 准备批量请求数据
        request_data = {
            "requests": [
                {
                    "user_question": "查询销售额最高的产品",
                    "data_source_id": "ds_001"
                },
                {
                    "user_question": "分析客户购买行为",
                    "data_source_id": "ds_001"
                }
            ]
        }
        
        # 发送请求
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) == 2
        assert data["success_count"] == 1
        assert data["error_count"] == 1
        
        # 验证成功结果
        assert data["results"][0]["selection_strategy"] == "ai_based"
        
        # 验证失败结果
        assert data["results"][1]["selection_strategy"] == "error"
        assert "第二个请求失败" in data["results"][1]["selection_explanation"]
    
    def test_batch_select_tables_invalid_request(self):
        """测试无效的批量请求"""
        # 空请求列表
        request_data = {
            "requests": []
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 422  # 验证错误
        
        # 请求数量过多
        request_data = {
            "requests": [{"user_question": f"问题{i}"} for i in range(11)]  # 超过最大数量
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 422  # 验证错误
    
    def test_get_selection_statistics_success(self, mock_table_selector_service):
        """测试获取选择统计成功"""
        # 设置Mock返回值
        mock_stats = {
            "total_selections": 100,
            "successful_selections": 95,
            "success_rate": 0.95,
            "average_processing_time": 1.5,
            "average_relevance_score": 0.85,
            "configuration": {
                "max_primary_tables": 3,
                "max_related_tables": 5,
                "min_relevance_threshold": 0.3,
                "confidence_thresholds": {
                    "high": 0.8,
                    "medium": 0.5,
                    "low": 0.3
                }
            }
        }
        mock_table_selector_service.get_selection_statistics = Mock(return_value=mock_stats)
        
        # 发送请求
        response = client.get("/api/intelligent-table-selector/statistics")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_selections"] == 100
        assert data["successful_selections"] == 95
        assert data["success_rate"] == 0.95
        assert data["average_processing_time"] == 1.5
        assert data["average_relevance_score"] == 0.85
        assert "configuration" in data
        assert data["configuration"]["max_primary_tables"] == 3
    
    def test_get_selection_statistics_service_error(self, mock_table_selector_service):
        """测试获取统计信息服务错误"""
        # 设置Mock抛出异常
        mock_table_selector_service.get_selection_statistics = Mock(side_effect=Exception("统计服务不可用"))
        
        # 发送请求
        response = client.get("/api/intelligent-table-selector/statistics")
        
        # 验证错误响应
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "统计服务不可用" in data["detail"]
    
    def test_health_check_success(self, mock_table_selector_service):
        """测试健康检查成功"""
        # 设置Mock返回值
        mock_stats = {
            "total_selections": 50,
            "success_rate": 0.96,
            "average_processing_time": 1.2
        }
        mock_table_selector_service.get_selection_statistics = Mock(return_value=mock_stats)
        
        # 发送请求
        response = client.get("/api/intelligent-table-selector/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "intelligent_table_selector"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "statistics" in data
        assert "dependencies" in data
        
        # 验证统计信息
        assert data["statistics"]["total_selections"] == 50
        assert data["statistics"]["success_rate"] == 0.96
        assert data["statistics"]["average_processing_time"] == 1.2
        
        # 验证依赖状态
        dependencies = data["dependencies"]
        assert dependencies["ai_service"] == "available"
        assert dependencies["semantic_aggregator"] == "available"
        assert dependencies["similarity_engine"] == "available"
        assert dependencies["data_integration"] == "available"
        assert dependencies["relation_module"] == "available"
    
    def test_health_check_service_error(self, mock_table_selector_service):
        """测试健康检查服务错误"""
        # 设置Mock抛出异常
        mock_table_selector_service.get_selection_statistics = Mock(side_effect=Exception("健康检查失败"))
        
        # 发送请求
        response = client.get("/api/intelligent-table-selector/health")
        
        # 验证响应（健康检查不应该返回500，而是返回不健康状态）
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["service"] == "intelligent_table_selector"
        assert "error" in data
        assert "健康检查失败" in data["error"]
        assert "timestamp" in data
    
    def test_convert_table_candidate_to_response(self, sample_table_candidate):
        """测试表候选对象转换为响应模型"""
        from src.api.intelligent_table_selector_api import convert_table_candidate_to_response
        
        # 执行转换
        response = convert_table_candidate_to_response(sample_table_candidate)
        
        # 验证转换结果
        assert response.table_id == "tbl_001"
        assert response.table_name == "products"
        assert response.table_comment == "产品信息表"
        assert response.relevance_score == 0.95
        assert response.confidence == "high"
        assert len(response.selection_reasons) == 2
        assert len(response.matched_keywords) == 2
        assert response.business_meaning == "存储产品基本信息和属性"
        assert len(response.relation_paths) == 1
    
    def test_convert_selection_result_to_response(self, sample_selection_result):
        """测试选择结果转换为响应模型"""
        from src.api.intelligent_table_selector_api import convert_selection_result_to_response
        
        # 执行转换
        response = convert_selection_result_to_response(sample_selection_result)
        
        # 验证转换结果
        assert len(response.primary_tables) == 1
        assert len(response.related_tables) == 1
        assert response.selection_strategy == "ai_based"
        assert response.total_relevance_score == 1.8
        assert len(response.recommended_joins) == 1
        assert response.selection_explanation == "基于用户问题选择了产品表作为主表，销售表作为关联表"
        assert response.processing_time == 1.23
        assert response.ai_reasoning == "用户询问产品销售额，需要产品表获取产品信息，销售表获取销售数据"
    
    def test_api_request_response_models(self):
        """测试API请求和响应模型的结构"""
        # 测试请求模型示例
        from src.api.intelligent_table_selector_api import TableSelectionRequest
        
        request_data = {
            "user_question": "查询销售额最高的产品",
            "data_source_id": "ds_001",
            "context": {
                "session_id": "session_123",
                "previous_tables": ["products", "sales"]
            }
        }
        
        request = TableSelectionRequest(**request_data)
        assert request.user_question == "查询销售额最高的产品"
        assert request.data_source_id == "ds_001"
        assert request.context["session_id"] == "session_123"
    
    def test_batch_request_model(self):
        """测试批量请求模型"""
        from src.api.intelligent_table_selector_api import BatchTableSelectionRequest, TableSelectionRequest
        
        request_data = {
            "requests": [
                {
                    "user_question": "查询销售额最高的产品",
                    "data_source_id": "ds_001"
                },
                {
                    "user_question": "分析客户购买行为",
                    "data_source_id": "ds_001"
                }
            ]
        }
        
        batch_request = BatchTableSelectionRequest(**request_data)
        assert len(batch_request.requests) == 2
        assert isinstance(batch_request.requests[0], TableSelectionRequest)
        assert batch_request.requests[0].user_question == "查询销售额最高的产品"
    
    def test_response_model_structure(self, sample_selection_result):
        """测试响应模型结构"""
        from src.api.intelligent_table_selector_api import (
            TableSelectionResponse,
            TableCandidateResponse,
            convert_selection_result_to_response
        )
        
        # 转换为响应模型
        response = convert_selection_result_to_response(sample_selection_result)
        
        # 验证响应模型类型
        assert isinstance(response, TableSelectionResponse)
        assert isinstance(response.primary_tables[0], TableCandidateResponse)
        assert isinstance(response.related_tables[0], TableCandidateResponse)
        
        # 验证字段类型
        assert isinstance(response.primary_tables, list)
        assert isinstance(response.related_tables, list)
        assert isinstance(response.selection_strategy, str)
        assert isinstance(response.total_relevance_score, float)
        assert isinstance(response.recommended_joins, list)
        assert isinstance(response.selection_explanation, str)
        assert isinstance(response.processing_time, float)
        assert isinstance(response.ai_reasoning, str)
    
    def test_statistics_response_model(self):
        """测试统计响应模型"""
        from src.api.intelligent_table_selector_api import SelectionStatisticsResponse
        
        stats_data = {
            "total_selections": 100,
            "successful_selections": 95,
            "success_rate": 0.95,
            "average_processing_time": 1.5,
            "average_relevance_score": 0.85,
            "configuration": {
                "max_primary_tables": 3,
                "max_related_tables": 5,
                "min_relevance_threshold": 0.3
            }
        }
        
        stats_response = SelectionStatisticsResponse(**stats_data)
        assert stats_response.total_selections == 100
        assert stats_response.successful_selections == 95
        assert stats_response.success_rate == 0.95
        assert stats_response.average_processing_time == 1.5
        assert stats_response.average_relevance_score == 0.85
        assert isinstance(stats_response.configuration, dict)
    
    @pytest.mark.asyncio
    async def test_api_endpoint_integration(self, mock_table_selector_service, sample_selection_result):
        """测试API端点集成"""
        # 设置Mock返回值
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        mock_table_selector_service.get_selection_statistics = Mock(return_value={
            "total_selections": 1,
            "successful_selections": 1,
            "success_rate": 1.0,
            "average_processing_time": 1.23,
            "average_relevance_score": 1.8,
            "configuration": {}
        })
        
        # 测试表选择端点
        request_data = {
            "user_question": "查询销售额最高的产品",
            "data_source_id": "ds_001"
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        # 测试统计端点
        response = client.get("/api/intelligent-table-selector/statistics")
        assert response.status_code == 200
        
        # 测试健康检查端点
        response = client.get("/api/intelligent-table-selector/health")
        assert response.status_code == 200
    
    def test_select_tables_with_special_characters(self, mock_table_selector_service, sample_selection_result):
        """测试包含特殊字符的用户问题"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        request_data = {
            "user_question": "查询销售额>10000的产品，按价格排序（降序）"
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        # 验证特殊字符被正确处理
        data = response.json()
        assert "primary_tables" in data
    
    def test_select_tables_with_unicode(self, mock_table_selector_service, sample_selection_result):
        """测试包含Unicode字符的用户问题"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        request_data = {
            "user_question": "查询销售额最高的产品🔥，包含emoji表情"
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "primary_tables" in data
    
    def test_select_tables_with_complex_context(self, mock_table_selector_service, sample_selection_result):
        """测试复杂上下文的表选择"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        request_data = {
            "user_question": "查询销售额最高的产品",
            "data_source_id": "ds_001",
            "context": {
                "session_id": "session_123",
                "previous_tables": ["products", "sales", "customers"],
                "user_preferences": {
                    "preferred_join_type": "LEFT",
                    "max_tables": 5
                },
                "query_history": [
                    {"question": "查询所有产品", "tables": ["products"]},
                    {"question": "查询销售记录", "tables": ["sales"]}
                ]
            }
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "primary_tables" in data
        
        # 验证复杂上下文被正确传递
        call_args = mock_table_selector_service.select_tables.call_args
        assert call_args.kwargs["context"]["session_id"] == "session_123"
        assert len(call_args.kwargs["context"]["previous_tables"]) == 3
    
    def test_select_tables_response_format_validation(self, mock_table_selector_service, sample_selection_result):
        """测试响应格式验证"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        request_data = {
            "user_question": "查询销售额最高的产品"
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证响应格式完整性
        required_fields = [
            "primary_tables", "related_tables", "selection_strategy",
            "total_relevance_score", "recommended_joins", "selection_explanation",
            "processing_time", "ai_reasoning"
        ]
        
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"
        
        # 验证表候选对象格式
        if data["primary_tables"]:
            table = data["primary_tables"][0]
            table_fields = [
                "table_id", "table_name", "table_comment", "relevance_score",
                "confidence", "selection_reasons", "matched_keywords",
                "business_meaning", "relation_paths"
            ]
            for field in table_fields:
                assert field in table, f"表候选对象缺少字段: {field}"
    
    def test_select_tables_data_types_validation(self, mock_table_selector_service, sample_selection_result):
        """测试响应数据类型验证"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        request_data = {
            "user_question": "查询销售额最高的产品"
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证数据类型
        assert isinstance(data["primary_tables"], list)
        assert isinstance(data["related_tables"], list)
        assert isinstance(data["selection_strategy"], str)
        assert isinstance(data["total_relevance_score"], (int, float))
        assert isinstance(data["recommended_joins"], list)
        assert isinstance(data["selection_explanation"], str)
        assert isinstance(data["processing_time"], (int, float))
        assert isinstance(data["ai_reasoning"], str)
        
        # 验证表候选对象数据类型
        if data["primary_tables"]:
            table = data["primary_tables"][0]
            assert isinstance(table["table_id"], str)
            assert isinstance(table["table_name"], str)
            assert isinstance(table["table_comment"], str)
            assert isinstance(table["relevance_score"], (int, float))
            assert isinstance(table["confidence"], str)
            assert isinstance(table["selection_reasons"], list)
            assert isinstance(table["matched_keywords"], list)
            assert isinstance(table["business_meaning"], str)
            assert isinstance(table["relation_paths"], list)
    
    def test_batch_select_tables_empty_results(self, mock_table_selector_service):
        """测试批量选择返回空结果"""
        # 设置Mock返回空结果
        empty_result = TableSelectionResult(
            primary_tables=[],
            related_tables=[],
            selection_strategy="no_match",
            total_relevance_score=0.0,
            recommended_joins=[],
            selection_explanation="未找到相关表",
            processing_time=0.5,
            ai_reasoning="没有匹配的表"
        )
        mock_table_selector_service.select_tables = AsyncMock(return_value=empty_result)
        
        request_data = {
            "requests": [
                {"user_question": "查询不存在的数据"},
                {"user_question": "查询另一个不存在的数据"}
            ]
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 2
        assert data["success_count"] == 2  # 即使结果为空也算成功
        assert data["error_count"] == 0
        
        # 验证空结果格式
        for result in data["results"]:
            assert len(result["primary_tables"]) == 0
            assert len(result["related_tables"]) == 0
            assert result["selection_strategy"] == "no_match"
    
    def test_batch_select_tables_mixed_results(self, mock_table_selector_service, sample_selection_result):
        """测试批量选择混合结果"""
        # 设置Mock：第一个成功，第二个返回空结果
        empty_result = TableSelectionResult(
            primary_tables=[],
            related_tables=[],
            selection_strategy="no_match",
            total_relevance_score=0.0,
            recommended_joins=[],
            selection_explanation="未找到相关表",
            processing_time=0.3,
            ai_reasoning="没有匹配的表"
        )
        
        mock_table_selector_service.select_tables = AsyncMock(
            side_effect=[sample_selection_result, empty_result]
        )
        
        request_data = {
            "requests": [
                {"user_question": "查询销售额最高的产品"},
                {"user_question": "查询不存在的数据"}
            ]
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 2
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        
        # 验证第一个结果有数据
        assert len(data["results"][0]["primary_tables"]) > 0
        
        # 验证第二个结果为空
        assert len(data["results"][1]["primary_tables"]) == 0
    
    def test_batch_select_tables_all_failures(self, mock_table_selector_service):
        """测试批量选择全部失败"""
        mock_table_selector_service.select_tables = AsyncMock(side_effect=Exception("服务不可用"))
        
        request_data = {
            "requests": [
                {"user_question": "查询销售额最高的产品"},
                {"user_question": "分析客户购买行为"}
            ]
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 2
        assert data["success_count"] == 0
        assert data["error_count"] == 2
        
        # 验证所有结果都是错误结果
        for result in data["results"]:
            assert result["selection_strategy"] == "error"
            assert "服务不可用" in result["selection_explanation"]
    
    def test_batch_select_tables_performance(self, mock_table_selector_service, sample_selection_result):
        """测试批量选择性能指标"""
        # 设置Mock：模拟不同的处理时间
        results_with_times = []
        for i in range(3):
            result = TableSelectionResult(
                primary_tables=sample_selection_result.primary_tables,
                related_tables=sample_selection_result.related_tables,
                selection_strategy="ai_based",
                total_relevance_score=sample_selection_result.total_relevance_score,
                recommended_joins=sample_selection_result.recommended_joins,
                selection_explanation=sample_selection_result.selection_explanation,
                processing_time=0.1 + i * 0.05,  # 较小的处理时间
                ai_reasoning=sample_selection_result.ai_reasoning
            )
            results_with_times.append(result)
        
        mock_table_selector_service.select_tables = AsyncMock(side_effect=results_with_times)
        
        request_data = {
            "requests": [
                {"user_question": f"查询问题{i}"} for i in range(3)
            ]
        }
        
        response = client.post("/api/intelligent-table-selector/select/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证性能指标
        assert data["total_processing_time"] > 0
        # 总处理时间应该大于等于最大的单个处理时间，但由于并发可能会更小
        max_individual_time = max(r.processing_time for r in results_with_times)
        assert data["total_processing_time"] >= 0  # 至少大于0
        
        # 验证每个结果的处理时间
        for i, result in enumerate(data["results"]):
            expected_time = 0.1 + i * 0.05
            assert abs(result["processing_time"] - expected_time) < 0.01
    
    def test_statistics_response_completeness(self, mock_table_selector_service):
        """测试统计响应完整性"""
        mock_stats = {
            "total_selections": 150,
            "successful_selections": 142,
            "success_rate": 0.9467,
            "average_processing_time": 1.35,
            "average_relevance_score": 0.78,
            "configuration": {
                "max_primary_tables": 3,
                "max_related_tables": 5,
                "min_relevance_threshold": 0.3,
                "confidence_thresholds": {
                    "high": 0.8,
                    "medium": 0.5,
                    "low": 0.3
                }
            }
        }
        mock_table_selector_service.get_selection_statistics = Mock(return_value=mock_stats)
        
        response = client.get("/api/intelligent-table-selector/statistics")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证所有统计字段
        assert data["total_selections"] == 150
        assert data["successful_selections"] == 142
        assert abs(data["success_rate"] - 0.9467) < 0.0001
        assert abs(data["average_processing_time"] - 1.35) < 0.01
        assert abs(data["average_relevance_score"] - 0.78) < 0.01
        
        # 验证配置信息
        config = data["configuration"]
        assert config["max_primary_tables"] == 3
        assert config["max_related_tables"] == 5
        assert config["min_relevance_threshold"] == 0.3
        
        # 验证置信度阈值
        thresholds = config["confidence_thresholds"]
        assert thresholds["high"] == 0.8
        assert thresholds["medium"] == 0.5
        assert thresholds["low"] == 0.3
    
    def test_statistics_zero_selections(self, mock_table_selector_service):
        """测试零选择次数的统计"""
        mock_stats = {
            "total_selections": 0,
            "successful_selections": 0,
            "success_rate": 0.0,
            "average_processing_time": 0.0,
            "average_relevance_score": 0.0,
            "configuration": {
                "max_primary_tables": 3,
                "max_related_tables": 5,
                "min_relevance_threshold": 0.3,
                "confidence_thresholds": {"high": 0.8, "medium": 0.5, "low": 0.3}
            }
        }
        mock_table_selector_service.get_selection_statistics = Mock(return_value=mock_stats)
        
        response = client.get("/api/intelligent-table-selector/statistics")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证零值处理
        assert data["total_selections"] == 0
        assert data["successful_selections"] == 0
        assert data["success_rate"] == 0.0
        assert data["average_processing_time"] == 0.0
        assert data["average_relevance_score"] == 0.0
    
    def test_health_check_detailed_status(self, mock_table_selector_service):
        """测试健康检查详细状态"""
        mock_stats = {
            "total_selections": 100,
            "success_rate": 0.95,
            "average_processing_time": 1.2
        }
        mock_table_selector_service.get_selection_statistics = Mock(return_value=mock_stats)
        
        response = client.get("/api/intelligent-table-selector/health")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证健康状态详细信息
        assert data["status"] == "healthy"
        assert data["service"] == "intelligent_table_selector"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        
        # 验证统计信息
        stats = data["statistics"]
        assert stats["total_selections"] == 100
        assert stats["success_rate"] == 0.95
        assert stats["average_processing_time"] == 1.2
        
        # 验证依赖状态
        deps = data["dependencies"]
        expected_deps = [
            "ai_service", "semantic_aggregator", "similarity_engine",
            "data_integration", "relation_module"
        ]
        for dep in expected_deps:
            assert dep in deps
            assert deps[dep] == "available"
    
    def test_health_check_timestamp_format(self, mock_table_selector_service):
        """测试健康检查时间戳格式"""
        mock_table_selector_service.get_selection_statistics = Mock(return_value={
            "total_selections": 0,
            "success_rate": 0.0,
            "average_processing_time": 0.0
        })
        
        response = client.get("/api/intelligent-table-selector/health")
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证时间戳格式（ISO 8601）
        timestamp = data["timestamp"]
        assert "T" in timestamp
        # 时间戳应该是有效的ISO格式，不一定需要时区信息
        assert len(timestamp) >= 19  # 至少包含 YYYY-MM-DDTHH:MM:SS
        
        # 尝试解析时间戳
        from datetime import datetime
        try:
            # 移除可能的时区信息进行基本解析测试
            base_timestamp = timestamp.split("+")[0].split("Z")[0]
            if "." in base_timestamp:
                # 包含微秒
                datetime.strptime(base_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                # 不包含微秒
                datetime.strptime(base_timestamp, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pytest.fail(f"时间戳格式无效: {timestamp}")
    
    def test_error_handling_consistency(self, mock_table_selector_service):
        """测试错误处理一致性"""
        # 测试不同类型的服务错误
        error_scenarios = [
            ("连接超时", "Connection timeout"),
            ("服务不可用", "Service unavailable"),
            ("内存不足", "Out of memory"),
            ("权限不足", "Permission denied")
        ]
        
        for error_msg, error_type in error_scenarios:
            mock_table_selector_service.select_tables = AsyncMock(side_effect=Exception(error_msg))
            
            request_data = {"user_question": "测试错误处理"}
            response = client.post("/api/intelligent-table-selector/select", json=request_data)
            
            # 验证错误响应格式一致性
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert error_msg in data["detail"]
    
    def test_concurrent_request_handling(self, mock_table_selector_service, sample_selection_result):
        """测试并发请求处理"""
        import threading
        import time
        
        # 设置Mock：模拟处理延迟
        def slow_select_tables(*args, **kwargs):
            time.sleep(0.1)  # 模拟处理时间
            return sample_selection_result
        
        mock_table_selector_service.select_tables = AsyncMock(side_effect=slow_select_tables)
        
        # 并发发送请求
        responses = []
        threads = []
        
        def send_request():
            request_data = {"user_question": "并发测试请求"}
            response = client.post("/api/intelligent-table-selector/select", json=request_data)
            responses.append(response)
        
        # 创建多个并发线程
        for _ in range(3):
            thread = threading.Thread(target=send_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有请求都成功处理
        assert len(responses) == 3
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "primary_tables" in data
    
    def test_api_documentation_examples(self, mock_table_selector_service, sample_selection_result):
        """测试API文档示例的有效性"""
        mock_table_selector_service.select_tables = AsyncMock(return_value=sample_selection_result)
        
        # 测试请求模型示例
        example_request = {
            "user_question": "查询销售额最高的产品",
            "data_source_id": "ds_001",
            "context": {
                "session_id": "session_123",
                "previous_tables": ["products", "sales"]
            }
        }
        
        response = client.post("/api/intelligent-table-selector/select", json=example_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # 验证响应符合文档示例格式
        assert "primary_tables" in data
        assert "related_tables" in data
        assert "selection_strategy" in data
        assert "total_relevance_score" in data
        assert "recommended_joins" in data
        assert "selection_explanation" in data
        assert "processing_time" in data
        assert "ai_reasoning" in data
        
        # 验证表候选对象格式符合文档
        if data["primary_tables"]:
            table = data["primary_tables"][0]
            expected_fields = [
                "table_id", "table_name", "table_comment", "relevance_score",
                "confidence", "selection_reasons", "matched_keywords",
                "business_meaning", "relation_paths"
            ]
            for field in expected_fields:
                assert field in table