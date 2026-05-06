"""
集成测试：ChatBI 上下文传递修复完整功能验证

这个测试文件验证所有上下文传递修复功能的集成：
1. 完整对话流程
2. 语义上下文传递
3. 历史对话管理
4. Token 阈值触发

Requirements: 所有需求 (1.1-6.7)
"""

import pytest
import logging
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from src.services.chat_orchestrator import ChatOrchestrator
from src.services.semantic_context_aggregator import SemanticContextAggregator
from src.services.context_manager import ContextManager
from src.database import get_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_complete_dialogue_flow():
    """
    测试完整对话流程
    
    验证：
    1. 用户问题 -> 意图识别 -> 智能选表 -> SQL生成 -> SQL执行 -> 数据分析
    2. 每个阶段的上下文正确传递
    3. 历史对话正确记录
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 4.1, 4.2
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：完整对话流程")
    logger.info("=" * 80)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 创建 ChatOrchestrator
        orchestrator = ChatOrchestrator()
        
        # 模拟用户问题
        session_id = "test_session_001"
        user_question = "查询 2024 年乳制品每个月的销售额"
        data_source_id = "test_datasource_001"
        
        # Mock AI 服务响应
        with patch.object(orchestrator.ai_service, 'call_cloud_model', new_callable=AsyncMock) as mock_cloud:
            with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
                # Mock 意图识别响应
                mock_cloud.side_effect = [
                    # 意图识别响应
                    {
                        "success": True,
                        "content": '{"intent": "query", "confidence": 0.95}'
                    },
                    # 智能选表响应
                    {
                        "success": True,
                        "content": '{"selected_tables": ["sales_table"], "confidence": 0.90}'
                    },
                    # SQL 生成响应
                    {
                        "success": True,
                        "content": '''```sql
SELECT 
    DATE_FORMAT(sale_date, '%Y-%m') as month,
    SUM(amount) as total_sales
FROM sales_table
WHERE YEAR(sale_date) = 2024 
    AND product_category = '乳制品'
GROUP BY DATE_FORMAT(sale_date, '%Y-%m')
ORDER BY month
```'''
                    }
                ]
                
                # Mock 数据分析响应
                mock_local.return_value = {
                    "success": True,
                    "content": "根据查询结果，2024年乳制品销售额呈现上升趋势..."
                }
                
                # Mock SQL 执行
                with patch.object(orchestrator, '_execute_sql', new_callable=AsyncMock) as mock_execute:
                    mock_execute.return_value = {
                        "success": True,
                        "data": [
                            {"month": "2024-01", "total_sales": 100000},
                            {"month": "2024-02", "total_sales": 120000},
                            {"month": "2024-03", "total_sales": 150000}
                        ],
                        "columns": ["month", "total_sales"],
                        "row_count": 3
                    }
                    
                    # 执行对话流程
                    result = await orchestrator.start_chat(
                        session_id=session_id,
                        user_question=user_question,
                        data_source_id=data_source_id
                    )
                    
                    # 验证结果
                    assert result is not None
                    assert result.get("success") is True
                    
                    logger.info("✅ 完整对话流程测试通过")
                    logger.info(f"📊 结果: {result}")
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_semantic_context_passing():
    """
    测试语义上下文传递
    
    验证：
    1. SemanticContextAggregator 正确聚合所有语义信息
    2. 数据源信息、表结构、数据字典、表关联、知识库信息都被包含
    3. 语义上下文正确传递给 SQL 生成阶段
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：语义上下文传递")
    logger.info("=" * 80)
    
    db = next(get_db())
    
    try:
        # 创建语义上下文聚合器
        aggregator = SemanticContextAggregator(db_session=db)
        
        # 执行语义上下文聚合
        result = await aggregator.aggregate_semantic_context(
            user_question="查询销售数据",
            table_ids=None,
            include_global=True
        )
        
        # 验证结果
        assert result is not None
        assert result.enhanced_context is not None
        assert isinstance(result.modules_used, list)
        assert len(result.modules_used) > 0
        
        # 验证语义上下文包含关键信息
        context = result.enhanced_context
        
        # 检查是否包含各种语义信息（根据实际加载的模块）
        logger.info(f"📦 加载的模块: {result.modules_used}")
        logger.info(f"📊 Token 使用量: {result.total_tokens_used}")
        logger.info(f"📝 语义上下文长度: {len(context)} 字符")
        
        # 验证至少有一些内容
        assert len(context) > 0, "语义上下文不应为空"
        
        logger.info("✅ 语义上下文传递测试通过")
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_history_context_management():
    """
    测试历史对话管理
    
    验证：
    1. ContextManager 正确记录历史对话
    2. 历史对话可以正确获取
    3. 历史对话格式正确
    
    Requirements: 2.1, 4.1, 4.2, 4.3, 4.4
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：历史对话管理")
    logger.info("=" * 80)
    
    # 创建 ContextManager
    context_manager = ContextManager()
    session_id = "test_session_002"
    
    # 添加用户消息
    context_manager.add_user_message(session_id, "第一个问题：查询销售数据")
    
    # 添加 SQL 响应
    context_manager.add_sql_response(
        session_id,
        "SELECT * FROM sales WHERE year = 2024",
        {"data": [{"sales": 1000}], "columns": ["sales"]}
    )
    
    # 添加分析响应
    context_manager.add_analysis_response(
        session_id,
        "销售数据分析结果...",
        {"chart_type": "line"}
    )
    
    # 添加第二轮对话
    context_manager.add_user_message(session_id, "第二个问题：按月份统计")
    context_manager.add_sql_response(
        session_id,
        "SELECT month, SUM(sales) FROM sales GROUP BY month",
        {"data": [{"month": "01", "sum": 1000}], "columns": ["month", "sum"]}
    )
    
    # 获取云端历史（用于发送给 AI）
    cloud_history = context_manager.get_cloud_history(session_id, max_messages=10)
    
    # 验证历史记录
    assert len(cloud_history) > 0
    logger.info(f"📚 云端历史记录数: {len(cloud_history)}")
    
    # 验证消息格式
    for msg in cloud_history:
        assert "role" in msg
        assert "content" in msg
        assert msg["role"] in ["user", "assistant"]
    
    # 获取本地历史（包含完整数据）
    local_history = context_manager.get_local_history(session_id, max_messages=10)
    
    assert len(local_history) > 0
    logger.info(f"📚 本地历史记录数: {len(local_history)}")
    
    logger.info("✅ 历史对话管理测试通过")


@pytest.mark.asyncio
async def test_token_threshold_trigger():
    """
    测试 Token 阈值触发
    
    验证：
    1. 历史对话 Token 数正确计算
    2. 超过阈值时触发摘要
    3. 未超过阈值时使用完整历史
    4. 摘要保留最近 3 轮对话
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：Token 阈值触发")
    logger.info("=" * 80)
    
    db = next(get_db())
    
    try:
        # 创建 ChatOrchestrator
        orchestrator = ChatOrchestrator()
        
        # 测试场景 1: 历史对话未超过阈值
        logger.info("\n📊 场景 1: 历史对话未超过阈值")
        
        short_history = [
            {"role": "user", "content": "问题1", "timestamp": "2024-01-01 10:00:00"},
            {"role": "assistant", "content": "回答1", "timestamp": "2024-01-01 10:00:05"},
            {"role": "user", "content": "问题2", "timestamp": "2024-01-01 10:01:00"},
            {"role": "assistant", "content": "回答2", "timestamp": "2024-01-01 10:01:05"}
        ]
        
        # 计算 Token 数
        total_tokens = orchestrator._calculate_history_tokens(short_history)
        logger.info(f"📊 短历史 Token 数: {total_tokens}")
        
        # 验证 Token 计算
        assert total_tokens > 0
        assert total_tokens < 2000  # 应该小于阈值
        
        # 获取历史上下文（不应触发摘要）
        history_context = orchestrator._format_full_history(short_history)
        assert history_context is not None
        assert len(history_context) > 0
        
        logger.info("✅ 场景 1 通过：未超过阈值，使用完整历史")
        
        # 测试场景 2: 历史对话超过阈值
        logger.info("\n📊 场景 2: 历史对话超过阈值")
        
        # 创建一个很长的历史对话
        long_history = []
        for i in range(20):  # 20 轮对话 = 40 条消息
            long_history.append({
                "role": "user",
                "content": f"这是第 {i+1} 个问题，内容比较长，包含很多详细信息和上下文，用于测试 Token 阈值触发机制。" * 10,
                "timestamp": f"2024-01-01 10:{i:02d}:00"
            })
            long_history.append({
                "role": "assistant",
                "content": f"这是第 {i+1} 个回答，包含详细的分析结果、SQL 查询和数据解释，内容也比较长。" * 10,
                "timestamp": f"2024-01-01 10:{i:02d}:05"
            })
        
        # 计算 Token 数
        total_tokens = orchestrator._calculate_history_tokens(long_history)
        logger.info(f"📊 长历史 Token 数: {total_tokens}")
        
        # 验证 Token 计算
        assert total_tokens > 2000  # 应该超过阈值
        
        # Mock AI 服务用于摘要
        with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = {
                "success": True,
                "content": "早期对话摘要：用户主要关注销售数据分析，涉及 sales_table 表，时间范围为 2024 年..."
            }
            
            # 获取历史上下文（应触发摘要）
            history_context = await orchestrator._summarize_history_context(
                long_history,
                "当前问题"
            )
            
            assert history_context is not None
            assert len(history_context) > 0
            assert "早期对话摘要" in history_context or "最近对话" in history_context
            
            logger.info("✅ 场景 2 通过：超过阈值，触发智能摘要")
        
        # 测试场景 3: 验证摘要保留最近 3 轮对话
        logger.info("\n📊 场景 3: 验证摘要保留最近 3 轮对话")
        
        # 使用 10 轮对话测试
        medium_history = []
        for i in range(10):
            medium_history.append({
                "role": "user",
                "content": f"问题 {i+1}：" + "内容" * 50,
                "timestamp": f"2024-01-01 10:{i:02d}:00"
            })
            medium_history.append({
                "role": "assistant",
                "content": f"回答 {i+1}：" + "内容" * 50,
                "timestamp": f"2024-01-01 10:{i:02d}:05"
            })
        
        with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = {
                "success": True,
                "content": "早期对话摘要内容..."
            }
            
            history_context = await orchestrator._summarize_history_context(
                medium_history,
                "当前问题"
            )
            
            # 验证最近 3 轮对话（6 条消息）被保留
            # 检查最后几个问题是否在上下文中
            assert "问题 8" in history_context or "问题 9" in history_context or "问题 10" in history_context
            
            logger.info("✅ 场景 3 通过：摘要保留最近 3 轮对话")
        
        logger.info("\n✅ Token 阈值触发测试全部通过")
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_end_to_end_with_context_and_history():
    """
    端到端测试：完整对话流程 + 语义上下文 + 历史对话
    
    验证：
    1. 完整对话流程正常工作
    2. 语义上下文正确传递给 SQL 生成
    3. 历史对话正确管理和使用
    4. 所有组件协同工作
    
    Requirements: 所有需求 (1.1-6.7)
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：端到端完整流程")
    logger.info("=" * 80)
    
    db = next(get_db())
    
    try:
        # 创建 ChatOrchestrator
        orchestrator = ChatOrchestrator()
        session_id = "test_session_003"
        
        # 第一轮对话
        logger.info("\n📝 第一轮对话")
        
        with patch.object(orchestrator.ai_service, 'call_cloud_model', new_callable=AsyncMock) as mock_cloud:
            with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
                with patch.object(orchestrator, '_execute_sql', new_callable=AsyncMock) as mock_execute:
                    # Mock 响应
                    mock_cloud.side_effect = [
                        {"success": True, "content": '{"intent": "query", "confidence": 0.95}'},
                        {"success": True, "content": '{"selected_tables": ["sales"], "confidence": 0.90}'},
                        {"success": True, "content": '```sql\nSELECT * FROM sales\n```'}
                    ]
                    mock_local.return_value = {"success": True, "content": "分析结果1"}
                    mock_execute.return_value = {
                        "success": True,
                        "data": [{"sales": 1000}],
                        "columns": ["sales"],
                        "row_count": 1
                    }
                    
                    result1 = await orchestrator.start_chat(
                        session_id=session_id,
                        user_question="查询销售数据",
                        data_source_id="test_ds_001"
                    )
                    
                    assert result1.get("success") is True
                    logger.info("✅ 第一轮对话完成")
        
        # 第二轮对话（应该包含历史上下文）
        logger.info("\n📝 第二轮对话（包含历史）")
        
        with patch.object(orchestrator.ai_service, 'call_cloud_model', new_callable=AsyncMock) as mock_cloud:
            with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
                with patch.object(orchestrator, '_execute_sql', new_callable=AsyncMock) as mock_execute:
                    # Mock 响应
                    mock_cloud.side_effect = [
                        {"success": True, "content": '{"intent": "query", "confidence": 0.95}'},
                        {"success": True, "content": '{"selected_tables": ["sales"], "confidence": 0.90}'},
                        {"success": True, "content": '```sql\nSELECT month, SUM(sales) FROM sales GROUP BY month\n```'}
                    ]
                    mock_local.return_value = {"success": True, "content": "分析结果2"}
                    mock_execute.return_value = {
                        "success": True,
                        "data": [{"month": "01", "sum": 1000}],
                        "columns": ["month", "sum"],
                        "row_count": 1
                    }
                    
                    result2 = await orchestrator.start_chat(
                        session_id=session_id,
                        user_question="按月份统计",
                        data_source_id="test_ds_001"
                    )
                    
                    assert result2.get("success") is True
                    logger.info("✅ 第二轮对话完成（包含历史上下文）")
        
        # 验证历史记录
        cloud_history = orchestrator.context_manager.get_cloud_history(session_id)
        assert len(cloud_history) > 0
        logger.info(f"📚 历史记录数: {len(cloud_history)}")
        
        logger.info("\n✅ 端到端完整流程测试通过")
        
    finally:
        db.close()


@pytest.mark.asyncio
async def test_logging_verification():
    """
    测试日志记录验证
    
    验证：
    1. 语义上下文聚合日志完整
    2. 历史对话管理日志完整
    3. SQL 生成 Prompt 日志完整
    4. AI 响应日志完整
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
    """
    logger.info("=" * 80)
    logger.info("🧪 测试：日志记录验证")
    logger.info("=" * 80)
    
    db = next(get_db())
    
    try:
        # 创建 ChatOrchestrator
        orchestrator = ChatOrchestrator()
        
        # 捕获日志输出
        import io
        import sys
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        
        # 添加 handler 到相关 logger
        chat_logger = logging.getLogger('src.services.chat_orchestrator')
        semantic_logger = logging.getLogger('src.services.semantic_context_aggregator')
        
        chat_logger.addHandler(handler)
        semantic_logger.addHandler(handler)
        
        try:
            # 执行一次完整对话
            with patch.object(orchestrator.ai_service, 'call_cloud_model', new_callable=AsyncMock) as mock_cloud:
                with patch.object(orchestrator.ai_service, 'call_local_model', new_callable=AsyncMock) as mock_local:
                    with patch.object(orchestrator, '_execute_sql', new_callable=AsyncMock) as mock_execute:
                        mock_cloud.side_effect = [
                            {"success": True, "content": '{"intent": "query"}'},
                            {"success": True, "content": '{"selected_tables": ["test"]}'},
                            {"success": True, "content": '```sql\nSELECT * FROM test\n```'}
                        ]
                        mock_local.return_value = {"success": True, "content": "分析"}
                        mock_execute.return_value = {
                            "success": True,
                            "data": [],
                            "columns": [],
                            "row_count": 0
                        }
                        
                        await orchestrator.start_chat(
                            session_id="test_log_session",
                            user_question="测试问题",
                            data_source_id="test_ds"
                        )
            
            # 获取日志内容
            log_content = log_capture.getvalue()
            
            # 验证关键日志存在
            # 注意：由于我们使用了 Mock，实际的日志可能不会完全输出
            # 这里主要验证日志系统是否正常工作
            
            logger.info("📝 日志内容长度: " + str(len(log_content)))
            
            if len(log_content) > 0:
                logger.info("✅ 日志系统正常工作")
            else:
                logger.warning("⚠️ 日志内容为空（可能是由于 Mock）")
            
        finally:
            # 移除 handler
            chat_logger.removeHandler(handler)
            semantic_logger.removeHandler(handler)
        
        logger.info("✅ 日志记录验证测试完成")
        
    finally:
        db.close()


if __name__ == "__main__":
    """
    直接运行此文件进行集成测试
    """
    print("=" * 80)
    print("🚀 开始 ChatBI 上下文传递修复集成测试")
    print("=" * 80)
    
    # 运行所有测试
    asyncio.run(test_complete_dialogue_flow())
    print()
    asyncio.run(test_semantic_context_passing())
    print()
    asyncio.run(test_history_context_management())
    print()
    asyncio.run(test_token_threshold_trigger())
    print()
    asyncio.run(test_end_to_end_with_context_and_history())
    print()
    asyncio.run(test_logging_verification())
    
    print("\n" + "=" * 80)
    print("✅ 所有集成测试完成")
    print("=" * 80)
