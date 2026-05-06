"""
语义增强系统单元测试
测试数据源语义注入模块的完整功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.services.semantic_enhancement import (
    DataSourceSemanticModule,
    TableStructureSemanticModule,
    TableRelationSemanticModule,
    DictionarySemanticModule,
    KnowledgeSemanticModule,
    SemanticContextAggregator,
    DatabaseType,
    DataSourceSemanticInfo,
    get_semantic_aggregator,
    init_semantic_aggregator
)


class TestDataSourceSemanticModule:
    """数据源语义注入模块测试"""
    
    @pytest.fixture
    def module(self):
        """创建数据源语义模块实例"""
        return DataSourceSemanticModule()
    
    @pytest.fixture
    def mysql_data_source(self):
        """MySQL数据源测试数据"""
        return {
            "id": "ds_mysql_001",
            "name": "MySQL Production DB",
            "type": "mysql",
            "config": {
                "host": "localhost",
                "port": 3306,
                "database": "production",
                "charset": "utf8mb4",
                "connection_pool": {
                    "min": 2,
                    "max": 20,
                    "timeout": 30
                }
            },
            "business_rules": [
                {
                    "rule_type": "data_retention",
                    "description": "数据保留30天",
                    "sql_pattern": "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
                }
            ]
        }
    
    @pytest.fixture
    def sqlserver_data_source(self):
        """SQL Server数据源测试数据"""
        return {
            "id": "ds_sqlserver_001", 
            "name": "SQL Server Analytics DB",
            "type": "sqlserver",
            "config": {
                "host": "sqlserver.company.com",
                "port": 1433,
                "database": "analytics",
                "connection_pool": {
                    "min": 1,
                    "max": 15,
                    "timeout": 60
                }
            }
        }
    
    @pytest.fixture
    def context_with_data_sources(self, mysql_data_source, sqlserver_data_source):
        """包含数据源的上下文"""
        return {
            "user_question": "查询销售数据",
            "data_sources": [mysql_data_source, sqlserver_data_source]
        }
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_success(self, module, context_with_data_sources):
        """测试成功注入语义信息"""
        result = await module.inject_semantic_info(context_with_data_sources)
        
        # 验证返回结果包含语义信息
        assert "data_source_semantics" in result
        assert len(result["data_source_semantics"]) == 2
        
        # 验证MySQL数据源语义信息
        mysql_semantic = result["data_source_semantics"][0]
        assert mysql_semantic["source_id"] == "ds_mysql_001"
        assert mysql_semantic["database_type"] == "mysql"
        assert "sql_dialect" in mysql_semantic
        assert mysql_semantic["sql_dialect"]["limit_syntax"] == "LIMIT {limit}"
        assert mysql_semantic["sql_dialect"]["quote_identifier"] == "`{identifier}`"
        
        # 验证SQL Server数据源语义信息
        sqlserver_semantic = result["data_source_semantics"][1]
        assert sqlserver_semantic["source_id"] == "ds_sqlserver_001"
        assert sqlserver_semantic["database_type"] == "sqlserver"
        assert sqlserver_semantic["sql_dialect"]["limit_syntax"] == "TOP {limit}"
        assert sqlserver_semantic["sql_dialect"]["quote_identifier"] == "[{identifier}]"
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_empty_data_sources(self, module):
        """测试空数据源列表的处理"""
        context = {"user_question": "查询数据", "data_sources": []}
        result = await module.inject_semantic_info(context)
        
        assert "data_source_semantics" in result
        assert len(result["data_source_semantics"]) == 0
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_no_data_sources(self, module):
        """测试缺少数据源的上下文"""
        context = {"user_question": "查询数据"}
        result = await module.inject_semantic_info(context)
        
        assert "data_source_semantics" in result
        assert len(result["data_source_semantics"]) == 0
    
    def test_identify_database_type_mysql(self, module):
        """测试MySQL数据库类型识别"""
        data_source = {"type": "mysql"}
        db_type = module._identify_database_type(data_source)
        assert db_type == DatabaseType.MYSQL
        
        # 测试MariaDB识别为MySQL
        data_source = {"type": "mariadb"}
        db_type = module._identify_database_type(data_source)
        assert db_type == DatabaseType.MYSQL
    
    def test_identify_database_type_sqlserver(self, module):
        """测试SQL Server数据库类型识别"""
        test_cases = ["sqlserver", "mssql", "sql_server"]
        for db_type_str in test_cases:
            data_source = {"type": db_type_str}
            db_type = module._identify_database_type(data_source)
            assert db_type == DatabaseType.SQL_SERVER
    
    def test_identify_database_type_postgresql(self, module):
        """测试PostgreSQL数据库类型识别"""
        test_cases = ["postgresql", "postgres"]
        for db_type_str in test_cases:
            data_source = {"type": db_type_str}
            db_type = module._identify_database_type(data_source)
            assert db_type == DatabaseType.POSTGRESQL
    
    def test_identify_database_type_unknown_defaults_to_mysql(self, module):
        """测试未知数据库类型默认为MySQL"""
        data_source = {"type": "unknown_db"}
        db_type = module._identify_database_type(data_source)
        assert db_type == DatabaseType.MYSQL
    
    def test_extract_connection_config(self, module, mysql_data_source):
        """测试连接配置提取"""
        config = module._extract_connection_config(mysql_data_source)
        
        assert config["host"] == "localhost"
        assert config["port"] == 3306
        assert config["database"] == "production"
        assert config["charset"] == "utf8mb4"
        assert config["connection_pool"]["min_connections"] == 2
        assert config["connection_pool"]["max_connections"] == 20
        assert config["connection_pool"]["timeout"] == 30
    
    def test_extract_business_rules_mysql(self, module, mysql_data_source):
        """测试MySQL业务规则提取"""
        rules = module._extract_business_rules(mysql_data_source)
        
        # 验证包含默认MySQL规则
        rule_types = [rule["rule_type"] for rule in rules]
        assert "query_optimization" in rule_types
        assert "date_handling" in rule_types
        
        # 验证包含自定义规则
        assert "data_retention" in rule_types
        
        # 验证MySQL特定的SQL模式
        query_opt_rule = next(rule for rule in rules if rule["rule_type"] == "query_optimization")
        assert "LIMIT" in query_opt_rule["sql_pattern"]
    
    def test_extract_business_rules_sqlserver(self, module, sqlserver_data_source):
        """测试SQL Server业务规则提取"""
        rules = module._extract_business_rules(sqlserver_data_source)
        
        # 验证包含默认SQL Server规则
        rule_types = [rule["rule_type"] for rule in rules]
        assert "query_optimization" in rule_types
        assert "date_handling" in rule_types
        
        # 验证SQL Server特定的SQL模式
        query_opt_rule = next(rule for rule in rules if rule["rule_type"] == "query_optimization")
        assert "TOP" in query_opt_rule["sql_pattern"]
    
    def test_get_sql_dialect_info(self, module):
        """测试获取SQL方言信息"""
        mysql_dialect = module.get_sql_dialect_info(DatabaseType.MYSQL)
        assert mysql_dialect["limit_syntax"] == "LIMIT {limit}"
        assert mysql_dialect["quote_identifier"] == "`{identifier}`"
        
        sqlserver_dialect = module.get_sql_dialect_info(DatabaseType.SQL_SERVER)
        assert sqlserver_dialect["limit_syntax"] == "TOP {limit}"
        assert sqlserver_dialect["quote_identifier"] == "[{identifier}]"
    
    def test_get_performance_characteristics(self, module):
        """测试获取性能特征"""
        mysql_perf = module.get_performance_characteristics(DatabaseType.MYSQL)
        assert mysql_perf["optimal_batch_size"] == 1000
        assert mysql_perf["index_hint_support"] is True
        
        sqlserver_perf = module.get_performance_characteristics(DatabaseType.SQL_SERVER)
        assert sqlserver_perf["optimal_batch_size"] == 1000
        assert sqlserver_perf["index_hint_support"] is True
    
    def test_adapt_sql_for_mysql(self, module):
        """测试MySQL SQL适配（无需修改）"""
        sql = "SELECT * FROM users LIMIT 10"
        adapted_sql = module.adapt_sql_for_database(sql, DatabaseType.MYSQL)
        assert adapted_sql == sql  # MySQL不需要修改
    
    def test_adapt_sql_for_sqlserver_simple_limit(self, module):
        """测试SQL Server SQL适配 - 简单LIMIT"""
        sql = "SELECT * FROM users LIMIT 10"
        adapted_sql = module.adapt_sql_for_database(sql, DatabaseType.SQL_SERVER)
        
        assert "SELECT TOP 10" in adapted_sql
        assert "LIMIT" not in adapted_sql
        assert "FROM users" in adapted_sql
    
    def test_adapt_sql_for_sqlserver_complex_query(self, module):
        """测试SQL Server SQL适配 - 复杂查询"""
        sql = "SELECT u.name, u.email FROM users u WHERE u.active = 1 LIMIT 5"
        adapted_sql = module.adapt_sql_for_database(sql, DatabaseType.SQL_SERVER)
        
        assert "SELECT TOP 5" in adapted_sql
        assert "LIMIT" not in adapted_sql
        assert "u.name, u.email FROM users u WHERE u.active = 1" in adapted_sql
    
    def test_adapt_sql_for_sqlserver_no_limit(self, module):
        """测试SQL Server SQL适配 - 无LIMIT语句"""
        sql = "SELECT * FROM users WHERE active = 1"
        adapted_sql = module.adapt_sql_for_database(sql, DatabaseType.SQL_SERVER)
        
        # 没有LIMIT的SQL不应该被修改
        assert adapted_sql == sql
    
    def test_get_module_name(self, module):
        """测试获取模块名称"""
        assert module.get_module_name() == "DataSourceSemanticModule"
    
    @pytest.mark.asyncio
    async def test_create_data_source_semantic_info(self, module, mysql_data_source):
        """测试创建数据源语义信息"""
        semantic_info = await module._create_data_source_semantic_info(mysql_data_source)
        
        assert isinstance(semantic_info, DataSourceSemanticInfo)
        assert semantic_info.source_id == "ds_mysql_001"
        assert semantic_info.source_name == "MySQL Production DB"
        assert semantic_info.database_type == DatabaseType.MYSQL
        assert semantic_info.sql_dialect["limit_syntax"] == "LIMIT {limit}"
        assert len(semantic_info.business_rules) >= 2  # 默认规则 + 自定义规则


class TestSemanticContextAggregator:
    """语义上下文聚合引擎测试"""
    
    @pytest.fixture
    def aggregator(self):
        """创建语义聚合器实例"""
        return SemanticContextAggregator(max_tokens=1000)
    
    @pytest.fixture
    def base_context(self):
        """基础上下文"""
        return {
            "user_question": "查询销售数据",
            "data_sources": [
                {
                    "id": "ds_001",
                    "name": "Sales DB",
                    "type": "mysql"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_aggregate_semantic_context_all_modules(self, aggregator, base_context):
        """测试聚合所有模块的语义上下文"""
        result = await aggregator.aggregate_semantic_context(base_context)
        
        # 验证包含数据源语义信息（目前只有这个模块实现了）
        assert "data_source_semantics" in result
        assert len(result["data_source_semantics"]) == 1
        
        # 验证原始上下文保持不变
        assert result["user_question"] == "查询销售数据"
        assert "data_sources" in result
    
    @pytest.mark.asyncio
    async def test_aggregate_semantic_context_specific_modules(self, aggregator, base_context):
        """测试聚合指定模块的语义上下文"""
        enabled_modules = ["DataSourceSemanticModule"]
        result = await aggregator.aggregate_semantic_context(base_context, enabled_modules)
        
        # 验证只包含指定模块的语义信息
        assert "data_source_semantics" in result
        assert len(result["data_source_semantics"]) == 1
    
    @pytest.mark.asyncio
    async def test_aggregate_semantic_context_empty_modules(self, aggregator, base_context):
        """测试空模块列表"""
        enabled_modules = []
        result = await aggregator.aggregate_semantic_context(base_context, enabled_modules)
        
        # 验证没有添加语义信息
        assert "data_source_semantics" not in result
        assert result == base_context
    
    def test_optimize_context_for_tokens_no_optimization_needed(self, aggregator):
        """测试Token数量在限制内时不需要优化"""
        small_context = {"user_question": "简单问题", "data": "少量数据"}
        optimized = aggregator._optimize_context_for_tokens(small_context)
        
        assert optimized == small_context
    
    def test_optimize_context_for_tokens_optimization_needed(self, aggregator):
        """测试Token数量超限时需要优化"""
        # 创建一个大的上下文
        large_context = {
            "user_question": "复杂问题",
            "knowledge_semantics": ["知识" * 100] * 10,  # 大量知识库信息
            "table_relation_semantics": ["关联" * 100] * 10,  # 大量关联信息
            "dictionary_semantics": ["字典" * 100] * 10,  # 大量字典信息
            "table_structure_semantics": ["结构" * 100] * 10,  # 大量结构信息
            "data_source_semantics": ["数据源" * 100] * 10  # 大量数据源信息
        }
        
        optimized = aggregator._optimize_context_for_tokens(large_context)
        
        # 验证优化后的上下文更小
        import json
        original_size = len(json.dumps(large_context, ensure_ascii=False))
        optimized_size = len(json.dumps(optimized, ensure_ascii=False))
        assert optimized_size < original_size
        
        # 验证保留了高优先级信息（数据源语义）
        assert "data_source_semantics" in optimized
    
    def test_get_enabled_modules(self, aggregator):
        """测试获取已启用的模块列表"""
        modules = aggregator.get_enabled_modules()
        
        expected_modules = [
            "DataSourceSemanticModule",
            "TableStructureSemanticModule", 
            "TableRelationSemanticModule",
            "DictionarySemanticModule",
            "KnowledgeSemanticModule"
        ]
        
        assert modules == expected_modules


class TestTableRelationSemanticModule:
    """表关联语义注入模块测试"""
    
    @pytest.fixture
    def module(self):
        """创建表关联语义模块实例"""
        return TableRelationSemanticModule()
    
    @pytest.fixture
    def users_table(self):
        """用户表结构"""
        return {
            "id": "users_table",
            "name": "users",
            "schema": "public",
            "fields": [
                {"name": "id", "type": "bigint", "is_primary_key": True},
                {"name": "username", "type": "varchar(50)"},
                {"name": "email", "type": "varchar(100)"},
                {"name": "created_at", "type": "datetime"}
            ],
            "foreign_keys": [],
            "indexes": []
        }
    
    @pytest.fixture
    def orders_table(self):
        """订单表结构"""
        return {
            "id": "orders_table",
            "name": "orders",
            "schema": "public",
            "fields": [
                {"name": "id", "type": "bigint", "is_primary_key": True},
                {"name": "user_id", "type": "bigint"},
                {"name": "amount", "type": "decimal(10,2)"},
                {"name": "status", "type": "varchar(20)"},
                {"name": "created_at", "type": "datetime"}
            ],
            "foreign_keys": [
                {
                    "name": "fk_orders_user_id",
                    "column": "user_id",
                    "referenced_table": "users",
                    "referenced_column": "id"
                }
            ],
            "indexes": []
        }
    
    @pytest.fixture
    def order_items_table(self):
        """订单明细表结构"""
        return {
            "id": "order_items_table",
            "name": "order_items",
            "schema": "public",
            "fields": [
                {"name": "id", "type": "bigint", "is_primary_key": True},
                {"name": "order_id", "type": "bigint"},
                {"name": "product_id", "type": "bigint"},
                {"name": "quantity", "type": "int"},
                {"name": "price", "type": "decimal(10,2)"}
            ],
            "foreign_keys": [
                {
                    "name": "fk_order_items_order_id",
                    "column": "order_id",
                    "referenced_table": "orders",
                    "referenced_column": "id"
                }
            ],
            "indexes": []
        }
    
    @pytest.fixture
    def products_table(self):
        """产品表结构"""
        return {
            "id": "products_table",
            "name": "products",
            "schema": "public",
            "fields": [
                {"name": "id", "type": "bigint", "is_primary_key": True},
                {"name": "name", "type": "varchar(100)"},
                {"name": "category_id", "type": "bigint"},
                {"name": "price", "type": "decimal(10,2)"}
            ],
            "foreign_keys": [],
            "indexes": []
        }
    
    @pytest.fixture
    def context_with_multiple_tables(self, users_table, orders_table, order_items_table, products_table):
        """包含多个表的上下文"""
        return {
            "user_question": "查询用户订单和商品信息",
            "tables": [users_table, orders_table, order_items_table, products_table]
        }
    
    @pytest.fixture
    def context_with_two_tables(self, users_table, orders_table):
        """包含两个表的上下文"""
        return {
            "user_question": "查询用户订单",
            "tables": [users_table, orders_table]
        }
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_success(self, module, context_with_multiple_tables):
        """测试成功注入表关联语义信息"""
        result = await module.inject_semantic_info(context_with_multiple_tables)
        
        # 验证返回结果包含表关联语义信息
        assert "table_relation_semantics" in result
        assert len(result["table_relation_semantics"]) > 0
        
        # 验证关联关系信息
        relations = result["table_relation_semantics"]
        
        # 应该发现用户-订单关联
        user_order_relation = next(
            (r for r in relations if r["source_table"] == "orders" and r["target_table"] == "users"), 
            None
        )
        assert user_order_relation is not None
        assert user_order_relation["join_type"] in ["INNER", "LEFT", "RIGHT", "FULL"]
        assert len(user_order_relation["join_conditions"]) > 0
        
        # 验证最优关联路径
        if "optimal_join_paths" in result:
            paths = result["optimal_join_paths"]
            assert len(paths) > 0
            
            # 验证路径信息
            for path in paths:
                assert "source_table" in path
                assert "target_table" in path
                assert "path_length" in path
                assert "join_sequence" in path
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_single_table(self, module):
        """测试单表情况的处理"""
        context = {
            "user_question": "查询用户信息",
            "tables": [{"name": "users", "fields": []}]
        }
        result = await module.inject_semantic_info(context)
        
        assert "table_relation_semantics" in result
        assert len(result["table_relation_semantics"]) == 0
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_no_tables(self, module):
        """测试无表情况的处理"""
        context = {"user_question": "查询数据", "tables": []}
        result = await module.inject_semantic_info(context)
        
        assert "table_relation_semantics" in result
        assert len(result["table_relation_semantics"]) == 0
    
    @pytest.mark.asyncio
    async def test_discover_foreign_key_relations(self, module, users_table, orders_table):
        """测试基于外键发现关联关系"""
        tables = [users_table, orders_table]
        relations = module._discover_foreign_key_relations(tables)
        
        assert len(relations) == 1
        relation = relations[0]
        assert relation["source_table"] == "orders"
        assert relation["target_table"] == "users"
        assert relation["source_field"] == "user_id"
        assert relation["target_field"] == "id"
        assert relation["relation_type"] == "FOREIGN_KEY"
        assert relation["confidence"] == 1.0
    
    @pytest.mark.asyncio
    async def test_discover_pattern_based_relations(self, module, users_table, orders_table):
        """测试基于模式发现关联关系"""
        tables = [users_table, orders_table]
        relations = module._discover_pattern_based_relations(tables)
        
        # 应该发现 user_id 模式
        user_id_relations = [r for r in relations if r["source_field"] == "user_id"]
        assert len(user_id_relations) > 0
        
        relation = user_id_relations[0]
        assert relation["relation_type"] == "PATTERN_MATCH"
        assert relation["discovery_method"] == "field_pattern"
        assert relation["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_discover_business_pattern_relations(self, module, users_table, orders_table):
        """测试基于业务模式发现关联关系"""
        tables = [users_table, orders_table]
        relations = module._discover_business_pattern_relations(tables)
        
        # 应该发现用户-订单业务模式
        business_relations = [r for r in relations if r["discovery_method"] == "business_pattern"]
        assert len(business_relations) > 0
        
        relation = business_relations[0]
        assert "business_meaning" in relation
        assert relation["confidence"] == 0.7
    
    def test_get_table_base_name(self, module):
        """测试获取表名基础形式"""
        assert module._get_table_base_name("users") == "user"
        assert module._get_table_base_name("orders") == "order"
        assert module._get_table_base_name("tbl_products") == "product"
        assert module._get_table_base_name("t_categories") == "categorie"
        assert module._get_table_base_name("user_profiles") == "user_profile"
    
    def test_field_exists_in_table(self, module, users_table):
        """测试字段存在性检查"""
        assert module._field_exists_in_table(users_table, "id") is True
        assert module._field_exists_in_table(users_table, "username") is True
        assert module._field_exists_in_table(users_table, "nonexistent") is False
        assert module._field_exists_in_table(users_table, "ID") is True  # 大小写不敏感
    
    def test_deduplicate_relations(self, module):
        """测试关联关系去重"""
        relations = [
            {
                "source_table": "orders",
                "target_table": "users",
                "source_field": "user_id",
                "target_field": "id",
                "confidence": 0.8
            },
            {
                "source_table": "orders",
                "target_table": "users",
                "source_field": "user_id",
                "target_field": "id",
                "confidence": 1.0  # 更高置信度
            }
        ]
        
        unique_relations = module._deduplicate_relations(relations)
        assert len(unique_relations) == 1
        assert unique_relations[0]["confidence"] == 1.0  # 保留高置信度的
    
    @pytest.mark.asyncio
    async def test_create_relation_semantic_info(self, module, users_table, orders_table):
        """测试创建关联关系语义信息"""
        relation = {
            "source_table": "orders",
            "target_table": "users",
            "source_field": "user_id",
            "target_field": "id",
            "relation_type": "FOREIGN_KEY",
            "confidence": 1.0,
            "discovery_method": "foreign_key"
        }
        
        tables = [users_table, orders_table]
        semantic_info = await module._create_relation_semantic_info(relation, tables)
        
        assert semantic_info.source_table == "orders"
        assert semantic_info.target_table == "users"
        assert semantic_info.join_type in ["INNER", "LEFT", "RIGHT", "FULL"]
        assert len(semantic_info.join_conditions) == 1
        assert semantic_info.relation_description is not None
        assert semantic_info.business_logic is not None
        
        # 验证JOIN条件
        join_condition = semantic_info.join_conditions[0]
        assert join_condition["source_field"] == "user_id"
        assert join_condition["target_field"] == "id"
        assert join_condition["operator"] == "="
    
    def test_recommend_join_type(self, module):
        """测试JOIN类型推荐"""
        # 外键关系推荐INNER
        fk_relation = {"discovery_method": "foreign_key"}
        assert module._recommend_join_type(fk_relation, []) == "INNER"
        
        # ID字段推荐LEFT
        id_relation = {"source_field": "user_id"}
        assert module._recommend_join_type(id_relation, []) == "LEFT"
        
        # 一对多关系推荐LEFT
        one_to_many = {"relation_type": "ONE_TO_MANY"}
        assert module._recommend_join_type(one_to_many, []) == "LEFT"
        
        # 多对一关系推荐INNER
        many_to_one = {"relation_type": "MANY_TO_ONE"}
        assert module._recommend_join_type(many_to_one, []) == "INNER"
    
    def test_generate_relation_description(self, module):
        """测试关联关系描述生成"""
        relation = {
            "source_table": "orders",
            "target_table": "users",
            "source_field": "user_id",
            "target_field": "id",
            "discovery_method": "foreign_key"
        }
        
        description = module._generate_relation_description(relation, "INNER")
        assert "外键" in description
        assert "orders" in description
        assert "users" in description
        assert "user_id" in description
        assert "内连接" in description
    
    def test_generate_business_logic(self, module, users_table, orders_table):
        """测试业务逻辑生成"""
        relation = {
            "source_table": "orders",
            "target_table": "users"
        }
        
        tables = [users_table, orders_table]
        business_logic = module._generate_business_logic(relation, tables)
        
        assert business_logic is not None
        assert len(business_logic) > 0
    
    def test_build_relation_graph(self, module):
        """测试关联关系图构建"""
        relations = [
            {"source_table": "users", "target_table": "orders"},
            {"source_table": "orders", "target_table": "order_items"},
            {"source_table": "order_items", "target_table": "products"}
        ]
        
        graph = module._build_relation_graph(relations)
        
        assert "users" in graph
        assert "orders" in graph["users"]
        assert "users" in graph["orders"]  # 双向关联
        assert len(graph["orders"]) == 2  # orders连接users和order_items
    
    def test_find_shortest_path(self, module):
        """测试最短路径查找"""
        graph = {
            "users": ["orders"],
            "orders": ["users", "order_items"],
            "order_items": ["orders", "products"],
            "products": ["order_items"]
        }
        
        # 直接连接
        path = module._find_shortest_path(graph, "users", "orders")
        assert path == ["users", "orders"]
        
        # 间接连接
        path = module._find_shortest_path(graph, "users", "products")
        assert path == ["users", "orders", "order_items", "products"]
        
        # 无连接
        isolated_graph = {"users": [], "products": []}
        path = module._find_shortest_path(isolated_graph, "users", "products")
        assert path == []
    
    def test_find_relation(self, module):
        """测试查找关联关系"""
        relations = [
            {
                "source_table": "orders",
                "target_table": "users",
                "source_field": "user_id",
                "target_field": "id"
            }
        ]
        
        # 正向查找
        relation = module._find_relation(relations, "orders", "users")
        assert relation is not None
        assert relation["source_field"] == "user_id"
        
        # 反向查找
        relation = module._find_relation(relations, "users", "orders")
        assert relation is not None
        
        # 未找到
        relation = module._find_relation(relations, "products", "categories")
        assert relation is None
    
    def test_estimate_path_performance(self, module):
        """测试路径性能估算"""
        relations = [
            {"source_table": "users", "target_table": "orders", "confidence": 1.0},
            {"source_table": "orders", "target_table": "order_items", "confidence": 0.8}
        ]
        
        # 短路径性能更好
        short_path = ["users", "orders"]
        long_path = ["users", "orders", "order_items"]
        
        short_score = module._estimate_path_performance(short_path, relations)
        long_score = module._estimate_path_performance(long_path, relations)
        
        assert short_score > long_score
    
    def test_describe_join_path(self, module):
        """测试JOIN路径描述"""
        relations = [
            {
                "source_table": "users",
                "target_table": "orders",
                "business_meaning": "用户的订单记录"
            }
        ]
        
        path = ["users", "orders"]
        description = module._describe_join_path(path, relations)
        
        assert "用户的订单记录" in description
    
    @pytest.mark.asyncio
    async def test_generate_optimal_join_paths(self, module, context_with_multiple_tables):
        """测试最优关联路径生成"""
        tables = context_with_multiple_tables["tables"]
        
        # 模拟一些关联关系（包含必需的字段）
        relations = [
            {
                "source_table": "orders", 
                "target_table": "users", 
                "source_field": "user_id",
                "target_field": "id",
                "confidence": 1.0
            },
            {
                "source_table": "order_items", 
                "target_table": "orders", 
                "source_field": "order_id",
                "target_field": "id",
                "confidence": 1.0
            },
            {
                "source_table": "order_items", 
                "target_table": "products", 
                "source_field": "product_id",
                "target_field": "id",
                "confidence": 0.8
            }
        ]
        
        paths = module._generate_optimal_join_paths(relations, tables)
        
        assert len(paths) > 0
        
        for path in paths:
            assert "source_table" in path
            assert "target_table" in path
            assert "path_length" in path
            assert "join_sequence" in path
            assert "estimated_performance" in path
            assert "business_description" in path
    
    def test_get_relation_summary(self, module):
        """测试关联关系摘要"""
        from src.services.semantic_enhancement import TableRelationSemanticInfo
        
        relations = [
            TableRelationSemanticInfo(
                relation_id="rel1",
                source_table="orders",
                target_table="users",
                join_type="INNER",
                join_conditions=[],
                relation_description="",
                business_logic=""
            ),
            TableRelationSemanticInfo(
                relation_id="rel2",
                source_table="order_items",
                target_table="orders",
                join_type="LEFT",
                join_conditions=[],
                relation_description="",
                business_logic=""
            )
        ]
        
        summary = module.get_relation_summary(relations)
        
        assert "2个表关联关系" in summary
        assert "内连接" in summary
        assert "左外连接" in summary
    
    def test_get_module_name(self, module):
        """测试获取模块名称"""
        assert module.get_module_name() == "TableRelationSemanticModule"


class TestTableStructureSemanticModule:
    """表结构语义注入模块测试"""
    
    @pytest.fixture
    def module(self):
        """创建表结构语义模块实例"""
        return TableStructureSemanticModule()
    
    @pytest.fixture
    def users_table_structure(self):
        """用户表结构测试数据"""
        return {
            "id": "users_table",
            "name": "users",
            "schema": "public",
            "comment": "用户信息表",
            "fields": [
                {
                    "name": "id",
                    "type": "bigint",
                    "comment": "用户ID",
                    "is_primary_key": True,
                    "is_nullable": False
                },
                {
                    "name": "username",
                    "type": "varchar(50)",
                    "comment": "用户名",
                    "is_nullable": False,
                    "max_length": 50
                },
                {
                    "name": "email",
                    "type": "varchar(100)",
                    "comment": "邮箱地址",
                    "is_nullable": True,
                    "max_length": 100
                },
                {
                    "name": "created_at",
                    "type": "datetime",
                    "comment": "创建时间",
                    "is_nullable": False,
                    "default_value": "CURRENT_TIMESTAMP"
                },
                {
                    "name": "updated_at",
                    "type": "datetime",
                    "comment": "更新时间",
                    "is_nullable": True
                },
                {
                    "name": "is_active",
                    "type": "tinyint",
                    "comment": "是否激活",
                    "is_nullable": False,
                    "default_value": 1
                },
                {
                    "name": "balance",
                    "type": "decimal(10,2)",
                    "comment": "账户余额",
                    "is_nullable": True,
                    "precision": 10,
                    "scale": 2
                }
            ],
            "foreign_keys": [],
            "indexes": [
                {
                    "name": "idx_username",
                    "type": "BTREE",
                    "columns": ["username"],
                    "is_unique": True
                },
                {
                    "name": "idx_email",
                    "type": "BTREE", 
                    "columns": ["email"],
                    "is_unique": False
                }
            ]
        }
    
    @pytest.fixture
    def orders_table_structure(self):
        """订单表结构测试数据"""
        return {
            "id": "orders_table",
            "name": "orders",
            "schema": "public",
            "comment": "订单信息表",
            "fields": [
                {
                    "name": "id",
                    "type": "bigint",
                    "comment": "订单ID",
                    "is_primary_key": True,
                    "is_nullable": False
                },
                {
                    "name": "user_id",
                    "type": "bigint",
                    "comment": "用户ID",
                    "is_nullable": False
                },
                {
                    "name": "order_no",
                    "type": "varchar(32)",
                    "comment": "订单号",
                    "is_nullable": False,
                    "max_length": 32
                },
                {
                    "name": "total_amount",
                    "type": "decimal(12,2)",
                    "comment": "订单总金额",
                    "is_nullable": False,
                    "precision": 12,
                    "scale": 2
                },
                {
                    "name": "status",
                    "type": "varchar(20)",
                    "comment": "订单状态",
                    "is_nullable": False,
                    "default_value": "pending"
                },
                {
                    "name": "created_at",
                    "type": "datetime",
                    "comment": "创建时间",
                    "is_nullable": False
                }
            ],
            "foreign_keys": [
                {
                    "name": "fk_orders_user_id",
                    "column": "user_id",
                    "referenced_table": "users",
                    "referenced_column": "id"
                }
            ],
            "indexes": [
                {
                    "name": "idx_user_id",
                    "type": "BTREE",
                    "columns": ["user_id"],
                    "is_unique": False
                },
                {
                    "name": "idx_order_no",
                    "type": "BTREE",
                    "columns": ["order_no"],
                    "is_unique": True
                }
            ]
        }
    
    @pytest.fixture
    def context_with_tables(self, users_table_structure, orders_table_structure):
        """包含表结构的上下文"""
        return {
            "user_question": "查询用户订单信息",
            "tables": [users_table_structure, orders_table_structure]
        }
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_success(self, module, context_with_tables):
        """测试成功注入表结构语义信息"""
        result = await module.inject_semantic_info(context_with_tables)
        
        # 验证返回结果包含表结构语义信息
        assert "table_structure_semantics" in result
        assert len(result["table_structure_semantics"]) == 2
        
        # 验证用户表语义信息
        users_semantic = result["table_structure_semantics"][0]
        assert users_semantic["table_name"] == "users"
        assert users_semantic["business_meaning"] is not None
        assert len(users_semantic["fields"]) == 7
        assert len(users_semantic["primary_keys"]) == 1
        assert users_semantic["primary_keys"][0] == "id"
        
        # 验证订单表语义信息
        orders_semantic = result["table_structure_semantics"][1]
        assert orders_semantic["table_name"] == "orders"
        assert len(orders_semantic["foreign_keys"]) == 1
        assert orders_semantic["foreign_keys"][0]["referenced_table"] == "users"
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_empty_tables(self, module):
        """测试空表列表的处理"""
        context = {"user_question": "查询数据", "tables": []}
        result = await module.inject_semantic_info(context)
        
        assert "table_structure_semantics" in result
        assert len(result["table_structure_semantics"]) == 0
    
    @pytest.mark.asyncio
    async def test_inject_semantic_info_no_tables(self, module):
        """测试缺少表的上下文处理"""
        context = {"user_question": "查询数据"}
        result = await module.inject_semantic_info(context)
        
        assert "table_structure_semantics" in result
        assert len(result["table_structure_semantics"]) == 0
    
    @pytest.mark.asyncio
    async def test_create_table_semantic_info(self, module, users_table_structure):
        """测试创建表结构语义信息"""
        semantic_info = await module._create_table_semantic_info(users_table_structure)
        
        assert semantic_info.table_name == "users"
        assert semantic_info.schema_name == "public"
        assert semantic_info.table_comment == "用户信息表"
        assert len(semantic_info.fields) == 7
        assert len(semantic_info.primary_keys) == 1
        assert semantic_info.primary_keys[0] == "id"
        assert semantic_info.business_meaning is not None
    
    @pytest.mark.asyncio
    async def test_enhance_field_info(self, module):
        """测试字段信息增强"""
        field = {
            "name": "user_id",
            "type": "bigint",
            "comment": "用户标识符",
            "is_nullable": False,
            "is_primary_key": False
        }
        
        enhanced_field = await module._enhance_field_info(field, "orders")
        
        assert enhanced_field["name"] == "user_id"
        assert enhanced_field["type"] == "bigint"
        assert "type_semantic" in enhanced_field
        assert "field_pattern" in enhanced_field
        assert "business_meaning" in enhanced_field
        assert "constraints_semantic" in enhanced_field
        
        # 验证字段模式识别
        assert enhanced_field["field_pattern"]["type"] == "identifier"
        
        # 验证数据类型语义
        assert enhanced_field["type_semantic"]["category"] == "数值"
    
    def test_get_data_type_semantic(self, module):
        """测试数据类型语义化"""
        # 测试整数类型
        int_semantic = module._get_data_type_semantic("bigint")
        assert int_semantic["category"] == "数值"
        assert "大整数类型" in int_semantic["description"]
        
        # 测试字符串类型
        varchar_semantic = module._get_data_type_semantic("varchar(50)")
        assert varchar_semantic["category"] == "文本"
        assert "可变长度" in varchar_semantic["description"]
        
        # 测试时间类型
        datetime_semantic = module._get_data_type_semantic("datetime")
        assert datetime_semantic["category"] == "时间"
        assert "日期时间" in datetime_semantic["description"]
        
        # 测试未知类型
        unknown_semantic = module._get_data_type_semantic("unknown_type")
        assert unknown_semantic["category"] == "其他"
    
    def test_recognize_field_pattern(self, module):
        """测试字段名模式识别"""
        # 测试ID字段
        id_pattern = module._recognize_field_pattern("user_id")
        assert id_pattern["type"] == "identifier"
        assert "标识符" in id_pattern["meaning"]
        
        # 测试主键字段
        pk_pattern = module._recognize_field_pattern("id")
        assert pk_pattern["type"] == "identifier"  # "id"字段匹配identifier模式
        assert "标识符" in pk_pattern["meaning"]
        
        # 测试时间字段
        time_pattern = module._recognize_field_pattern("created_at")
        assert time_pattern["type"] == "timestamp"
        assert "创建时间" in time_pattern["meaning"]
        
        # 测试状态字段
        status_pattern = module._recognize_field_pattern("status")
        assert status_pattern["type"] == "status"
        assert "状态" in status_pattern["meaning"]
        
        # 测试布尔字段
        bool_pattern = module._recognize_field_pattern("is_active")
        assert bool_pattern["type"] == "boolean"
        assert "是否标记" in bool_pattern["meaning"]
        
        # 测试通用字段
        general_pattern = module._recognize_field_pattern("some_field")
        assert general_pattern["type"] == "general"
    
    def test_infer_field_business_meaning(self, module):
        """测试字段业务含义推断"""
        meaning = module._infer_field_business_meaning(
            "user_id", "bigint", "用户标识符", "orders"
        )
        
        assert "用户标识符" in meaning  # 注释含义
        assert "标识符" in meaning      # 字段模式含义
        assert "大数值ID、时间戳" in meaning    # 数据类型含义（bigint对应的business_meaning）
        assert "订单" in meaning        # 表上下文含义
    
    def test_get_table_base_name(self, module):
        """测试获取表名基础形式"""
        assert module._get_table_base_name("users") == "user"
        assert module._get_table_base_name("orders") == "order"
        assert module._get_table_base_name("tbl_products") == "product"
        assert module._get_table_base_name("t_categories") == "categorie"
        assert module._get_table_base_name("user") == "user"  # 单数形式保持不变
    
    def test_analyze_field_constraints(self, module):
        """测试字段约束分析"""
        field = {
            "name": "username",
            "type": "varchar(50)",
            "is_primary_key": False,
            "is_nullable": False,
            "max_length": 50,
            "default_value": None
        }
        
        constraints = module._analyze_field_constraints(field)
        
        # 验证非空约束
        not_null_constraint = next((c for c in constraints if c["type"] == "NOT_NULL"), None)
        assert not_null_constraint is not None
        assert "非空约束" in not_null_constraint["description"]
        
        # 验证长度约束
        length_constraint = next((c for c in constraints if c["type"] == "LENGTH"), None)
        assert length_constraint is not None
        assert "50" in length_constraint["description"]
    
    def test_analyze_field_constraints_primary_key(self, module):
        """测试主键字段约束分析"""
        field = {
            "name": "id",
            "type": "bigint",
            "is_primary_key": True,
            "is_nullable": False
        }
        
        constraints = module._analyze_field_constraints(field)
        
        # 验证主键约束
        pk_constraint = next((c for c in constraints if c["type"] == "PRIMARY_KEY"), None)
        assert pk_constraint is not None
        assert "主键约束" in pk_constraint["description"]
        assert "唯一标识符" in pk_constraint["business_impact"]
    
    def test_process_foreign_keys(self, module):
        """测试外键信息处理"""
        foreign_keys = [
            {
                "name": "fk_orders_user_id",
                "column": "user_id",
                "referenced_table": "users",
                "referenced_column": "id"
            }
        ]
        
        processed_fks = module._process_foreign_keys(foreign_keys)
        
        assert len(processed_fks) == 1
        fk = processed_fks[0]
        assert fk["name"] == "fk_orders_user_id"
        assert fk["column"] == "user_id"
        assert fk["referenced_table"] == "users"
        assert "外键关联" in fk["semantic_description"]
        assert "关联关系" in fk["business_meaning"]
    
    def test_process_indexes(self, module):
        """测试索引信息处理"""
        indexes = [
            {
                "name": "idx_username",
                "type": "BTREE",
                "columns": ["username"],
                "is_unique": True
            },
            {
                "name": "idx_user_created",
                "type": "BTREE",
                "columns": ["user_id", "created_at"],
                "is_unique": False
            }
        ]
        
        processed_indexes = module._process_indexes(indexes)
        
        assert len(processed_indexes) == 2
        
        # 验证唯一索引
        unique_index = processed_indexes[0]
        assert unique_index["is_unique"] is True
        assert "唯一" in unique_index["semantic_description"]
        assert "单字段" in unique_index["performance_impact"]
        
        # 验证复合索引
        composite_index = processed_indexes[1]
        assert composite_index["is_unique"] is False
        assert len(composite_index["columns"]) == 2
        assert "复合" in composite_index["performance_impact"]
    
    def test_get_index_semantic_description(self, module):
        """测试索引语义描述生成"""
        # 唯一索引
        unique_desc = module._get_index_semantic_description("BTREE", ["username"], True)
        assert "唯一" in unique_desc
        assert "username" in unique_desc
        
        # 普通索引
        normal_desc = module._get_index_semantic_description("BTREE", ["user_id"], False)
        assert "加速" in normal_desc
        assert "user_id" in normal_desc
    
    def test_get_index_performance_impact(self, module):
        """测试索引性能影响描述"""
        # 单字段B树索引
        single_btree = module._get_index_performance_impact("BTREE", 1)
        assert "单字段B树索引" in single_btree
        assert "等值和范围查询" in single_btree
        
        # 复合B树索引
        composite_btree = module._get_index_performance_impact("BTREE", 2)
        assert "复合B树索引" in composite_btree
        assert "左前缀匹配" in composite_btree
        
        # 哈希索引
        hash_index = module._get_index_performance_impact("HASH", 1)
        assert "哈希索引" in hash_index
        assert "等值查询" in hash_index
        assert "不支持范围查询" in hash_index
    
    def test_infer_table_business_meaning(self, module):
        """测试表业务含义推断"""
        fields = [
            {"field_pattern": {"type": "primary_key"}},
            {"field_pattern": {"type": "timestamp"}},
            {"field_pattern": {"type": "status"}}
        ]
        
        meaning = module._infer_table_business_meaning("users", fields, "用户信息表")
        
        assert "用户信息表" in meaning      # 表注释
        assert "用户信息管理" in meaning    # 业务领域
        assert "字段分析" in meaning       # 字段分析
        assert "结构特征" in meaning       # 结构特征
    
    def test_analyze_table_fields(self, module):
        """测试表字段分析"""
        fields = [
            {"field_pattern": {"type": "primary_key"}},
            {"field_pattern": {"type": "identifier"}},
            {"field_pattern": {"type": "timestamp"}},
            {"field_pattern": {"type": "timestamp"}},
            {"field_pattern": {"type": "status"}},
            {"field_pattern": {"type": "amount"}}
        ]
        
        analysis = module._analyze_table_fields(fields)
        
        assert "完整的时间戳管理" in analysis  # 2个timestamp字段
        assert "状态管理字段" in analysis      # 1个status字段
        assert "金额" in analysis            # 1个amount字段
    
    def test_analyze_table_structure(self, module):
        """测试表结构分析"""
        # 大型表结构
        large_fields = [{"is_nullable": True, "is_primary_key": False}] * 25
        large_fields[0]["is_primary_key"] = True
        large_analysis = module._analyze_table_structure(large_fields)
        assert "大型表结构" in large_analysis
        
        # 简单表结构
        simple_fields = [
            {"is_nullable": False, "is_primary_key": True},
            {"is_nullable": True, "is_primary_key": False}
        ]
        simple_analysis = module._analyze_table_structure(simple_fields)
        assert "简单表结构" in simple_analysis
        
        # 无主键结构
        no_pk_fields = [{"is_nullable": True, "is_primary_key": False}] * 3
        no_pk_analysis = module._analyze_table_structure(no_pk_fields)
        assert "缺少主键定义" in no_pk_analysis
    
    def test_get_table_structure_summary(self, module):
        """测试表结构摘要生成"""
        from src.services.semantic_enhancement import TableSemanticInfo
        
        tables = [
            TableSemanticInfo(
                table_id="users",
                table_name="users",
                schema_name="public",
                table_comment="用户表",
                fields=[
                    {"type_semantic": {"category": "数值"}},
                    {"type_semantic": {"category": "文本"}},
                    {"type_semantic": {"category": "时间"}}
                ],
                primary_keys=["id"],
                foreign_keys=[],
                indexes=[],
                business_meaning="用户管理"
            )
        ]
        
        summary = module.get_table_structure_summary(tables)
        
        assert "1个表" in summary
        assert "3个字段" in summary
        assert "字段类型分布" in summary
        assert "数值: 1个" in summary
        assert "文本: 1个" in summary
        assert "时间: 1个" in summary
    
    def test_get_table_structure_summary_empty(self, module):
        """测试空表结构摘要"""
        summary = module.get_table_structure_summary([])
        assert summary == "无表结构信息"
    
    def test_get_module_name(self, module):
        """测试获取模块名称"""
        assert module.get_module_name() == "TableStructureSemanticModule"


class TestOtherSemanticModules:
    """其他语义模块基础测试"""
    
    def test_table_structure_module_name(self):
        """测试表结构模块名称"""
        module = TableStructureSemanticModule()
        assert module.get_module_name() == "TableStructureSemanticModule"
    
    def test_table_relation_module_name(self):
        """测试表关联模块名称"""
        module = TableRelationSemanticModule()
        assert module.get_module_name() == "TableRelationSemanticModule"
    
    def test_dictionary_module_name(self):
        """测试数据字典模块名称"""
        module = DictionarySemanticModule()
        assert module.get_module_name() == "DictionarySemanticModule"
    
    def test_knowledge_module_name(self):
        """测试知识库模块名称"""
        module = KnowledgeSemanticModule()
        assert module.get_module_name() == "KnowledgeSemanticModule"
    
    @pytest.mark.asyncio
    async def test_placeholder_modules_return_context_unchanged(self):
        """测试占位符模块返回未修改的上下文"""
        context = {"test": "data"}
        
        modules = [
            DictionarySemanticModule(),
            KnowledgeSemanticModule()
        ]
        
        for module in modules:
            result = await module.inject_semantic_info(context)
            assert result == context


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_init_semantic_aggregator(self):
        """测试初始化语义聚合器"""
        aggregator = init_semantic_aggregator(max_tokens=2000)
        
        assert isinstance(aggregator, SemanticContextAggregator)
        assert aggregator.max_tokens == 2000
    
    def test_get_semantic_aggregator_after_init(self):
        """测试初始化后获取语义聚合器"""
        # 先初始化
        init_aggregator = init_semantic_aggregator(max_tokens=3000)
        
        # 再获取
        get_aggregator = get_semantic_aggregator()
        
        assert get_aggregator is init_aggregator
        assert get_aggregator.max_tokens == 3000


class TestDataSourceSemanticInfo:
    """数据源语义信息数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        semantic_info = DataSourceSemanticInfo(
            source_id="test_id",
            source_name="Test DB",
            database_type=DatabaseType.MYSQL,
            sql_dialect={"limit": "LIMIT {n}"},
            connection_config={"host": "localhost"},
            performance_characteristics={"batch_size": 1000},
            business_rules=[{"type": "test"}]
        )
        
        result = semantic_info.to_dict()
        
        assert result["source_id"] == "test_id"
        assert result["source_name"] == "Test DB"
        assert result["database_type"] == "mysql"
        assert result["sql_dialect"] == {"limit": "LIMIT {n}"}
        assert result["connection_config"] == {"host": "localhost"}
        assert result["performance_characteristics"] == {"batch_size": 1000}
        assert result["business_rules"] == [{"type": "test"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])