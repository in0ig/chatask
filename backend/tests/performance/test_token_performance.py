"""
Token 计数性能测试

性能基准：Token 计数时间 < 100ms
"""

import pytest
import time
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from services.token_manager import TokenManager, Message, ModelType


class TestTokenCountPerformance:
    """Token 计数性能测试"""
    
    @pytest.fixture
    def token_manager(self):
        """创建 TokenManager 实例"""
        return TokenManager()
    
    @pytest.fixture
    def sample_messages(self):
        """创建示例消息列表"""
        return [
            Message("user", "查询上个月的销售额"),
            Message("assistant", "好的，我正在为您查询上个月的销售额数据。"),
            Message("user", "按产品类别分组"),
            Message("assistant", "已按产品类别对上个月的销售额进行分组分析。"),
            Message("user", "显示前五名产品"),
            Message("assistant", "前五名产品是：A产品(120万), B产品(95万), C产品(87万), D产品(76万), E产品(68万)。"),
        ]
    
    @pytest.fixture
    def large_messages(self):
        """创建大量消息列表（100条）"""
        messages = []
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"这是第{i+1}条消息，包含一些测试内容。" * 10
            messages.append(Message(role, content))
        return messages
    
    def test_token_count_small_messages_performance(self, token_manager, sample_messages):
        """测试小量消息的 Token 计数性能"""
        # 预热
        token_manager.count_messages_tokens(sample_messages, ModelType.LOCAL)
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):  # 运行100次取平均
            token_manager.count_messages_tokens(sample_messages, ModelType.LOCAL)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000  # 转换为毫秒
        
        print(f"\n小量消息 Token 计数平均时间: {avg_time:.2f}ms")
        
        # 性能断言：应该在 100ms 内完成
        assert avg_time < 100, f"Token 计数时间 {avg_time:.2f}ms 超过 100ms 基准"
    
    def test_token_count_large_messages_performance(self, token_manager, large_messages):
        """测试大量消息的 Token 计数性能"""
        # 预热
        token_manager.count_messages_tokens(large_messages, ModelType.LOCAL)
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(10):  # 运行10次取平均
            token_manager.count_messages_tokens(large_messages, ModelType.LOCAL)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10 * 1000  # 转换为毫秒
        
        print(f"\n大量消息 Token 计数平均时间: {avg_time:.2f}ms")
        
        # 性能断言：应该在 100ms 内完成
        assert avg_time < 100, f"Token 计数时间 {avg_time:.2f}ms 超过 100ms 基准"
    
    def test_token_count_alibaba_model_performance(self, token_manager, sample_messages):
        """测试阿里云模型的 Token 计数性能"""
        # 预热
        token_manager.count_messages_tokens(sample_messages, ModelType.ALIBABA)
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):
            token_manager.count_messages_tokens(sample_messages, ModelType.ALIBABA)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000
        
        print(f"\n阿里云模型 Token 计数平均时间: {avg_time:.2f}ms")
        
        # 性能断言
        assert avg_time < 100, f"Token 计数时间 {avg_time:.2f}ms 超过 100ms 基准"


class TestTokenLimitCheckPerformance:
    """Token 限制检查性能测试"""
    
    @pytest.fixture
    def token_manager(self):
        return TokenManager()
    
    def test_check_token_limit_performance(self, token_manager):
        """测试 Token 限制检查性能"""
        # 测量执行时间
        start_time = time.time()
        for _ in range(1000):
            token_manager.check_token_limit(10000, ModelType.LOCAL)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000 * 1000  # 转换为毫秒
        
        print(f"\nToken 限制检查平均时间: {avg_time:.4f}ms")
        
        # 性能断言：应该非常快
        assert avg_time < 1, f"Token 限制检查时间 {avg_time:.4f}ms 超过 1ms"
