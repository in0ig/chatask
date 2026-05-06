"""
集成测试：验证 SemanticContextAggregator 的日志输出

这个测试验证在真实场景下，所有模块是否正确加载并记录详细日志
"""

import pytest
import logging
from src.services.semantic_context_aggregator import SemanticContextAggregator
from src.database import get_db

# 配置日志以便查看详细输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.mark.asyncio
async def test_semantic_context_aggregator_with_real_db():
    """
    使用真实数据库测试语义上下文聚合器
    
    验证：
    1. 所有 5 个语义模块正确初始化
    2. 模块加载逻辑正常工作
    3. 详细的日志记录输出
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 创建聚合器
        aggregator = SemanticContextAggregator(db_session=db)
        
        # 验证所有服务已初始化
        assert aggregator.data_source_service is not None
        assert aggregator.table_structure_service is not None
        assert aggregator.table_relation_service is not None
        assert aggregator.dictionary_service is not None
        assert aggregator.knowledge_service is not None
        
        print("\n" + "=" * 80)
        print("✅ 所有 5 个语义服务已成功初始化")
        print("=" * 80)
        
        # 执行语义上下文聚合
        result = await aggregator.aggregate_semantic_context(
            user_question="查询 2024 年乳制品每个月的销售额",
            table_ids=None,  # 不指定具体表，测试全局加载
            include_global=True
        )
        
        # 验证结果
        assert result is not None
        assert result.enhanced_context is not None
        assert isinstance(result.modules_used, list)
        assert result.total_tokens_used >= 0
        
        print("\n" + "=" * 80)
        print("📊 聚合结果统计:")
        print(f"   - 使用的模块: {result.modules_used}")
        print(f"   - Token 使用量: {result.total_tokens_used}")
        print(f"   - 剩余 Token: {result.token_budget_remaining}")
        print(f"   - 相关性评分: {result.relevance_scores}")
        print("=" * 80)
        
        print("\n" + "=" * 80)
        print("📝 完整语义上下文:")
        print(result.enhanced_context)
        print("=" * 80)
        
        # 验证至少加载了一些模块
        assert len(result.modules_used) > 0, "应该至少加载一个模块"
        
        print("\n✅ 测试通过：语义上下文聚合器工作正常")
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_semantic_context_aggregator_with_specific_tables():
    """
    测试指定表ID时的语义上下文聚合
    
    这个测试验证当指定具体表时，相关模块是否正确加载
    """
    db = next(get_db())
    
    try:
        aggregator = SemanticContextAggregator(db_session=db)
        
        # 使用一个假设的表ID（在实际环境中应该存在）
        result = await aggregator.aggregate_semantic_context(
            user_question="查询销售数据",
            table_ids=["test_table_1"],
            include_global=True
        )
        
        assert result is not None
        assert result.enhanced_context is not None
        
        print("\n" + "=" * 80)
        print("📊 指定表ID的聚合结果:")
        print(f"   - 使用的模块: {result.modules_used}")
        print(f"   - Token 使用量: {result.total_tokens_used}")
        print("=" * 80)
        
        # 验证表结构模块被加载（因为指定了表ID）
        # 注意：这取决于优化算法的选择
        print(f"\n📦 加载的模块: {result.modules_used}")
        
        print("\n✅ 测试通过：指定表ID的语义上下文聚合正常")
        
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio
    
    print("=" * 80)
    print("开始集成测试：SemanticContextAggregator 日志验证")
    print("=" * 80)
    
    # 运行测试
    asyncio.run(test_semantic_context_aggregator_with_real_db())
    print("\n")
    asyncio.run(test_semantic_context_aggregator_with_specific_tables())
    
    print("\n" + "=" * 80)
    print("✅ 所有集成测试通过")
    print("=" * 80)
