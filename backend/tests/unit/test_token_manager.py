"""
Token 管理服务单元测试
"""

import unittest
from typing import List
from unittest.mock import patch, MagicMock
import sys
import os

# 将 backend/src 添加到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from services.token_manager import TokenManager, ModelType, Message

class TestTokenManager(unittest.TestCase):
    """Token 管理服务测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.token_manager = TokenManager()
        
    def test_count_text_tokens_local_empty(self):
        """测试本地模型空文本 Token 计数"""
        result = self.token_manager.count_text_tokens("", ModelType.LOCAL)
        self.assertEqual(result, 0)
        
    def test_count_text_tokens_local_simple(self):
        """测试本地模型简单文本 Token 计数"""
        # "Hello world" 在 cl100k_base 编码器中应该是 2 个 token
        result = self.token_manager.count_text_tokens("Hello world", ModelType.LOCAL)
        self.assertGreaterEqual(result, 1)  # 至少有一个 token
        
    def test_count_text_tokens_alibaba_empty(self):
        """测试阿里云模型空文本 Token 计数"""
        result = self.token_manager.count_text_tokens("", ModelType.ALIBABA)
        self.assertEqual(result, 0)
        
    def test_count_text_tokens_alibaba_simple(self):
        """测试阿里云模型简单文本 Token 计数"""
        result = self.token_manager.count_text_tokens("Hello world", ModelType.ALIBABA)
        self.assertGreaterEqual(result, 1)  # 至少有一个 token
        
    def test_count_messages_tokens_empty(self):
        """测试空消息列表 Token 计数"""
        result = self.token_manager.count_messages_tokens([], ModelType.LOCAL)
        self.assertEqual(result, 0)
        
    def test_count_messages_tokens_single(self):
        """测试单条消息 Token 计数"""
        messages = [Message("user", "Hello world")]
        result = self.token_manager.count_messages_tokens(messages, ModelType.LOCAL)
        # 应该大于单个文本的 token 数（因为有额外开销）
        text_tokens = self.token_manager.count_text_tokens("Hello world", ModelType.LOCAL)
        self.assertGreater(result, text_tokens)
        
    def test_count_messages_tokens_multiple(self):
        """测试多条消息 Token 计数"""
        messages = [
            Message("system", "You are a helpful assistant"),
            Message("user", "Hello"),
            Message("assistant", "Hi there!")
        ]
        result = self.token_manager.count_messages_tokens(messages, ModelType.LOCAL)
        
        # 验证总 token 数大于各消息单独计数的总和
        total_text_tokens = sum(
            self.token_manager.count_text_tokens(msg.content, ModelType.LOCAL) 
            for msg in messages
        )
        self.assertGreater(result, total_text_tokens)
        
    def test_check_token_limit_local_within_threshold(self):
        """测试本地模型在阈值内"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.LOCAL: {"input": 10000, "output": 2000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.LOCAL)
        
        self.assertTrue(result["is_within_hard_limit"])
        self.assertTrue(result["is_within_summary_threshold"])
        self.assertFalse(result["is_over_hard_limit"])
        self.assertFalse(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 12000)
        self.assertEqual(result["hard_limit"], 32000)
        self.assertEqual(result["summary_threshold"], 15000)
        
    def test_check_token_limit_local_over_summary_threshold(self):
        """测试本地模型超过总结阈值"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.LOCAL: {"input": 16000, "output": 2000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.LOCAL)
        
        self.assertTrue(result["is_within_hard_limit"])
        self.assertFalse(result["is_within_summary_threshold"])
        self.assertFalse(result["is_over_hard_limit"])
        self.assertTrue(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 18000)
        
    def test_check_token_limit_local_over_hard_limit(self):
        """测试本地模型超过硬限制"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.LOCAL: {"input": 30000, "output": 5000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.LOCAL)
        
        self.assertFalse(result["is_within_hard_limit"])
        self.assertFalse(result["is_within_summary_threshold"])
        self.assertTrue(result["is_over_hard_limit"])
        self.assertTrue(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 35000)
        
    def test_check_token_limit_alibaba_within_threshold(self):
        """测试阿里云模型在阈值内"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.ALIBABA: {"input": 500000, "output": 200000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.ALIBABA)
        
        self.assertTrue(result["is_within_hard_limit"])
        self.assertTrue(result["is_within_summary_threshold"])
        self.assertFalse(result["is_over_hard_limit"])
        self.assertFalse(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 700000)
        self.assertEqual(result["hard_limit"], 1000000)
        self.assertEqual(result["summary_threshold"], 800000)
        
    def test_check_token_limit_alibaba_over_summary_threshold(self):
        """测试阿里云模型超过总结阈值"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.ALIBABA: {"input": 850000, "output": 100000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.ALIBABA)
        
        self.assertTrue(result["is_within_hard_limit"])
        self.assertFalse(result["is_within_summary_threshold"])
        self.assertFalse(result["is_over_hard_limit"])
        self.assertTrue(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 950000)
        
    def test_check_token_limit_alibaba_over_hard_limit(self):
        """测试阿里云模型超过硬限制"""
        # 模拟会话状态
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.ALIBABA: {"input": 900000, "output": 200000}
        }
        
        result = self.token_manager.check_token_limit("test_session", ModelType.ALIBABA)
        
        self.assertFalse(result["is_within_hard_limit"])
        self.assertFalse(result["is_within_summary_threshold"])
        self.assertTrue(result["is_over_hard_limit"])
        self.assertTrue(result["is_over_summary_threshold"])
        self.assertEqual(result["total_tokens"], 1100000)
        
    def test_get_token_usage_stats_empty_session(self):
        """测试空会话的 Token 使用统计"""
        result = self.token_manager.get_token_usage_stats("empty_session")
        
        self.assertEqual(result["session_id"], "empty_session")
        self.assertEqual(result["total_input_tokens"], 0)
        self.assertEqual(result["total_output_tokens"], 0)
        self.assertEqual(result["total_tokens"], 0)
        self.assertEqual(result["model_stats"], {})
        
    def test_get_token_usage_stats_single_model(self):
        """测试单模型会话的 Token 使用统计"""
        # 设置测试数据
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.LOCAL: {"input": 5000, "output": 3000}
        }
        
        result = self.token_manager.get_token_usage_stats("test_session")
        
        self.assertEqual(result["session_id"], "test_session")
        self.assertEqual(result["total_input_tokens"], 5000)
        self.assertEqual(result["total_output_tokens"], 3000)
        self.assertEqual(result["total_tokens"], 8000)
        self.assertIn(ModelType.LOCAL, result["model_stats"])
        self.assertEqual(result["model_stats"][ModelType.LOCAL]["input_tokens"], 5000)
        self.assertEqual(result["model_stats"][ModelType.LOCAL]["output_tokens"], 3000)
        self.assertEqual(result["model_stats"][ModelType.LOCAL]["total_tokens"], 8000)
        
    def test_get_token_usage_stats_multiple_models(self):
        """测试多模型会话的 Token 使用统计"""
        # 设置测试数据
        self.token_manager.token_usage_stats["test_session"] = {
            ModelType.LOCAL: {"input": 5000, "output": 3000},
            ModelType.ALIBABA: {"input": 20000, "output": 10000}
        }
        
        result = self.token_manager.get_token_usage_stats("test_session")
        
        self.assertEqual(result["total_input_tokens"], 25000)
        self.assertEqual(result["total_output_tokens"], 13000)
        self.assertEqual(result["total_tokens"], 38000)
        self.assertEqual(len(result["model_stats"]), 2)
        
    def test_update_token_usage(self):
        """测试更新 Token 使用情况"""
        # 初始状态
        self.token_manager.update_token_usage("test_session", ModelType.LOCAL, 1000, 500)
        
        # 验证更新结果
        stats = self.token_manager.get_token_usage_stats("test_session")
        self.assertEqual(stats["total_input_tokens"], 1000)
        self.assertEqual(stats["total_output_tokens"], 500)
        
        # 再次更新
        self.token_manager.update_token_usage("test_session", ModelType.LOCAL, 2000, 1000)
        
        # 验证累加结果
        stats = self.token_manager.get_token_usage_stats("test_session")
        self.assertEqual(stats["total_input_tokens"], 3000)
        self.assertEqual(stats["total_output_tokens"], 1500)
        
    def test_update_token_usage_multiple_sessions(self):
        """测试多个会话的 Token 使用情况"""
        # 更新第一个会话
        self.token_manager.update_token_usage("session1", ModelType.LOCAL, 1000, 500)
        
        # 更新第二个会话
        self.token_manager.update_token_usage("session2", ModelType.ALIBABA, 2000, 1000)
        
        # 验证第一个会话
        stats1 = self.token_manager.get_token_usage_stats("session1")
        self.assertEqual(stats1["total_input_tokens"], 1000)
        self.assertEqual(stats1["total_output_tokens"], 500)
        
        # 验证第二个会话
        stats2 = self.token_manager.get_token_usage_stats("session2")
        self.assertEqual(stats2["total_input_tokens"], 2000)
        self.assertEqual(stats2["total_output_tokens"], 1000)
        
    def test_check_token_limit_invalid_model(self):
        """测试无效模型类型"""
        with self.assertRaises(ValueError):
            self.token_manager.check_token_limit("test_session", "invalid_model")
    
    def test_count_text_tokens_invalid_model(self):
        """测试无效模型类型的 Token 计数"""
        with self.assertRaises(ValueError):
            self.token_manager.count_text_tokens("test", "invalid_model")
    
    def test_count_messages_tokens_invalid_model(self):
        """测试无效模型类型的消息 Token 计数"""
        messages = [Message("user", "test")]
        with self.assertRaises(ValueError):
            self.token_manager.count_messages_tokens(messages, "invalid_model")
    
    def test_edge_case_large_text(self):
        """测试大文本边界情况"""
        # 创建一个很长的文本
        large_text = "A" * 100000
        
        # 测试本地模型
        local_tokens = self.token_manager.count_text_tokens(large_text, ModelType.LOCAL)
        self.assertGreater(local_tokens, 0)
        
        # 测试阿里云模型
        alibaba_tokens = self.token_manager.count_text_tokens(large_text, ModelType.ALIBABA)
        self.assertGreater(alibaba_tokens, 0)
        
        # 验证两个模型的计数逻辑一致
        self.assertEqual(local_tokens, alibaba_tokens)
        
    def test_edge_case_empty_messages(self):
        """测试空消息列表"""
        result = self.token_manager.count_messages_tokens([], ModelType.LOCAL)
        self.assertEqual(result, 0)
        
    def test_edge_case_whitespace_only(self):
        """测试仅包含空白字符的文本"""
        whitespace_text = "   \n\t  "
        result = self.token_manager.count_text_tokens(whitespace_text, ModelType.LOCAL)
        # 空白字符通常也会被编码为 token
        self.assertGreaterEqual(result, 1)
        
    def test_edge_case_special_characters(self):
        """测试特殊字符"""
        special_text = "Hello, 世界! @#$%^&*()"
        result = self.token_manager.count_text_tokens(special_text, ModelType.LOCAL)
        self.assertGreater(result, 0)
        
if __name__ == '__main__':
    unittest.main()
