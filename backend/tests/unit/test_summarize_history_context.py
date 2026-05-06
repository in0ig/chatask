"""
测试智能对话摘要功能
验证 _summarize_history_context 方法的正确性
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.chat_orchestrator import ChatOrchestrator


@pytest.fixture
def orchestrator():
    """创建 ChatOrchestrator 实例"""
    with patch('src.services.chat_orchestrator.get_ai_service'):
        with patch('src.services.chat_orchestrator.get_websocket_stream_service'):
            orchestrator = ChatOrchestrator()
            return orchestrator


@pytest.mark.asyncio
async def test_summarize_history_context_short_history(orchestrator):
    """测试短历史对话（不超过6条消息）- 应返回完整对话"""
    # 准备测试数据：4条消息（2轮对话）
    history_messages = [
        {"role": "user", "content": "查询2023年销售额"},
        {"role": "assistant", "content": "好的，我来查询2023年的销售额"},
        {"role": "user", "content": "按月份分组"},
        {"role": "assistant", "content": "已按月份分组显示"}
    ]
    
    current_question = "显示图表"
    
    # 执行摘要
    result = await orchestrator._summarize_history_context(history_messages, current_question)
    
    # 验证结果
    assert "历史对话上下文（完整对话）" in result
    assert "查询2023年销售额" in result
    assert "按月份分组" in result
    assert len(history_messages) == 4  # 确保原始数据未被修改


@pytest.mark.asyncio
async def test_summarize_history_context_long_history_success(orchestrator):
    """测试长历史对话（超过6条消息）- 应进行摘要"""
    # 准备测试数据：10条消息（5轮对话）
    history_messages = [
        {"role": "user", "content": "查询2023年1月销售额"},
        {"role": "assistant", "content": "2023年1月销售额为100万"},
        {"role": "user", "content": "查询2023年2月销售额"},
        {"role": "assistant", "content": "2023年2月销售额为120万"},
        {"role": "user", "content": "查询2023年3月销售额"},
        {"role": "assistant", "content": "2023年3月销售额为150万"},
        {"role": "user", "content": "查询2023年4月销售额"},
        {"role": "assistant", "content": "2023年4月销售额为180万"},
        {"role": "user", "content": "查询2023年5月销售额"},
        {"role": "assistant", "content": "2023年5月销售额为200万"}
    ]
    
    current_question = "对比前5个月的销售趋势"
    
    # Mock AI 服务的摘要响应
    orchestrator.ai_service.call_local_model = AsyncMock(return_value={
        "success": True,
        "content": "用户查询了2023年1-5月的销售额数据，涉及表：sales，字段：month, amount。时间范围：2023年1月至5月。"
    })
    
    # 执行摘要
    result = await orchestrator._summarize_history_context(history_messages, current_question)
    
    # 验证结果
    assert "历史对话上下文" in result
    assert "早期对话摘要" in result
    assert "最近对话（最近3轮）" in result
    
    # 验证最近3轮对话（6条消息）被完整保留
    assert "查询2023年3月销售额" in result
    assert "查询2023年4月销售额" in result
    assert "查询2023年5月销售额" in result
    
    # 验证 AI 服务被调用
    orchestrator.ai_service.call_local_model.assert_called_once()
    call_args = orchestrator.ai_service.call_local_model.call_args
    assert "早期历史对话" in call_args[0][0]
    assert current_question in call_args[0][0]


@pytest.mark.asyncio
async def test_summarize_history_context_long_history_ai_failure(orchestrator):
    """测试长历史对话 - AI摘要失败时的降级策略"""
    # 准备测试数据：10条消息
    history_messages = [
        {"role": "user", "content": "查询2023年1月销售额"},
        {"role": "assistant", "content": "2023年1月销售额为100万"},
        {"role": "user", "content": "查询2023年2月销售额"},
        {"role": "assistant", "content": "2023年2月销售额为120万"},
        {"role": "user", "content": "查询2023年3月销售额"},
        {"role": "assistant", "content": "2023年3月销售额为150万"},
        {"role": "user", "content": "查询2023年4月销售额"},
        {"role": "assistant", "content": "2023年4月销售额为180万"},
        {"role": "user", "content": "查询2023年5月销售额"},
        {"role": "assistant", "content": "2023年5月销售额为200万"}
    ]
    
    current_question = "对比前5个月的销售趋势"
    
    # Mock AI 服务摘要失败
    orchestrator.ai_service.call_local_model = AsyncMock(return_value={
        "success": False,
        "error": "AI服务不可用"
    })
    
    # 执行摘要
    result = await orchestrator._summarize_history_context(history_messages, current_question)
    
    # 验证降级策略：使用简化的早期对话
    assert "历史对话上下文" in result
    assert "早期对话摘要" in result
    assert "最近对话（最近3轮）" in result
    
    # 验证最近3轮对话仍然被完整保留
    assert "查询2023年3月销售额" in result
    assert "查询2023年4月销售额" in result
    assert "查询2023年5月销售额" in result


@pytest.mark.asyncio
async def test_summarize_history_context_preserves_key_info(orchestrator):
    """测试摘要保留关键信息（表名、字段名、时间范围）"""
    # 准备测试数据：包含关键信息的历史对话
    history_messages = [
        {"role": "user", "content": "查询 orders 表中 2023年1月 的 total_amount 字段"},
        {"role": "assistant", "content": "已查询 orders 表，2023年1月的 total_amount 总计为100万"},
        {"role": "user", "content": "再查询 customers 表中 customer_name 字段"},
        {"role": "assistant", "content": "已查询 customers 表的 customer_name 字段"},
        {"role": "user", "content": "关联 orders 和 customers 表"},
        {"role": "assistant", "content": "已通过 customer_id 关联两个表"},
        {"role": "user", "content": "筛选 total_amount > 1000 的记录"},
        {"role": "assistant", "content": "已筛选 total_amount > 1000 的记录"},
        {"role": "user", "content": "按 customer_name 分组"},
        {"role": "assistant", "content": "已按 customer_name 分组显示"}
    ]
    
    current_question = "显示图表"
    
    # Mock AI 服务返回包含关键信息的摘要
    orchestrator.ai_service.call_local_model = AsyncMock(return_value={
        "success": True,
        "content": "用户查询了 orders 表和 customers 表，关注字段：total_amount, customer_name, customer_id。时间范围：2023年1月。筛选条件：total_amount > 1000。分组字段：customer_name。"
    })
    
    # 执行摘要
    result = await orchestrator._summarize_history_context(history_messages, current_question)
    
    # 验证摘要中包含关键信息
    assert "orders" in result or "表" in result
    assert "customers" in result or "表" in result
    
    # 验证 AI 被调用时的 prompt 包含关键信息提取要求
    orchestrator.ai_service.call_local_model.assert_called_once()
    call_args = orchestrator.ai_service.call_local_model.call_args
    prompt = call_args[0][0]
    assert "表名称和字段名称" in prompt
    assert "时间范围、筛选条件" in prompt
    assert "必须保留原始名称" in prompt


@pytest.mark.asyncio
async def test_format_messages_for_summary_truncates_long_content(orchestrator):
    """测试 _format_messages_for_summary 截断过长内容"""
    # 准备测试数据：包含超长内容的消息
    long_content = "这是一个非常长的内容" * 100  # 超过500字符
    messages = [
        {"role": "user", "content": long_content},
        {"role": "assistant", "content": "短内容"}
    ]
    
    # 执行格式化
    result = orchestrator._format_messages_for_summary(messages)
    
    # 验证长内容被截断
    assert "..." in result
    assert len(result) < len(long_content) + 100  # 确保被截断
    
    # 验证短内容未被截断
    assert "短内容" in result
    assert result.count("短内容") == 1


@pytest.mark.asyncio
async def test_summarize_history_context_exception_handling(orchestrator):
    """测试摘要过程中的异常处理"""
    # 准备测试数据
    history_messages = [
        {"role": "user", "content": "消息1"},
        {"role": "assistant", "content": "消息2"},
        {"role": "user", "content": "消息3"},
        {"role": "assistant", "content": "消息4"},
        {"role": "user", "content": "消息5"},
        {"role": "assistant", "content": "消息6"},
        {"role": "user", "content": "消息7"},
        {"role": "assistant", "content": "消息8"}
    ]
    
    current_question = "测试问题"
    
    # Mock AI 服务抛出异常
    orchestrator.ai_service.call_local_model = AsyncMock(side_effect=Exception("网络错误"))
    
    # 执行摘要（不应抛出异常）
    result = await orchestrator._summarize_history_context(history_messages, current_question)
    
    # 验证降级策略：返回最近6条消息
    assert "历史对话上下文" in result
    assert "消息3" in result  # 最近6条消息的第一条
    assert "消息8" in result  # 最近6条消息的最后一条


def test_count_tokens_chinese_and_english(orchestrator):
    """测试 Token 计数 - 中英文混合"""
    # 测试纯中文
    chinese_text = "这是一个测试"  # 6个中文字符
    chinese_tokens = orchestrator._count_tokens(chinese_text)
    # Token 计数是估算值，允许一定误差
    assert 8 <= chinese_tokens <= 11  # 约 9 tokens，允许 ±2 的误差
    
    # 测试纯英文
    english_text = "This is a test"  # 4个英文单词
    english_tokens = orchestrator._count_tokens(english_text)
    assert english_tokens >= 4  # 至少4 tokens
    
    # 测试中英文混合
    mixed_text = "查询 orders 表的 total_amount 字段"
    mixed_tokens = orchestrator._count_tokens(mixed_text)
    assert mixed_tokens > 0


def test_calculate_history_tokens(orchestrator):
    """测试历史消息 Token 计算"""
    history_messages = [
        {"role": "user", "content": "查询销售额"},  # 约 6 tokens
        {"role": "assistant", "content": "好的"},  # 约 3 tokens
        {"role": "user", "content": "按月份分组"}  # 约 7.5 tokens
    ]
    
    total_tokens = orchestrator._calculate_history_tokens(history_messages)
    
    # 验证总 Token 数在合理范围内
    assert total_tokens > 0
    assert total_tokens < 100  # 短消息不应超过100 tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
