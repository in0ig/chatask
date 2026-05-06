"""
消息保存和检索性能测试

性能基准：
- 消息保存时间 < 100ms
- 对话历史检索时间 < 500ms
"""

import pytest
import time
import sys
import os
from unittest.mock import Mock, patch

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from services.multi_turn_handler import MultiTurnHandler


class TestMessageSavePerformance:
    """消息保存性能测试"""
    
    @pytest.fixture
    def handler(self):
        """创建测试模式的 MultiTurnHandler"""
        return MultiTurnHandler(test_mode=True)
    
    def test_add_message_performance(self, handler):
        """测试添加消息性能"""
        session_id = "perf_test_session"
        
        # 预热
        handler.add_message(session_id, {
            "role": "user",
            "content": "预热消息",
            "parent_message_id": None
        })
        
        # 测量执行时间
        start_time = time.time()
        for i in range(100):
            handler.add_message(session_id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"这是第{i+1}条测试消息，包含一些内容。" * 5,
                "parent_message_id": None
            })
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000  # 转换为毫秒
        
        print(f"\n添加消息平均时间: {avg_time:.2f}ms")
        
        # 性能断言：应该在 100ms 内完成
        assert avg_time < 100, f"消息保存时间 {avg_time:.2f}ms 超过 100ms 基准"
    
    def test_batch_add_messages_performance(self, handler):
        """测试批量添加消息性能"""
        session_id = "batch_perf_test_session"
        
        # 测量执行时间
        start_time = time.time()
        
        # 批量添加 500 条消息
        for i in range(500):
            handler.add_message(session_id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"批量消息 {i+1}",
                "parent_message_id": None
            })
        
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        avg_time = total_time / 500
        
        print(f"\n批量添加 500 条消息总时间: {total_time:.2f}ms")
        print(f"平均每条消息时间: {avg_time:.2f}ms")
        
        # 性能断言
        assert avg_time < 100, f"消息保存平均时间 {avg_time:.2f}ms 超过 100ms"


class TestMessageRetrievalPerformance:
    """消息检索性能测试"""
    
    @pytest.fixture
    def handler_with_messages(self):
        """创建包含大量消息的 MultiTurnHandler"""
        handler = MultiTurnHandler(test_mode=True)
        session_id = "retrieval_perf_test_session"
        
        # 添加 1000 条消息
        for i in range(1000):
            handler.add_message(session_id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i+1}：这是一条测试消息，包含一些内容。" * 3,
                "parent_message_id": None
            })
        
        return handler, session_id
    
    def test_get_conversation_history_performance(self, handler_with_messages):
        """测试获取对话历史性能"""
        handler, session_id = handler_with_messages
        
        # 预热
        handler.get_conversation_history(session_id)
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):
            handler.get_conversation_history(session_id)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000
        
        print(f"\n获取对话历史平均时间: {avg_time:.2f}ms")
        
        # 性能断言：应该在 500ms 内完成
        assert avg_time < 500, f"对话历史检索时间 {avg_time:.2f}ms 超过 500ms 基准"
    
    def test_get_conversation_history_with_limit_performance(self, handler_with_messages):
        """测试带限制的对话历史检索性能"""
        handler, session_id = handler_with_messages
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(100):
            handler.get_conversation_history(session_id, limit=50)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000
        
        print(f"\n获取限制数量对话历史平均时间: {avg_time:.2f}ms")
        
        # 性能断言
        assert avg_time < 100, f"限制数量对话历史检索时间 {avg_time:.2f}ms 超过 100ms"
    
    def test_get_last_message_performance(self, handler_with_messages):
        """测试获取最后一条消息性能"""
        handler, session_id = handler_with_messages
        
        # 测量执行时间
        start_time = time.time()
        for _ in range(1000):
            handler.get_last_message(session_id)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000 * 1000
        
        print(f"\n获取最后一条消息平均时间: {avg_time:.4f}ms")
        
        # 性能断言
        assert avg_time < 10, f"获取最后一条消息时间 {avg_time:.4f}ms 超过 10ms"


class TestConcurrentAccessPerformance:
    """并发访问性能测试"""
    
    def test_concurrent_message_operations(self):
        """测试并发消息操作性能"""
        import threading
        
        handler = MultiTurnHandler(test_mode=True)
        results = {"success": 0, "errors": 0}
        lock = threading.Lock()
        
        def add_messages(session_id, count):
            try:
                for i in range(count):
                    handler.add_message(session_id, {
                        "role": "user",
                        "content": f"并发消息 {i}",
                        "parent_message_id": None
                    })
                with lock:
                    results["success"] += count
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        # 创建多个线程
        threads = []
        start_time = time.time()
        
        for i in range(10):
            t = threading.Thread(target=add_messages, args=(f"session_{i}", 100))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000
        
        print(f"\n并发添加 1000 条消息总时间: {total_time:.2f}ms")
        print(f"成功: {results['success']}, 错误: {results['errors']}")
        
        # 性能断言
        assert results["errors"] == 0, f"并发操作出现 {results['errors']} 个错误"
        assert total_time < 5000, f"并发操作时间 {total_time:.2f}ms 超过 5000ms"
