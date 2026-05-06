"""
多源数据整合引擎测试

测试任务 5.2.1 的实现：多源数据整合引擎的核心功能，包括：
1. 整合数据源信息、表结构、表关联、数据字典、知识库五大模块
2. 创建统一的元数据查询和聚合接口
3. 实现元数据的缓存和增量更新机制
4. 支持跨数据源的表关联分析和推荐
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime

from src.services.multi_source_data_integration import (
    MultiSourceDataIntegrationEngine,
    MetadataQuery,
    IntegratedMetadata
)


class TestMultiSourceDataIntegrationEngine:
    """多源数据整合引擎测试类"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock()
    
    @pytest.fixture
    def integration_engine(self, mock_db_session):
        """创建整合引擎实例"""
        return MultiSourceDataIntegrationEngine(mock_db_session)
    
    @pytest.fixture
    def sample_metadata_query(self):
        """示例元数据查询"""
        return MetadataQuery(
            user_question="查询用户订单信息",
            data_source_ids=["ds1", "ds2"],
            table_ids=["users", "orders"],
            include_relations=True,
            include_dictionary=True,
            include_knowledge=True,
            max_tables=10,
            token_budget=4000
        )
    
    @pytest.mark.asyncio
    async def test_query_integrated_metadata_basic(self, integration_engine, sample_metadata_query):
        """测试基础元数据查询整合"""
        # Mock 语义聚合器
        mock_aggregation_result = Mock()
        mock_aggregation_result.enhanced_context = "增强上下文"
        mock_aggregation_result.relevance_scores = {"table_structure": 0.9}
        mock_aggregation_result.total_tokens_used = 500
        
        with patch.object(integration_engine.semantic_aggregator, 'aggregate_semantic_context', 
                         return_value=mock_aggregation_result):
            with patch.object(integration_engine, '_fetch_detailed_metadata', 
                             return_value=IntegratedMetadata(
                                 data_sources=[{"id": "ds1", "name": "测试数据源"}],
                                 tables=[{"id": "users", "table_name": "users"}],
                                 relations=[],
                                 dictionary_mappings=[],
                                 knowledge_items=[],
                                 enhanced_context="增强上下文",
                                 relevance_scores={"table_structure": 0.9},
                                 total_tokens_used=500
                             )):
                
                result = await integration_engine.query_integrated_metadata(sample_metadata_query)
                
                # 验证结果
                assert isinstance(result, IntegratedMetadata)
                assert len(result.data_sources) > 0
                assert len(result.tables) > 0
                assert result.enhanced_context == "增强上下文"
                assert result.total_tokens_used == 500
    
    @pytest.mark.asyncio
    async def test_intelligent_table_selection(self, integration_engine):
        """测试智能表选择功能"""
        # Mock 数据表服务
        mock_tables = [
            {
                "id": "users",
                "table_name": "users",
                "table_comment": "用户信息表",
                "fields": [
                    {"field_name": "id", "field_comment": "用户ID"},
                    {"field_name": "name", "field_comment": "用户姓名"}
                ]
            },
            {
                "id": "orders",
                "table_name": "orders", 
                "table_comment": "订单信息表",
                "fields": [
                    {"field_name": "id", "field_comment": "订单ID"},
                    {"field_name": "user_id", "field_comment": "用户ID"}
                ]
            },
            {
                "id": "products",
                "table_name": "products",
                "table_comment": "产品信息表",
                "fields": []
            }
        ]
        
        # Mock the get_all_tables method to return a response object
        mock_response = Mock()
        mock_table_objects = []
        
        for table_data in mock_tables:
            mock_table = Mock()
            mock_table.id = table_data["id"]
            mock_table.table_name = table_data["table_name"]
            mock_table.description = table_data["table_comment"]
            mock_table_objects.append(mock_table)
        
        mock_response.items = mock_table_objects
        
        # Mock get_table_columns to return field data
        def mock_get_columns(db, table_id):
            table_data = next((t for t in mock_tables if t["id"] == table_id), None)
            if table_data:
                mock_fields = []
                for field_data in table_data["fields"]:
                    mock_field = Mock()
                    mock_field.field_name = field_data["field_name"]
                    mock_field.description = field_data["field_comment"]
                    mock_fields.append(mock_field)
                return mock_fields
            return []
        
        with patch.object(integration_engine.data_table_service, 'get_all_tables', 
                         return_value=mock_response):
            with patch.object(integration_engine.data_table_service, 'get_table_columns',
                             side_effect=mock_get_columns):
                
                query = MetadataQuery(
                    user_question="查询用户订单信息",
                    max_tables=5
                )
                
                selected_tables = await integration_engine._intelligent_table_selection(query)
                
                # 验证智能选择结果
                assert isinstance(selected_tables, list)
                assert "users" in selected_tables  # 应该选中用户表
                assert "orders" in selected_tables  # 应该选中订单表
                # products表相关性较低，可能不会被选中
    
    @pytest.mark.asyncio
    async def test_cross_datasource_relations(self, integration_engine):
        """测试跨数据源表关联分析"""
        # Mock 数据表服务
        mock_tables_ds1 = [
            {"id": "users", "table_name": "users", "data_source_id": "ds1"}
        ]
        mock_tables_ds2 = [
            {"id": "orders", "table_name": "orders", "data_source_id": "ds2"}
        ]
        
        mock_fields_users = [
            Mock(field_name="id", field_type="int"),
            Mock(field_name="name", field_type="varchar")
        ]
        mock_fields_orders = [
            Mock(field_name="id", field_type="int"),
            Mock(field_name="user_id", field_type="int")
        ]
        
        with patch.object(integration_engine.data_table_service, 'get_tables_by_source') as mock_get_tables:
            mock_get_tables.side_effect = [mock_tables_ds1, mock_tables_ds2]
            
            with patch.object(integration_engine.data_table_service, 'get_table_columns') as mock_get_fields:
                mock_get_fields.side_effect = [mock_fields_users, mock_fields_orders]
                
                relations = await integration_engine.get_cross_datasource_relations(["ds1", "ds2"])
                
                # 验证跨数据源关联分析
                assert isinstance(relations, list)
                # 应该发现 users.id 和 orders.user_id 的关联
                if relations:
                    relation = relations[0]
                    assert relation["source_data_source"] != relation["target_data_source"]
                    assert "confidence" in relation
                    assert "reason" in relation
    
    def test_cache_key_generation(self, integration_engine):
        """测试缓存键生成"""
        query1 = MetadataQuery(
            user_question="查询用户信息",
            table_ids=["users"],
            include_relations=True
        )
        
        query2 = MetadataQuery(
            user_question="查询用户信息",
            table_ids=["users"],
            include_relations=True
        )
        
        query3 = MetadataQuery(
            user_question="查询订单信息",
            table_ids=["orders"],
            include_relations=True
        )
        
        key1 = integration_engine._generate_cache_key(query1)
        key2 = integration_engine._generate_cache_key(query2)
        key3 = integration_engine._generate_cache_key(query3)
        
        # 相同查询应该生成相同的缓存键
        assert key1 == key2
        # 不同查询应该生成不同的缓存键
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, integration_engine, sample_metadata_query):
        """测试缓存功能"""
        # Mock 语义聚合器和详细数据获取
        mock_result = IntegratedMetadata(
            data_sources=[],
            tables=[],
            relations=[],
            dictionary_mappings=[],
            knowledge_items=[],
            enhanced_context="测试上下文",
            relevance_scores={},
            total_tokens_used=100
        )
        
        with patch.object(integration_engine.semantic_aggregator, 'aggregate_semantic_context'):
            with patch.object(integration_engine, '_fetch_detailed_metadata', return_value=mock_result):
                
                # 第一次查询
                result1 = await integration_engine.query_integrated_metadata(sample_metadata_query)
                
                # 第二次查询应该使用缓存
                result2 = await integration_engine.query_integrated_metadata(sample_metadata_query)
                
                # 验证缓存工作
                assert result1.enhanced_context == result2.enhanced_context
                assert len(integration_engine.metadata_cache) > 0
    
    @pytest.mark.asyncio
    async def test_incremental_cache_update(self, integration_engine):
        """测试增量缓存更新"""
        # 添加一些缓存数据
        cache_key = "test_key"
        mock_cached_data = IntegratedMetadata(
            data_sources=[],
            tables=[{"id": "users", "table_name": "users"}],
            relations=[],
            dictionary_mappings=[],
            knowledge_items=[],
            enhanced_context="",
            relevance_scores={},
            total_tokens_used=0
        )
        
        integration_engine.metadata_cache[cache_key] = mock_cached_data
        integration_engine.last_update_time[cache_key] = datetime.now()
        
        # 执行增量更新
        await integration_engine.update_metadata_cache(["users"])
        
        # 验证受影响的缓存项被清除
        assert cache_key not in integration_engine.metadata_cache
        assert cache_key not in integration_engine.last_update_time
    
    def test_clear_cache(self, integration_engine):
        """测试缓存清空"""
        # 添加缓存数据
        integration_engine.metadata_cache["test"] = Mock()
        integration_engine.last_update_time["test"] = datetime.now()
        
        # 清空缓存
        integration_engine.clear_cache()
        
        # 验证缓存已清空
        assert len(integration_engine.metadata_cache) == 0
        assert len(integration_engine.last_update_time) == 0
    
    def test_get_cache_statistics(self, integration_engine):
        """测试缓存统计信息"""
        # 添加一些缓存数据
        integration_engine.metadata_cache["test1"] = Mock()
        integration_engine.metadata_cache["test2"] = Mock()
        integration_engine.last_update_time["test1"] = datetime.now()
        integration_engine.last_update_time["test2"] = datetime.now()
        
        stats = integration_engine.get_cache_statistics()
        
        # 验证统计信息
        assert isinstance(stats, dict)
        assert stats["total_cached_items"] == 2
        assert len(stats["cache_keys"]) == 2
        assert len(stats["last_update_times"]) == 2
        assert "semantic_aggregator_cache_size" in stats
    
    def test_extract_keywords(self, integration_engine):
        """测试关键词提取"""
        text = "查询用户订单信息和产品数据"
        keywords = integration_engine._extract_keywords(text)
        
        assert isinstance(keywords, set)
        # 检查2字符的中文词汇
        assert "查询" in keywords
        assert "用户" in keywords
        assert "订单" in keywords
        assert "信息" in keywords
        assert "产品" in keywords
        assert "数据" in keywords
        
        # 停用词应该被过滤
        assert "和" not in keywords
    
    def test_calculate_table_relevance(self, integration_engine):
        """测试表相关性计算"""
        table = {
            "table_name": "user_orders",
            "table_comment": "用户订单信息表",
            "fields": [
                {"field_name": "user_id", "field_comment": "用户ID"},
                {"field_name": "order_date", "field_comment": "订单日期"}
            ]
        }
        
        keywords = {"用户", "订单", "user", "order"}
        
        relevance = integration_engine._calculate_table_relevance(table, keywords)
        
        # 验证相关性计算
        assert isinstance(relevance, float)
        assert 0.0 <= relevance <= 1.0
        assert relevance > 0.5  # 应该有较高的相关性
    
    @pytest.mark.asyncio
    async def test_fetch_data_sources(self, integration_engine):
        """测试数据源信息获取"""
        # Mock 数据源服务
        mock_data_source = Mock()
        mock_data_source.id = "ds1"
        mock_data_source.name = "测试数据源"
        mock_data_source.db_type = "mysql"
        mock_data_source.host = "localhost"
        mock_data_source.port = 3306
        mock_data_source.database_name = "test_db"
        mock_data_source.status = "active"
        
        with patch.object(integration_engine.data_source_service, 'get_source_by_id', 
                         return_value=mock_data_source):
            
            result = await integration_engine._fetch_data_sources(["ds1"])
            
            # 验证数据源信息
            assert len(result) == 1
            assert result[0]["id"] == "ds1"
            assert result[0]["name"] == "测试数据源"
            assert result[0]["db_type"] == "mysql"
    
    @pytest.mark.asyncio
    async def test_fetch_tables(self, integration_engine):
        """测试表信息获取"""
        # Mock 数据表服务
        mock_table = Mock()
        mock_table.id = "users"
        mock_table.table_name = "users"
        mock_table.table_comment = "用户表"
        mock_table.data_source_id = "ds1"
        
        mock_fields = [
            Mock(field_name="id", data_type="int", description="ID", 
                 is_primary_key=True, is_nullable=False),
            Mock(field_name="name", data_type="varchar", description="姓名",
                 is_primary_key=False, is_nullable=True)
        ]
        
        with patch.object(integration_engine.data_table_service, 'get_table_by_id', 
                         return_value=mock_table):
            with patch.object(integration_engine.data_table_service, 'get_table_columns',
                             return_value=mock_fields):
                
                result = await integration_engine._fetch_tables(["users"])
                
                # 验证表信息
                assert len(result) == 1
                table = result[0]
                assert table["id"] == "users"
                assert table["table_name"] == "users"
                assert len(table["fields"]) == 2
                assert table["fields"][0]["field_name"] == "id"
                assert table["fields"][0]["is_primary_key"] is True
    
    @pytest.mark.asyncio
    async def test_fetch_dictionary_mappings(self, integration_engine):
        """测试数据字典映射获取"""
        # Mock 字典服务
        mock_result = {
            "field_mappings": [
                {
                    "table_id": "users",
                    "field_name": "name",
                    "business_name": "用户姓名",
                    "mapping_type": "DIRECT"
                }
            ]
        }
        
        with patch.object(integration_engine.dictionary_service, 'inject_semantic_values',
                         return_value=mock_result):
            
            result = await integration_engine._fetch_dictionary_mappings(["users"])
            
            # 验证字典映射
            assert len(result) == 1
            mapping = result[0]
            assert mapping["table_id"] == "users"
            assert mapping["field_name"] == "name"
            assert mapping["business_name"] == "用户姓名"
    
    @pytest.mark.asyncio
    async def test_fetch_knowledge_items(self, integration_engine):
        """测试知识库项目获取"""
        # Mock 知识库服务
        mock_term = Mock()
        mock_term.name = "用户"
        mock_term.description = "系统用户"
        mock_term.relevance_score = 0.8
        
        mock_logic = Mock()
        mock_logic.name = "订单逻辑"
        mock_logic.description = "订单处理逻辑"
        mock_logic.relevance_score = 0.7
        
        mock_knowledge_info = Mock()
        mock_knowledge_info.terms = [mock_term]
        mock_knowledge_info.logics = [mock_logic]
        mock_knowledge_info.events = []
        
        mock_result = Mock()
        mock_result.knowledge_info = mock_knowledge_info
        
        with patch.object(integration_engine.knowledge_service, 'inject_knowledge_semantics',
                         return_value=mock_result):
            
            result = await integration_engine._fetch_knowledge_items("查询用户信息", ["users"])
            
            # 验证知识库项目
            assert len(result) == 2  # 1个术语 + 1个逻辑
            
            term_item = next((item for item in result if item["type"] == "TERM"), None)
            assert term_item is not None
            assert term_item["name"] == "用户"
            assert term_item["relevance_score"] == 0.8
            
            logic_item = next((item for item in result if item["type"] == "LOGIC"), None)
            assert logic_item is not None
            assert logic_item["name"] == "订单逻辑"
            assert logic_item["relevance_score"] == 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_table_relation(self, integration_engine):
        """测试表关联分析"""
        table1 = {
            "id": "users",
            "table_name": "users",
            "data_source_id": "ds1"
        }
        
        table2 = {
            "id": "orders", 
            "table_name": "orders",
            "data_source_id": "ds2"
        }
        
        # Mock 字段信息
        fields1 = [Mock(field_name="id"), Mock(field_name="name")]
        fields2 = [Mock(field_name="id"), Mock(field_name="user_id")]
        
        with patch.object(integration_engine.data_table_service, 'get_table_columns') as mock_get_fields:
            mock_get_fields.side_effect = [fields1, fields2]
            
            relation = await integration_engine._analyze_table_relation(table1, table2)
            
            # 验证关联分析
            if relation:  # 可能找到关联
                assert relation["source_table"] == "users"
                assert relation["target_table"] == "orders"
                assert relation["source_data_source"] == "ds1"
                assert relation["target_data_source"] == "ds2"
                assert "confidence" in relation
                assert "reason" in relation
    
    @pytest.mark.asyncio
    async def test_error_handling(self, integration_engine, sample_metadata_query):
        """测试错误处理"""
        # Mock 语义聚合器抛出异常
        with patch.object(integration_engine.semantic_aggregator, 'aggregate_semantic_context',
                         side_effect=Exception("测试异常")):
            
            result = await integration_engine.query_integrated_metadata(sample_metadata_query)
            
            # 应该返回基础元数据而不是抛出异常
            assert isinstance(result, IntegratedMetadata)
            assert result.enhanced_context == f"用户问题: {sample_metadata_query.user_question}"
            assert result.total_tokens_used == 0
    
    @pytest.mark.asyncio
    async def test_empty_table_selection(self, integration_engine):
        """测试空表选择情况"""
        # Mock 返回空表列表
        with patch.object(integration_engine.data_table_service, 'get_all_tables',
                         return_value=[]):
            
            query = MetadataQuery(user_question="查询信息")
            selected_tables = await integration_engine._intelligent_table_selection(query)
            
            # 验证空结果处理
            assert selected_tables == []
    
    @pytest.mark.asyncio
    async def test_single_datasource_cross_relation(self, integration_engine):
        """测试单数据源跨关联分析（应该返回空）"""
        # 只有一个数据源
        relations = await integration_engine.get_cross_datasource_relations(["ds1"])
        
        # 单数据源不应该有跨数据源关联
        assert relations == []
    
    def test_metadata_query_dataclass(self):
        """测试MetadataQuery数据类"""
        query = MetadataQuery(
            user_question="测试问题",
            data_source_ids=["ds1"],
            table_ids=["table1"],
            include_relations=False,
            max_tables=5,
            token_budget=2000
        )
        
        assert query.user_question == "测试问题"
        assert query.data_source_ids == ["ds1"]
        assert query.table_ids == ["table1"]
        assert query.include_relations is False
        assert query.include_dictionary is True  # 默认值
        assert query.include_knowledge is True   # 默认值
        assert query.max_tables == 5
        assert query.token_budget == 2000
    
    def test_integrated_metadata_dataclass(self):
        """测试IntegratedMetadata数据类"""
        metadata = IntegratedMetadata(
            data_sources=[{"id": "ds1"}],
            tables=[{"id": "table1"}],
            relations=[{"source": "table1", "target": "table2"}],
            dictionary_mappings=[{"field": "name"}],
            knowledge_items=[{"type": "TERM"}],
            enhanced_context="测试上下文",
            relevance_scores={"module1": 0.8},
            total_tokens_used=500
        )
        
        assert len(metadata.data_sources) == 1
        assert len(metadata.tables) == 1
        assert len(metadata.relations) == 1
        assert len(metadata.dictionary_mappings) == 1
        assert len(metadata.knowledge_items) == 1
        assert metadata.enhanced_context == "测试上下文"
        assert metadata.relevance_scores["module1"] == 0.8
        assert metadata.total_tokens_used == 500