"""
语义上下文聚合引擎服务测试

测试语义上下文聚合引擎的核心功能：五模块元数据智能聚合、相关性评分、
动态上下文裁剪、按需加载、Token使用量精确控制和预算管理。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.services.semantic_context_aggregator import (
    SemanticContextAggregator,
    TokenBudget,
    ModuleType,
    ContextPriority,
    SemanticModule,
    AggregationContext,
    AggregationResult
)


class TestSemanticContextAggregator:
    """语义上下文聚合引擎测试类"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock()
    
    @pytest.fixture
    def aggregator(self, mock_db_session):
        """创建聚合引擎实例"""
        return SemanticContextAggregator(mock_db_session)
    
    @pytest.fixture
    def sample_token_budget(self):
        """示例Token预算"""
        return TokenBudget(total_budget=2000, reserved_for_response=500)
    
    @pytest.fixture
    def sample_module_priorities(self):
        """示例模块优先级"""
        return {
            ModuleType.TABLE_STRUCTURE: ContextPriority.CRITICAL,
            ModuleType.DICTIONARY: ContextPriority.HIGH,
            ModuleType.DATA_SOURCE: ContextPriority.MEDIUM,
            ModuleType.TABLE_RELATION: ContextPriority.LOW,
            ModuleType.KNOWLEDGE: ContextPriority.LOW
        }
    
    @pytest.mark.asyncio
    async def test_aggregate_semantic_context_basic(self, aggregator):
        """测试基础语义上下文聚合"""
        # 准备测试数据
        user_question = "查询用户订单信息"
        table_ids = ["users", "orders"]
        
        # 执行聚合
        result = await aggregator.aggregate_semantic_context(
            user_question=user_question,
            table_ids=table_ids
        )
        
        # 验证结果
        assert isinstance(result, AggregationResult)
        assert result.enhanced_context is not None
        assert len(result.enhanced_context) > 0
        assert isinstance(result.modules_used, list)
        assert isinstance(result.total_tokens_used, int)
        assert result.total_tokens_used >= 0
        assert isinstance(result.relevance_scores, dict)
        assert isinstance(result.optimization_summary, dict)
    
    @pytest.mark.asyncio
    async def test_aggregate_with_custom_token_budget(self, aggregator, sample_token_budget):
        """测试自定义Token预算的聚合"""
        user_question = "分析销售数据"
        
        result = await aggregator.aggregate_semantic_context(
            user_question=user_question,
            token_budget=sample_token_budget
        )
        
        # 验证Token预算控制
        assert result.total_tokens_used <= sample_token_budget.available_for_context
        assert result.token_budget_remaining >= 0
        assert result.token_budget_remaining == sample_token_budget.available_for_context - result.total_tokens_used
    
    @pytest.mark.asyncio
    async def test_aggregate_with_module_priorities(self, aggregator, sample_module_priorities):
        """测试自定义模块优先级的聚合"""
        user_question = "查询产品信息"
        table_ids = ["products"]
        
        result = await aggregator.aggregate_semantic_context(
            user_question=user_question,
            table_ids=table_ids,
            module_priorities=sample_module_priorities
        )
        
        # 验证优先级影响
        assert isinstance(result, AggregationResult)
        assert len(result.modules_used) > 0
        
        # 关键模块应该被包含
        assert any("table_structure" in module for module in result.modules_used) or \
               any("dictionary" in module for module in result.modules_used)
    
    @pytest.mark.asyncio
    async def test_initialize_semantic_modules(self, aggregator):
        """测试语义模块初始化"""
        context = AggregationContext(user_question="测试问题")
        
        await aggregator._initialize_semantic_modules(context)
        
        # 验证模块初始化
        assert len(context.modules) == 5  # 五个语义模块
        
        module_types = {module.module_type for module in context.modules}
        expected_types = {
            ModuleType.DATA_SOURCE,
            ModuleType.TABLE_STRUCTURE,
            ModuleType.TABLE_RELATION,
            ModuleType.DICTIONARY,
            ModuleType.KNOWLEDGE
        }
        assert module_types == expected_types
        
        # 验证每个模块都有服务实例
        for module in context.modules:
            assert module.service is not None
            assert isinstance(module.priority, ContextPriority)
    
    @pytest.mark.asyncio
    async def test_calculate_module_relevance(self, aggregator):
        """测试模块相关性计算"""
        context = AggregationContext(
            user_question="查询用户表的字段信息",
            table_ids=["users"]
        )
        
        # 初始化模块
        await aggregator._initialize_semantic_modules(context)
        
        # 计算相关性
        await aggregator._calculate_module_relevance(context)
        
        # 验证相关性评分
        for module in context.modules:
            assert 0.0 <= module.relevance_score <= 1.0
            assert module.estimated_tokens > 0
        
        # 表结构模块应该有较高的相关性（因为问题中包含"字段"）
        table_structure_module = next(
            (m for m in context.modules if m.module_type == ModuleType.TABLE_STRUCTURE),
            None
        )
        assert table_structure_module is not None
        assert table_structure_module.relevance_score > 0.5
    
    @pytest.mark.asyncio
    async def test_optimize_context_selection(self, aggregator):
        """测试动态上下文裁剪和优化"""
        context = AggregationContext(
            user_question="测试问题",
            token_budget=TokenBudget(total_budget=1000, reserved_for_response=200)
        )
        
        # 初始化和计算相关性
        await aggregator._initialize_semantic_modules(context)
        await aggregator._calculate_module_relevance(context)
        
        # 执行优化
        await aggregator._optimize_context_selection(context)
        
        # 验证优化结果
        selected_modules = [m for m in context.modules if m.is_loaded]
        total_estimated_tokens = sum(m.estimated_tokens for m in selected_modules)
        
        # 应该在预算范围内
        assert total_estimated_tokens <= context.token_budget.available_for_context
        
        # 关键模块应该被选中
        critical_modules = [m for m in selected_modules if m.priority == ContextPriority.CRITICAL]
        assert len(critical_modules) > 0
    
    @pytest.mark.asyncio
    async def test_load_selected_modules(self, aggregator):
        """测试按需加载选中的模块"""
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["test_table"]
        )
        
        # 初始化模块并选择一些模块
        await aggregator._initialize_semantic_modules(context)
        context.modules[0].is_loaded = True  # 选择第一个模块
        context.modules[1].is_loaded = True  # 选择第二个模块
        
        # 加载模块
        await aggregator._load_selected_modules(context)
        
        # 验证加载结果
        loaded_modules = [m for m in context.modules if m.is_loaded]
        assert len(loaded_modules) == 2
        
        for module in loaded_modules:
            assert module.content is not None
            assert isinstance(module.content, dict)
        
        # 验证聚合内容
        assert len(context.aggregated_content) == 2
        assert context.total_tokens_used > 0
    
    @pytest.mark.asyncio
    async def test_generate_aggregated_context(self, aggregator):
        """测试生成最终聚合上下文"""
        context = AggregationContext(user_question="测试问题")
        
        # 准备测试数据
        await aggregator._initialize_semantic_modules(context)
        context.modules[0].is_loaded = True
        context.modules[0].content = {"content": "测试内容1"}
        context.modules[1].is_loaded = True
        context.modules[1].content = {"content": "测试内容2"}
        
        # 生成聚合上下文
        enhanced_context = await aggregator._generate_aggregated_context(context)
        
        # 验证结果
        assert isinstance(enhanced_context, str)
        assert "测试问题" in enhanced_context
        assert "测试内容1" in enhanced_context or "测试内容2" in enhanced_context
    
    def test_extract_keywords(self, aggregator):
        """测试关键词提取"""
        text = "查询用户表的字段信息和业务含义"
        keywords = aggregator._extract_keywords(text)
        
        assert isinstance(keywords, set)
        assert len(keywords) > 0
        assert "查询" in keywords
        assert "用户" in keywords
        assert "字段" in keywords
        assert "业务" in keywords
        
        # 停用词应该被过滤
        assert "的" not in keywords
        assert "和" not in keywords
    
    def test_get_priority_weight(self, aggregator):
        """测试优先级权重获取"""
        assert aggregator._get_priority_weight(ContextPriority.CRITICAL) == 4
        assert aggregator._get_priority_weight(ContextPriority.HIGH) == 3
        assert aggregator._get_priority_weight(ContextPriority.MEDIUM) == 2
        assert aggregator._get_priority_weight(ContextPriority.LOW) == 1
    
    def test_estimate_module_tokens(self, aggregator):
        """测试模块Token使用量估算"""
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1", "table2"]
        )
        
        # 测试表结构模块
        table_module = SemanticModule(
            module_type=ModuleType.TABLE_STRUCTURE,
            service=Mock(),
            priority=ContextPriority.HIGH
        )
        
        tokens = aggregator._estimate_module_tokens(table_module, context)
        assert tokens > 0
        assert tokens >= 300  # 基础Token + 表数量 * 每表Token
        
        # 测试知识库模块
        knowledge_module = SemanticModule(
            module_type=ModuleType.KNOWLEDGE,
            service=Mock(),
            priority=ContextPriority.MEDIUM
        )
        
        tokens = aggregator._estimate_module_tokens(knowledge_module, context)
        assert tokens > 0
        assert tokens >= 300  # 基础Token
    
    def test_calculate_actual_tokens(self, aggregator):
        """测试实际Token使用量计算"""
        content = {
            "module_type": "test",
            "content": "这是一个测试内容",
            "data": {"key": "value"}
        }
        
        tokens = aggregator._calculate_actual_tokens(content)
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_generate_optimization_summary(self, aggregator):
        """测试优化摘要生成"""
        context = AggregationContext(
            user_question="测试问题",
            token_budget=TokenBudget(total_budget=2000, reserved_for_response=500)
        )
        
        # 准备测试数据
        context.modules = [
            SemanticModule(ModuleType.DATA_SOURCE, Mock(), ContextPriority.HIGH),
            SemanticModule(ModuleType.TABLE_STRUCTURE, Mock(), ContextPriority.CRITICAL),
        ]
        context.modules[0].is_loaded = True
        context.modules[0].relevance_score = 0.8
        context.modules[1].is_loaded = True
        context.modules[1].relevance_score = 0.9
        context.total_tokens_used = 800
        
        summary = aggregator._generate_optimization_summary(context)
        
        # 验证摘要内容
        assert isinstance(summary, dict)
        assert "total_modules_available" in summary
        assert "modules_selected" in summary
        assert "token_budget_used" in summary
        assert "token_budget_total" in summary
        assert "token_utilization_rate" in summary
        assert "modules_by_priority" in summary
        assert "average_relevance_score" in summary
        
        assert summary["total_modules_available"] == 2
        assert summary["modules_selected"] == 2
        assert summary["token_budget_used"] == 800
        assert summary["token_budget_total"] == 1500
        assert 0.0 <= summary["token_utilization_rate"] <= 1.0
        assert 0.0 <= summary["average_relevance_score"] <= 1.0
    
    def test_clear_cache(self, aggregator):
        """测试缓存清空"""
        # 添加一些缓存数据
        aggregator.context_cache["test_key"] = Mock()
        aggregator.relevance_cache["test_key"] = {"score": 0.5}
        
        # 清空缓存
        aggregator.clear_cache()
        
        # 验证缓存已清空
        assert len(aggregator.context_cache) == 0
        assert len(aggregator.relevance_cache) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, aggregator):
        """测试错误处理"""
        # 测试异常情况下的处理
        with patch.object(aggregator, '_initialize_semantic_modules', side_effect=Exception("测试异常")):
            result = await aggregator.aggregate_semantic_context("测试问题")
            
            # 应该返回基础上下文而不是抛出异常
            assert isinstance(result, AggregationResult)
            assert "测试问题" in result.enhanced_context
            assert result.total_tokens_used == 0
            assert "error" in result.optimization_summary
    
    @pytest.mark.asyncio
    async def test_module_loading_with_different_types(self, aggregator):
        """测试不同类型模块的加载"""
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["test_table"]
        )
        
        # 测试每种模块类型的加载
        for module_type in ModuleType:
            module = SemanticModule(
                module_type=module_type,
                service=Mock(),
                priority=ContextPriority.MEDIUM
            )
            module.is_loaded = True
            context.modules = [module]
            
            await aggregator._load_selected_modules(context)
            
            assert module.content is not None
            assert isinstance(module.content, dict)
    
    @pytest.mark.asyncio
    async def test_relevance_calculation_with_keywords(self, aggregator):
        """测试基于关键词的相关性计算"""
        # 测试包含表结构关键词的问题
        context = AggregationContext(
            user_question="查询表结构和字段信息",
            table_ids=["test_table"]
        )
        
        await aggregator._initialize_semantic_modules(context)
        await aggregator._calculate_module_relevance(context)
        
        # 表结构模块应该有更高的相关性
        table_structure_module = next(
            (m for m in context.modules if m.module_type == ModuleType.TABLE_STRUCTURE),
            None
        )
        dictionary_module = next(
            (m for m in context.modules if m.module_type == ModuleType.DICTIONARY),
            None
        )
        
        assert table_structure_module.relevance_score >= dictionary_module.relevance_score
    
    @pytest.mark.asyncio
    async def test_token_budget_constraints(self, aggregator):
        """测试Token预算约束"""
        # 设置很小的Token预算
        small_budget = TokenBudget(total_budget=500, reserved_for_response=200)
        
        context = AggregationContext(
            user_question="复杂的查询问题需要大量上下文",
            table_ids=["table1", "table2", "table3"],
            token_budget=small_budget
        )
        
        await aggregator._initialize_semantic_modules(context)
        await aggregator._calculate_module_relevance(context)
        await aggregator._optimize_context_selection(context)
        
        # 验证选中的模块不会超出预算
        selected_modules = [m for m in context.modules if m.is_loaded]
        total_estimated_tokens = sum(m.estimated_tokens for m in selected_modules)
        
        assert total_estimated_tokens <= small_budget.available_for_context
        
        # 在预算极小的情况下，可能没有模块被选中，这是合理的
        # 但如果有模块被选中，应该优先选择高优先级的模块
        if selected_modules:
            # 验证选中的模块按优先级排序
            priorities = [aggregator._get_priority_weight(m.priority) for m in selected_modules]
            assert priorities == sorted(priorities, reverse=True)
        
        # 验证系统能够处理极端预算约束而不崩溃
        assert isinstance(selected_modules, list)
        assert total_estimated_tokens >= 0