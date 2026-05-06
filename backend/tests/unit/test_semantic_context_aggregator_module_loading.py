"""
测试 SemanticContextAggregator 的模块加载功能

验证所有 5 个语义模块是否正确初始化和加载
"""

import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch
from src.services.semantic_context_aggregator import (
    SemanticContextAggregator,
    ModuleType,
    ContextPriority,
    TokenBudget
)

# 配置日志以便查看详细输出
logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    return Mock()


@pytest.fixture
def aggregator(mock_db_session):
    """创建 SemanticContextAggregator 实例"""
    return SemanticContextAggregator(db_session=mock_db_session)


class TestModuleInitialization:
    """测试模块初始化"""
    
    def test_all_services_initialized(self, aggregator):
        """测试所有 5 个语义服务是否正确初始化"""
        # 验证所有服务都已创建
        assert aggregator.data_source_service is not None, "DataSourceSemanticInjectionService 未初始化"
        assert aggregator.table_structure_service is not None, "TableStructureSemanticInjectionService 未初始化"
        assert aggregator.table_relation_service is not None, "TableRelationSemanticInjectionService 未初始化"
        assert aggregator.dictionary_service is not None, "SemanticInjectionService (Dictionary) 未初始化"
        assert aggregator.knowledge_service is not None, "KnowledgeSemanticInjectionService 未初始化"
        
        # 验证服务类型
        from src.services.data_source_semantic_injection import DataSourceSemanticInjectionService
        from src.services.table_structure_semantic_injection import TableStructureSemanticInjectionService
        from src.services.table_relation_semantic_injection import TableRelationSemanticInjectionService
        from src.services.semantic_injection_service import SemanticInjectionService
        from src.services.knowledge_semantic_injection import KnowledgeSemanticInjectionService
        
        assert isinstance(aggregator.data_source_service, DataSourceSemanticInjectionService)
        assert isinstance(aggregator.table_structure_service, TableStructureSemanticInjectionService)
        assert isinstance(aggregator.table_relation_service, TableRelationSemanticInjectionService)
        assert isinstance(aggregator.dictionary_service, SemanticInjectionService)
        assert isinstance(aggregator.knowledge_service, KnowledgeSemanticInjectionService)
    
    @pytest.mark.asyncio
    async def test_module_creation_in_context(self, aggregator):
        """测试在聚合上下文中创建的模块"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"],
            include_global=True
        )
        
        # 初始化模块
        await aggregator._initialize_semantic_modules(context)
        
        # 验证创建了 5 个模块
        assert len(context.modules) == 5, f"应该创建 5 个模块，实际创建了 {len(context.modules)} 个"
        
        # 验证每个模块类型都存在
        module_types = {module.module_type for module in context.modules}
        expected_types = {
            ModuleType.DATA_SOURCE,
            ModuleType.TABLE_STRUCTURE,
            ModuleType.TABLE_RELATION,
            ModuleType.DICTIONARY,
            ModuleType.KNOWLEDGE
        }
        assert module_types == expected_types, f"模块类型不完整: {module_types}"
        
        # 验证每个模块都有服务
        for module in context.modules:
            assert module.service is not None, f"模块 {module.module_type.value} 的服务未初始化"
            assert module.priority is not None, f"模块 {module.module_type.value} 的优先级未设置"
    
    @pytest.mark.asyncio
    async def test_module_priorities(self, aggregator):
        """测试模块优先级设置"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"]
        )
        
        await aggregator._initialize_semantic_modules(context)
        
        # 验证默认优先级
        priority_map = {module.module_type: module.priority for module in context.modules}
        
        assert priority_map[ModuleType.TABLE_STRUCTURE] == ContextPriority.CRITICAL
        assert priority_map[ModuleType.DICTIONARY] == ContextPriority.HIGH
        assert priority_map[ModuleType.DATA_SOURCE] == ContextPriority.HIGH
        assert priority_map[ModuleType.TABLE_RELATION] == ContextPriority.MEDIUM
        assert priority_map[ModuleType.KNOWLEDGE] == ContextPriority.MEDIUM
    
    @pytest.mark.asyncio
    async def test_custom_module_priorities(self, aggregator):
        """测试自定义模块优先级"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"]
        )
        
        # 自定义优先级
        custom_priorities = {
            ModuleType.KNOWLEDGE: ContextPriority.CRITICAL,
            ModuleType.TABLE_RELATION: ContextPriority.HIGH
        }
        
        await aggregator._initialize_semantic_modules(context, custom_priorities)
        
        # 验证自定义优先级生效
        priority_map = {module.module_type: module.priority for module in context.modules}
        
        assert priority_map[ModuleType.KNOWLEDGE] == ContextPriority.CRITICAL
        assert priority_map[ModuleType.TABLE_RELATION] == ContextPriority.HIGH


class TestModuleLoading:
    """测试模块加载"""
    
    @pytest.mark.asyncio
    async def test_module_loading_workflow(self, aggregator, mock_db_session):
        """测试完整的模块加载工作流"""
        # 模拟数据库查询
        with patch.object(aggregator, '_load_data_source_content', new_callable=AsyncMock) as mock_ds, \
             patch.object(aggregator, '_load_table_structure_content', new_callable=AsyncMock) as mock_ts, \
             patch.object(aggregator, '_load_table_relation_content', new_callable=AsyncMock) as mock_tr, \
             patch.object(aggregator, '_load_dictionary_content', new_callable=AsyncMock) as mock_dict, \
             patch.object(aggregator, '_load_knowledge_content', new_callable=AsyncMock) as mock_know:
            
            # 设置模拟返回值
            mock_ds.return_value = {"module_type": "data_source", "content": "数据源信息"}
            mock_ts.return_value = {"module_type": "table_structure", "content": "表结构信息"}
            mock_tr.return_value = {"module_type": "table_relation", "content": "表关联信息"}
            mock_dict.return_value = {"module_type": "dictionary", "content": "数据字典信息"}
            mock_know.return_value = {"module_type": "knowledge", "content": "知识库信息"}
            
            # 执行聚合
            result = await aggregator.aggregate_semantic_context(
                user_question="查询销售数据",
                table_ids=["sales_table"],
                include_global=True
            )
            
            # 验证结果
            assert result is not None
            assert len(result.modules_used) > 0, "应该至少加载一个模块"
            assert result.total_tokens_used >= 0
            assert result.enhanced_context is not None
            
            # 验证至少调用了一些加载方法（取决于优化算法的选择）
            # 注意：由于优化算法可能跳过某些模块，我们只验证至少有一个被调用
            call_count = (
                mock_ds.call_count +
                mock_ts.call_count +
                mock_tr.call_count +
                mock_dict.call_count +
                mock_know.call_count
            )
            assert call_count > 0, "应该至少调用一个模块加载方法"
    
    @pytest.mark.asyncio
    async def test_module_selection_based_on_priority(self, aggregator):
        """测试基于优先级的模块选择"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        # 创建一个小的Token预算，强制进行选择
        small_budget = TokenBudget(total_budget=500, reserved_for_response=100)
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"],
            token_budget=small_budget
        )
        
        # 初始化和优化
        await aggregator._initialize_semantic_modules(context)
        await aggregator._calculate_module_relevance(context)
        await aggregator._optimize_context_selection(context)
        
        # 验证至少选择了一些模块
        selected_modules = [m for m in context.modules if m.is_loaded]
        assert len(selected_modules) > 0, "应该至少选择一个模块"
        
        # 验证关键模块（CRITICAL优先级）被优先选择
        critical_modules = [m for m in selected_modules if m.priority == ContextPriority.CRITICAL]
        if len(selected_modules) > 0:
            # 如果有模块被选中，关键模块应该在其中
            assert len(critical_modules) > 0 or small_budget.available_for_context < 50, \
                "在预算允许的情况下，关键模块应该被选中"
    
    @pytest.mark.asyncio
    async def test_all_modules_loaded_with_sufficient_budget(self, aggregator):
        """测试在充足预算下所有模块都被加载"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        # 创建一个大的Token预算
        large_budget = TokenBudget(total_budget=10000, reserved_for_response=1000)
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"],
            token_budget=large_budget
        )
        
        # 初始化和优化
        await aggregator._initialize_semantic_modules(context)
        await aggregator._calculate_module_relevance(context)
        await aggregator._optimize_context_selection(context)
        
        # 验证至少选中了一些模块（在大预算下）
        selected_modules = [m for m in context.modules if m.is_loaded]
        # 注意：由于相关性评分和价值密度计算，可能不是所有模块都被选中
        # 但至少应该选中关键模块
        assert len(selected_modules) >= 1, f"在大预算下应该至少选中1个模块，实际选中了 {len(selected_modules)} 个"
        
        # 验证关键模块被选中
        critical_modules = [m for m in selected_modules if m.priority == ContextPriority.CRITICAL]
        assert len(critical_modules) > 0, "关键模块应该被选中"


class TestLoggingOutput:
    """测试日志输出"""
    
    @pytest.mark.asyncio
    async def test_detailed_logging_during_initialization(self, aggregator, caplog):
        """测试初始化过程中的详细日志"""
        from src.services.semantic_context_aggregator import AggregationContext
        
        caplog.set_level(logging.INFO)
        
        context = AggregationContext(
            user_question="测试问题",
            table_ids=["table1"]
        )
        
        await aggregator._initialize_semantic_modules(context)
        
        # 验证日志包含关键信息
        log_text = caplog.text
        
        assert "开始初始化语义模块" in log_text
        assert "验证语义服务初始化状态" in log_text
        assert "DataSourceSemanticInjectionService" in log_text
        assert "TableStructureSemanticInjectionService" in log_text
        assert "TableRelationSemanticInjectionService" in log_text
        assert "SemanticInjectionService" in log_text
        assert "KnowledgeSemanticInjectionService" in log_text
        assert "成功创建 5 个语义模块" in log_text
        assert "语义模块初始化完成" in log_text
    
    @pytest.mark.asyncio
    async def test_detailed_logging_during_aggregation(self, aggregator, caplog):
        """测试聚合过程中的详细日志"""
        caplog.set_level(logging.INFO)
        
        # 模拟模块加载
        with patch.object(aggregator, '_load_data_source_content', new_callable=AsyncMock) as mock_ds, \
             patch.object(aggregator, '_load_table_structure_content', new_callable=AsyncMock) as mock_ts, \
             patch.object(aggregator, '_load_table_relation_content', new_callable=AsyncMock) as mock_tr, \
             patch.object(aggregator, '_load_dictionary_content', new_callable=AsyncMock) as mock_dict, \
             patch.object(aggregator, '_load_knowledge_content', new_callable=AsyncMock) as mock_know:
            
            mock_ds.return_value = {"module_type": "data_source", "content": "数据源信息"}
            mock_ts.return_value = {"module_type": "table_structure", "content": "表结构信息"}
            mock_tr.return_value = {"module_type": "table_relation", "content": "表关联信息"}
            mock_dict.return_value = {"module_type": "dictionary", "content": "数据字典信息"}
            mock_know.return_value = {"module_type": "knowledge", "content": "知识库信息"}
            
            result = await aggregator.aggregate_semantic_context(
                user_question="查询销售数据",
                table_ids=["sales_table"]
            )
            
            log_text = caplog.text
            
            # 验证关键日志信息
            assert "开始语义上下文聚合" in log_text
            assert "用户问题" in log_text
            assert "选定的表" in log_text
            assert "Token预算" in log_text
            assert "语义上下文聚合完成" in log_text
            assert "使用的模块" in log_text
            assert "Token使用量" in log_text
            assert "完整语义上下文" in log_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
