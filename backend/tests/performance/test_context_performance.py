"""
上下文总结性能测试

性能基准：上下文总结时间 < 5s
"""

import pytest
import time
import sys
import os
from unittest.mock import Mock, patch

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from services.context_summarizer import ContextSummarizer
from services.token_manager import TokenManager


class TestContextSummarizerPerformance:
    """上下文总结性能测试"""
    
    @pytest.fixture
    def summarizer(self):
        """创建 ContextSummarizer 实例"""
        summarizer = ContextSummarizer()
        # Mock 依赖项
        summarizer.token_manager = Mock(spec=TokenManager)
        summarizer.session_service = Mock()
        return summarizer
    
    @pytest.fixture
    def sample_messages(self):
        """创建示例对话消息"""
        return [
            {"role": "user", "content": "查询上个月的销售额"},
            {"role": "assistant", "content": "好的，我正在为您查询上个月的销售额数据。"},
            {"role": "user", "content": "按产品类别分组"},
            {"role": "assistant", "content": "已按产品类别对上个月的销售额进行分组分析。"},
            {"role": "user", "content": "显示前五名产品"},
            {"role": "assistant", "content": "前五名产品是：A产品(120万), B产品(95万), C产品(87万), D产品(76万), E产品(68万)。"},
        ]
    
    @pytest.fixture
    def large_messages(self):
        """创建大量消息列表（50条）"""
        messages = []
        for i in range(50):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"这是第{i+1}条消息，包含一些测试内容。" * 20
            messages.append({"role": role, "content": content})
        return messages
    
    def test_should_summarize_check_performance(self, summarizer, sample_messages):
        """测试总结触发检查性能"""
        # 设置 mock 返回值
        summarizer.token_manager.count_messages_tokens.return_value = 16000
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 预热
        summarizer.should_summarize("test_session", "local")
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):
            summarizer.should_summarize("test_session", "local")
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000  # 转换为毫秒
        
        print(f"\n总结触发检查平均时间: {avg_time:.2f}ms")
        
        # 性能断言：应该在 10ms 内完成
        assert avg_time < 10, f"总结触发检查时间 {avg_time:.2f}ms 超过 10ms"
    
    def test_summarize_context_performance(self, summarizer, large_messages):
        """测试上下文总结性能（模拟）"""
        # 注意：实际的总结需要调用 LLM，这里只测试本地处理部分
        
        # 测量执行时间
        start_time = time.time()
        
        # 模拟总结过程的本地处理部分
        for _ in range(10):
            # 提取最近的消息
            recent_count = 4
            recent_messages = large_messages[-recent_count:]
            older_messages = large_messages[:-recent_count]
            
            # 构建总结提示
            summary_prompt = "请总结以下对话内容：\n"
            for msg in older_messages:
                summary_prompt += f"{msg['role']}: {msg['content']}\n"
        
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10 * 1000  # 转换为毫秒
        
        print(f"\n上下文总结本地处理平均时间: {avg_time:.2f}ms")
        
        # 性能断言：本地处理应该在 100ms 内完成
        assert avg_time < 100, f"上下文总结本地处理时间 {avg_time:.2f}ms 超过 100ms"
    
    def test_save_summary_performance(self, summarizer):
        """测试保存总结性能"""
        # 设置 mock
        summarizer.session_service.save_summary.return_value = None
        
        summary_text = "这是一个测试总结，包含对话的主要内容。" * 10
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):
            summarizer.save_summary("test_session", "local", summary_text)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000
        
        print(f"\n保存总结平均时间: {avg_time:.2f}ms")
        
        # 性能断言
        assert avg_time < 10, f"保存总结时间 {avg_time:.2f}ms 超过 10ms"


class TestContextManagerPerformance:
    """上下文管理器性能测试"""
    
    def test_context_update_performance(self):
        """测试上下文更新性能"""
        # 模拟上下文更新
        context = {
            "session_id": "test_session",
            "messages": [],
            "summary": "",
            "token_count": 0
        }
        
        # 测量执行时间
        start_time = time.time()
        for i in range(1000):
            # 模拟添加消息
            context["messages"].append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i}"
            })
            context["token_count"] += 10
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        
        print(f"\n1000次上下文更新总时间: {total_time:.2f}ms")
        
        # 性能断言
        assert total_time < 100, f"上下文更新时间 {total_time:.2f}ms 超过 100ms"
