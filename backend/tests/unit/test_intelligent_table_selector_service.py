"""
智能表选择服务单元测试

任务 5.2.3 的服务层测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from src.services.intelligent_table_selector import (
    IntelligentTableSelector,
    TableSelectionResult,
    TableCandidate,
    TableSelectionConfidence
)


class TestIntelligentTableSelector:
    """智能表选择器测试类"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock所有依赖服务"""
        with patch('src.services.intelligent_table_selector.AIModelService') as mock_ai, \
             patch('src.services.intelligent_table_selector.SemanticContextAggregator') as mock_aggregator, \
             patch('src.services.intelligent_table_selector.SemanticSimilarityEngine') as mock_similarity, \
             patch('src.services.intelligent_table_selector.MultiSourceDataIntegrationEngine') as mock_integration, \
             patch('src.services.intelligent_table_selector.TableRelationSemanticInjectionService') as mock_relation:
            
            yield {
                'ai_service': mock_ai.return_value,
                'semantic_aggregator': mock_aggregator.return_value,
                'similarity_engine': mock_similarity.return_value,
                'data_integration': mock_integration.return_value,
                'relation_module': mock_relation.return_value
            }
    
    @pytest.fixture
    def table_selector(self, mock_dependencies):
        """创建表选择器实例"""
        return IntelligentTableSelector()
    
    @pytest.fixture
    def sample_semantic_context(self):
        """示例语义上下文"""
        return {
            "keyword_analysis": {
                "all_keywords": ["产品", "销售", "最高"]
            },
            "modules": {
                "data_source": {
                    "database_type": "mysql",
                    "connection_info": "test_db"
                },
                "table_structure": {
                    "tables": ["products", "sales"]
                },
                "data_dictionary": {
                    "field_mappings": {
                        "product_name": "产品名称",
                        "sales_amount": "销售金额"
                    }
                },
                "knowledge_base": {
                    "business_rules": ["销售额计算规则"]
                }
            },
            "token_usage": 1500
        }
    
    @pytest.fixture
    def sample_candidate_tables(self):
        """示例候选表列表"""
        return [
            {
                "id": "tbl_001",
                "table_name": "products",
                "table_comment": "产品信息表",
                "fields": [
                    {"field_name": "id", "field_type": "int"},
                    {"field_name": "name", "field_type": "varchar"},
                    {"field_name": "price", "field_type": "decimal"}
                ]
            },
            {
                "id": "tbl_002",
                "table_name": "sales",
                "table_comment": "销售记录表",
                "fields": [
                    {"field_name": "id", "field_type": "int"},
                    {"field_name": "product_id", "field_type": "int"},
                    {"field_name": "amount", "field_type": "decimal"}
                ]
            },
            {
                "id": "tbl_003",
                "table_name": "customers",
                "table_comment": "客户信息表",
                "fields": [
                    {"field_name": "id", "field_type": "int"},
                    {"field_name": "name", "field_type": "varchar"}
                ]
            }
        ]
    
    @pytest.fixture
    def sample_ai_response(self):
        """示例AI响应"""
        return json.dumps({
            "primary_tables": [
                {
                    "table_id": "tbl_001",
                    "table_name": "products",
                    "relevance_score": 0.95,
                    "confidence": "high",
                    "selection_reasons": ["包含产品相关字段", "与销售查询高度相关"],
                    "matched_keywords": ["产品", "销售"],
                    "business_meaning": "存储产品基本信息和属性"
                }
            ],
            "related_tables": [
                {
                    "table_id": "tbl_002",
                    "table_name": "sales",
                    "relevance_score": 0.85,
                    "confidence": "high",
                    "selection_reasons": ["包含销售金额字段"],
                    "matched_keywords": ["销售", "金额"],
                    "business_meaning": "存储销售交易记录"
                }
            ],
            "selection_strategy": "ai_based",
            "selection_explanation": "基于用户问题选择了产品表作为主表，销售表作为关联表",
            "ai_reasoning": "用户询问产品销售额，需要产品表获取产品信息，销售表获取销售数据"
        })
    
    @pytest.mark.asyncio
    async def test_select_tables_success(self, table_selector, mock_dependencies, sample_semantic_context, sample_candidate_tables, sample_ai_response):
        """测试成功的表选择"""
        # 设置Mock返回值
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value=sample_ai_response)
        mock_dependencies['relation_module'].inject_table_relation_semantics = Mock(return_value=[])
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品",
            data_source_id="ds_001"
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        assert len(result.primary_tables) == 1
        assert len(result.related_tables) == 1
        assert result.primary_tables[0].table_name == "products"
        assert result.related_tables[0].table_name == "sales"
        assert result.selection_strategy == "ai_based"
        assert result.total_relevance_score > 0
        assert result.processing_time > 0
        
        # 验证服务调用
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context.assert_called_once()
        mock_dependencies['data_integration'].get_integrated_metadata.assert_called_once()
        mock_dependencies['ai_service'].generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_select_tables_with_context(self, table_selector, mock_dependencies, sample_semantic_context, sample_candidate_tables, sample_ai_response):
        """测试带上下文的表选择"""
        # 设置Mock返回值
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value=sample_ai_response)
        mock_dependencies['relation_module'].inject_table_relation_semantics = Mock(return_value=[])
        
        # 执行测试
        context = {"session_id": "test_session", "previous_tables": ["products"]}
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品",
            data_source_id="ds_001",
            context=context
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        assert len(result.primary_tables) == 1
        assert result.primary_tables[0].table_name == "products"
        
        # 验证上下文传递
        call_args = mock_dependencies['semantic_aggregator'].aggregate_semantic_context.call_args[0][0]
        assert call_args["context"] == context
    
    @pytest.mark.asyncio
    async def test_select_tables_no_data_source(self, table_selector, mock_dependencies, sample_semantic_context, sample_candidate_tables, sample_ai_response):
        """测试不指定数据源的表选择"""
        # 设置Mock返回值
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value=sample_ai_response)
        mock_dependencies['relation_module'].inject_table_relation_semantics = Mock(return_value=[])
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "ai_based"
        
        # 验证数据源ID为None的调用
        call_args = mock_dependencies['data_integration'].get_integrated_metadata.call_args
        assert call_args.kwargs["data_source_id"] is None
    
    @pytest.mark.asyncio
    async def test_select_tables_semantic_context_error(self, table_selector, mock_dependencies, sample_candidate_tables, sample_ai_response):
        """测试语义上下文获取失败"""
        # 设置Mock：语义上下文获取失败
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(side_effect=Exception("语义上下文服务不可用"))
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value=sample_ai_response)
        mock_dependencies['relation_module'].inject_table_relation_semantics = Mock(return_value=[])
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果：应该使用默认上下文继续处理
        assert isinstance(result, TableSelectionResult)
        # 由于语义上下文失败，可能会影响结果质量，但不应该完全失败
    
    @pytest.mark.asyncio
    async def test_select_tables_candidate_tables_error(self, table_selector, mock_dependencies, sample_semantic_context):
        """测试候选表获取失败"""
        # 设置Mock：候选表获取失败
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(side_effect=Exception("数据整合服务不可用"))
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果：当候选表获取失败时，会触发AI服务失败，然后降级到相似度选择
        assert isinstance(result, TableSelectionResult)
        assert len(result.primary_tables) == 0
        assert len(result.related_tables) == 0
        # 实际上会降级到相似度选择，但由于候选表为空，结果也为空
        assert result.selection_strategy in ["similarity_fallback", "error_fallback"]
    
    @pytest.mark.asyncio
    async def test_select_tables_ai_service_error(self, table_selector, mock_dependencies, sample_semantic_context, sample_candidate_tables):
        """测试AI服务失败时的降级策略"""
        # 设置Mock：AI服务失败，触发降级策略
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(side_effect=Exception("AI服务不可用"))
        
        # 设置相似度引擎Mock
        mock_keyword_analysis = Mock()
        mock_keyword_analysis.all_keywords = ["产品", "销售"]
        mock_dependencies['similarity_engine'].analyze_user_question = Mock(return_value=mock_keyword_analysis)
        
        mock_similarity_match = Mock()
        mock_similarity_match.similarity_score = 0.8
        mock_similarity_match.match_reasons = ["包含产品关键词"]
        mock_similarity_match.matched_keywords = ["产品"]
        mock_similarity_match.business_meaning = "产品信息表"
        mock_dependencies['similarity_engine'].calculate_table_similarity = Mock(return_value=mock_similarity_match)
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果：应该使用相似度降级策略
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "similarity_fallback"
        assert len(result.primary_tables) > 0  # 应该有降级结果
    
    @pytest.mark.asyncio
    async def test_select_tables_invalid_ai_response(self, table_selector, mock_dependencies, sample_semantic_context, sample_candidate_tables):
        """测试AI响应格式无效"""
        # 设置Mock：AI返回无效JSON
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": sample_candidate_tables})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value="这不是有效的JSON响应")
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果：应该尝试从文本中提取表名
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "text_extraction"
    
    @pytest.mark.asyncio
    async def test_select_tables_empty_candidate_tables(self, table_selector, mock_dependencies, sample_semantic_context, sample_ai_response):
        """测试候选表为空的情况"""
        # 设置Mock：候选表为空
        mock_dependencies['semantic_aggregator'].aggregate_semantic_context = AsyncMock(return_value=sample_semantic_context)
        mock_dependencies['data_integration'].get_integrated_metadata = AsyncMock(return_value={"tables": []})
        mock_dependencies['ai_service'].generate_response = AsyncMock(return_value=sample_ai_response)
        
        # 执行测试
        result = await table_selector.select_tables(
            user_question="查询销售额最高的产品"
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        # 即使候选表为空，也应该返回结果（可能为空）
    
    def test_determine_confidence_high(self, table_selector):
        """测试高置信度判断"""
        confidence = table_selector._determine_confidence(0.9)
        assert confidence == TableSelectionConfidence.HIGH
    
    def test_determine_confidence_medium(self, table_selector):
        """测试中等置信度判断"""
        confidence = table_selector._determine_confidence(0.6)
        assert confidence == TableSelectionConfidence.MEDIUM
    
    def test_determine_confidence_low(self, table_selector):
        """测试低置信度判断"""
        confidence = table_selector._determine_confidence(0.2)
        assert confidence == TableSelectionConfidence.LOW
    
    def test_build_table_selection_prompt(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试构建表选择Prompt"""
        user_question = "查询销售额最高的产品"
        
        prompt = table_selector._build_table_selection_prompt(
            user_question, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证Prompt内容
        assert user_question in prompt
        assert "products" in prompt
        assert "sales" in prompt
        assert "JSON" in prompt
        assert "primary_tables" in prompt
        assert "related_tables" in prompt
    
    def test_build_table_candidate_success(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试成功构建表候选对象"""
        table_data = {
            "table_id": "tbl_001",
            "table_name": "products",
            "relevance_score": 0.95,
            "selection_reasons": ["包含产品相关字段"],
            "matched_keywords": ["产品"],
            "business_meaning": "产品信息表"
        }
        
        candidate = table_selector._build_table_candidate(
            table_data, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证候选对象
        assert candidate is not None
        assert candidate.table_id == "tbl_001"
        assert candidate.table_name == "products"
        assert candidate.relevance_score == 0.95
        assert candidate.confidence == TableSelectionConfidence.HIGH
    
    def test_build_table_candidate_not_found(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试构建不存在的表候选对象"""
        table_data = {
            "table_id": "tbl_999",
            "table_name": "nonexistent_table",
            "relevance_score": 0.95
        }
        
        candidate = table_selector._build_table_candidate(
            table_data, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果：应该返回None
        assert candidate is None
    
    def test_build_table_candidate_invalid_score(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试构建表候选对象时评分无效"""
        table_data = {
            "table_id": "tbl_001",
            "table_name": "products",
            "relevance_score": "invalid_score"  # 无效评分
        }
        
        candidate = table_selector._build_table_candidate(
            table_data, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果：应该处理异常并返回None
        assert candidate is None
    
    def test_parse_ai_selection_response_success(self, table_selector, sample_candidate_tables, sample_semantic_context, sample_ai_response):
        """测试成功解析AI选择响应"""
        result = table_selector._parse_ai_selection_response(
            sample_ai_response, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证解析结果
        assert isinstance(result, TableSelectionResult)
        assert len(result.primary_tables) == 1
        assert len(result.related_tables) == 1
        assert result.selection_strategy == "ai_based"
        assert result.total_relevance_score > 0
    
    def test_parse_ai_selection_response_invalid_json(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试解析无效JSON响应"""
        invalid_response = "这不是有效的JSON"
        
        result = table_selector._parse_ai_selection_response(
            invalid_response, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果：应该降级到文本提取
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "text_extraction"
    
    def test_extract_tables_from_text(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试从文本中提取表名"""
        ai_response = "我建议使用products表和sales表来查询销售数据"
        
        result = table_selector._extract_tables_from_text(
            ai_response, sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "text_extraction"
        assert len(result.primary_tables) > 0
        # 验证提取到的表名
        table_names = [t.table_name for t in result.primary_tables]
        assert "products" in table_names or "sales" in table_names
    
    def test_update_selection_stats_success(self, table_selector, sample_candidate_tables, sample_semantic_context):
        """测试更新选择统计信息"""
        # 创建测试结果
        result = TableSelectionResult(
            primary_tables=[
                TableCandidate(
                    table_id="tbl_001",
                    table_name="products",
                    table_comment="产品表",
                    relevance_score=0.9,
                    confidence=TableSelectionConfidence.HIGH,
                    selection_reasons=[],
                    matched_keywords=[],
                    business_meaning="",
                    relation_paths=[],
                    semantic_context={}
                )
            ],
            related_tables=[],
            selection_strategy="ai_based",
            total_relevance_score=0.9,
            recommended_joins=[],
            selection_explanation="",
            processing_time=1.5,
            ai_reasoning=""
        )
        
        # 更新统计
        table_selector._update_selection_stats(result, 1.5)
        
        # 验证统计更新
        stats = table_selector.get_selection_statistics()
        assert stats["total_selections"] == 1
        assert stats["successful_selections"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["average_processing_time"] == 1.5
        assert stats["average_relevance_score"] == 0.9
    
    def test_update_selection_stats_failed(self, table_selector):
        """测试更新失败选择的统计信息"""
        # 创建失败结果
        result = TableSelectionResult(
            primary_tables=[],
            related_tables=[],
            selection_strategy="error",
            total_relevance_score=0.0,
            recommended_joins=[],
            selection_explanation="选择失败",
            processing_time=0.5,
            ai_reasoning=""
        )
        
        # 更新统计
        table_selector._update_selection_stats(result, 0.5)
        
        # 验证统计更新
        stats = table_selector.get_selection_statistics()
        assert stats["total_selections"] == 1
        assert stats["successful_selections"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_processing_time"] == 0.5
        assert stats["average_relevance_score"] == 0.0
    
    def test_get_selection_statistics(self, table_selector):
        """测试获取选择统计"""
        # 执行测试
        stats = table_selector.get_selection_statistics()
        
        # 验证统计结构
        assert "total_selections" in stats
        assert "successful_selections" in stats
        assert "success_rate" in stats
        assert "average_processing_time" in stats
        assert "average_relevance_score" in stats
        assert "configuration" in stats
        
        # 验证配置信息
        config = stats["configuration"]
        assert "max_primary_tables" in config
        assert "max_related_tables" in config
        assert "min_relevance_threshold" in config
        assert "confidence_thresholds" in config
    
    def test_get_selection_statistics_initial_state(self, table_selector):
        """测试初始状态的统计信息"""
        stats = table_selector.get_selection_statistics()
        
        # 验证初始值
        assert stats["total_selections"] == 0
        assert stats["successful_selections"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["average_processing_time"] == 0.0
        assert stats["average_relevance_score"] == 0.0
    
    def test_configuration_parameters(self, table_selector):
        """测试配置参数"""
        # 验证默认配置
        assert table_selector.max_primary_tables == 3
        assert table_selector.max_related_tables == 5
        assert table_selector.min_relevance_threshold == 0.3
        assert table_selector.confidence_thresholds["high"] == 0.8
        assert table_selector.confidence_thresholds["medium"] == 0.5
        assert table_selector.confidence_thresholds["low"] == 0.3
    
    @pytest.mark.asyncio
    async def test_fallback_similarity_selection_success(self, table_selector, mock_dependencies, sample_candidate_tables, sample_semantic_context):
        """测试相似度降级选择成功"""
        # 设置相似度引擎Mock
        mock_keyword_analysis = Mock()
        mock_keyword_analysis.all_keywords = ["产品", "销售"]
        mock_dependencies['similarity_engine'].analyze_user_question = Mock(return_value=mock_keyword_analysis)
        
        mock_similarity_match = Mock()
        mock_similarity_match.similarity_score = 0.8
        mock_similarity_match.match_reasons = ["包含产品关键词"]
        mock_similarity_match.matched_keywords = ["产品"]
        mock_similarity_match.business_meaning = "产品信息表"
        mock_dependencies['similarity_engine'].calculate_table_similarity = Mock(return_value=mock_similarity_match)
        
        # 执行测试
        result = await table_selector._fallback_similarity_selection(
            "查询销售额最高的产品", sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "similarity_fallback"
        assert len(result.primary_tables) > 0
        assert result.primary_tables[0].relevance_score == 0.8
    
    @pytest.mark.asyncio
    async def test_fallback_similarity_selection_low_scores(self, table_selector, mock_dependencies, sample_candidate_tables, sample_semantic_context):
        """测试相似度降级选择低分情况"""
        # 设置相似度引擎Mock：返回低分
        mock_keyword_analysis = Mock()
        mock_keyword_analysis.all_keywords = ["产品"]
        mock_dependencies['similarity_engine'].analyze_user_question = Mock(return_value=mock_keyword_analysis)
        
        mock_similarity_match = Mock()
        mock_similarity_match.similarity_score = 0.1  # 低于阈值
        mock_similarity_match.match_reasons = ["弱相关"]
        mock_similarity_match.matched_keywords = []
        mock_similarity_match.business_meaning = ""
        mock_dependencies['similarity_engine'].calculate_table_similarity = Mock(return_value=mock_similarity_match)
        
        # 执行测试
        result = await table_selector._fallback_similarity_selection(
            "查询不相关的内容", sample_candidate_tables, sample_semantic_context
        )
        
        # 验证结果：应该没有符合阈值的表
        assert isinstance(result, TableSelectionResult)
        assert result.selection_strategy == "similarity_fallback"
        assert len(result.primary_tables) == 0  # 没有符合阈值的主表
        assert len(result.related_tables) == 0  # 没有符合阈值的关联表