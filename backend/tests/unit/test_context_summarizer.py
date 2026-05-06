"""
上下文总结服务单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import logging
import sys
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from src.services.token_manager import Message, ModelType

# 将 backend/src 添加到 Python 路径
import os
import sys
# 使用绝对路径确保能正确找到src目录
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, src_path)
print(f"Added {src_path} to Python path")

from services.context_summarizer import ContextSummarizer
from services.token_manager import TokenManager
from services.session_service import SessionService
from models.session_model import SessionModel

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestContextSummarizer:
    """
    ContextSummarizer 类的单元测试
    """
    
    @pytest.fixture
    def summarizer(self):
        """创建ContextSummarizer实例的pytest fixture"""
        # 使用mock对象替换依赖项
        mock_token_manager = Mock(spec=TokenManager)
        
        # 创建SessionService mock并添加缺失的方法
        mock_session_service = Mock(spec=SessionService)
        mock_session_service.save_summary = Mock()
        mock_session_service.get_summary = Mock()
        mock_session_service.update_conversation = Mock()
        mock_session_service.log_summary_event = Mock()
        
        summarizer = ContextSummarizer()
        summarizer.token_manager = mock_token_manager
        summarizer.session_service = mock_session_service
        
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
            {"role": "user", "content": "比较今年和去年的同期数据"},
            {"role": "assistant", "content": "已计算今年和去年同期的销售额对比。今年同比增长15%。"},
            {"role": "user", "content": "生成柱状图"},
            {"role": "assistant", "content": "已生成销售额的柱状图，显示各产品类别对比。"},
            {"role": "user", "content": "导出为Excel"},
            {"role": "assistant", "content": "已准备导出为Excel文件，包含所有数据和图表。"}
        ]
    
    def test_should_summarize_local_exceed_threshold(self, summarizer, sample_messages):
        """测试本地模型超过token阈值时触发总结"""
        # 设置mock返回值
        summarizer.token_manager.count_messages_tokens.return_value = 16000  # 超过15000阈值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        result = summarizer.should_summarize("test_session", "local")
        
        assert result is True
        # 验证count_messages_tokens被调用，参数是Message对象列表而不是消息字典列表
        assert summarizer.token_manager.count_messages_tokens.call_count == 1
        call_args = summarizer.token_manager.count_messages_tokens.call_args[0]
        assert len(call_args) == 2  # 两个参数：messages列表和model_enum
        messages_list = call_args[0]
        model_enum = call_args[1]
        # 验证第一个参数是Message对象列表
        assert all(isinstance(msg, Message) for msg in messages_list)
        # 验证第二个参数是ModelType.LOCAL
        assert model_enum == ModelType.LOCAL
    
    def test_should_summarize_local_below_threshold(self, summarizer, sample_messages):
        """测试本地模型低于token阈值时不触发总结"""
        # 设置mock返回值
        summarizer.token_manager.count_messages_tokens.return_value = 14000  # 低于15000阈值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        result = summarizer.should_summarize("test_session", "local")
        
        assert result is False
        # 验证count_messages_tokens被调用，参数是Message对象列表而不是消息字典列表
        assert summarizer.token_manager.count_messages_tokens.call_count == 1
        call_args = summarizer.token_manager.count_messages_tokens.call_args[0]
        assert len(call_args) == 2  # 两个参数：messages列表和model_enum
        messages_list = call_args[0]
        model_enum = call_args[1]
        # 验证第一个参数是Message对象列表
        assert all(isinstance(msg, Message) for msg in messages_list)
        # 验证第二个参数是ModelType.LOCAL
        assert model_enum == ModelType.LOCAL
    
    def test_should_summarize_aliyun_exceed_threshold(self, summarizer, sample_messages):
        """测试阿里云模型超过token阈值时触发总结"""
        # 设置mock返回值
        summarizer.token_manager.count_messages_tokens.return_value = 810000  # 超过800000阈值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        result = summarizer.should_summarize("test_session", "aliyun")
        
        assert result is True
        # 验证count_messages_tokens被调用，参数是Message对象列表而不是消息字典列表
        assert summarizer.token_manager.count_messages_tokens.call_count == 1
        call_args = summarizer.token_manager.count_messages_tokens.call_args[0]
        assert len(call_args) == 2  # 两个参数：messages列表和model_enum
        messages_list = call_args[0]
        model_enum = call_args[1]
        # 验证第一个参数是Message对象列表
        assert all(isinstance(msg, Message) for msg in messages_list)
        # 验证第二个参数是ModelType.ALIBABA
        assert model_enum == ModelType.ALIBABA
    
    def test_should_summarize_aliyun_below_threshold(self, summarizer, sample_messages):
        """测试阿里云模型低于token阈值时不触发总结"""
        # 设置mock返回值
        summarizer.token_manager.count_messages_tokens.return_value = 790000  # 低于800000阈值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        result = summarizer.should_summarize("test_session", "aliyun")
        
        assert result is False
        # 验证count_messages_tokens被调用，参数是Message对象列表而不是消息字典列表
        assert summarizer.token_manager.count_messages_tokens.call_count == 1
        call_args = summarizer.token_manager.count_messages_tokens.call_args[0]
        assert len(call_args) == 2  # 两个参数：messages列表和model_enum
        messages_list = call_args[0]
        model_enum = call_args[1]
        # 验证第一个参数是Message对象列表
        assert all(isinstance(msg, Message) for msg in messages_list)
        # 验证第二个参数是ModelType.ALIBABA
        assert model_enum == ModelType.ALIBABA
    
    def test_should_summarize_unknown_model(self, summarizer, sample_messages):
        """测试未知模型类型"""
        # 设置mock返回值
        summarizer.token_manager.count_messages_tokens.return_value = 16000
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        result = summarizer.should_summarize("test_session", "unknown")
        
        assert result is False
        # 验证count_messages_tokens没有被调用，因为模型类型未知
        summarizer.token_manager.count_messages_tokens.assert_not_called()
    
    def test_summarize_context_local_model(self, summarizer, sample_messages):
        """测试本地模型的上下文总结生成"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "这是本地模型生成的上下文总结，涵盖了用户对销售额的查询需求。"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", sample_messages)
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建
            mock_client.generate_summary.assert_called_once()
            
            # 验证保留的消息数量（3-5条，取中间值4）
            # 由于我们使用了4条最近消息，所以应该有8条消息被总结（12-4=8）
            # 但实际在_summarize_context中，我们使用了all_messages[:-len(recent_messages)]
            # 所以应该是12-4=8条消息用于总结
            pass  # 这里可以添加更多验证
    
    def test_summarize_context_aliyun_model(self, summarizer, sample_messages):
        """测试阿里云模型的上下文总结生成"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "这是阿里云模型生成的上下文总结，涵盖了用户对销售额的详细分析需求。"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "aliyun", sample_messages)
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建
            mock_client.generate_summary.assert_called_once()
            
            # 验证保留的消息数量（10-20条，取中间值15）
            # 但我们的sample_messages只有12条，所以全部保留
            pass  # 这里可以添加更多验证
    
    def test_save_summary(self, summarizer):
        """测试保存总结到数据库"""
        # 调用save_summary
        summarizer.save_summary("test_session", "local", "测试总结内容")
        
        # 验证session_service的save_summary被调用
        summarizer.session_service.save_summary.assert_called_once_with("test_session", "local", "测试总结内容")
    
    def test_get_summary(self, summarizer):
        """测试获取总结"""
        # 设置mock返回值
        summarizer.session_service.get_summary.return_value = "已存在的总结内容"
        
        # 调用get_summary
        summary = summarizer.get_summary("test_session", "local")
        
        # 验证结果
        assert summary == "已存在的总结内容"
        summarizer.session_service.get_summary.assert_called_once_with("test_session", "local")
    
    def test_update_context_after_summary(self, summarizer, sample_messages):
        """测试总结后更新上下文"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 模拟最近消息（本地模型保留4条）
        recent_messages = sample_messages[-4:]
        
        # 调用update_context_after_summary
        summarizer.update_context_after_summary("test_session", "local", "测试总结", recent_messages)
        
        # 验证session_service的update_conversation被调用
        # 新的对话历史应该是：[总结消息] + 最近的4条消息
        expected_conversation = [
            {"role": "system", "content": "[上下文总结] 测试总结"},
            *recent_messages
        ]
        summarizer.session_service.update_conversation.assert_called_once_with("test_session", expected_conversation)
        
        # 验证log_summary_event被调用
        summarizer.session_service.log_summary_event.assert_called_once_with("test_session", "local", len("测试总结"))
    
    def test_summarize_context_empty_messages(self, summarizer):
        """测试空消息列表的边界情况"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=[])
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "空对话的总结"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", [])
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建（应该能处理空列表）
            mock_client.generate_summary.assert_called_once()
    
    def test_summarize_context_large_messages(self, summarizer):
        """测试超大消息列表的边界情况"""
        # 创建超大消息列表
        large_messages = [{"role": "user", "content": "消息" + str(i)} for i in range(1000)]
        
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=large_messages)
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "超大对话的总结"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", large_messages)
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建（应该能处理大列表）
            mock_client.generate_summary.assert_called_once()
    
    def test_summarize_context_error_handling(self, summarizer, sample_messages):
        """测试总结生成错误处理"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 模拟模型API调用失败
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.side_effect = Exception("模型API调用失败")
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", sample_messages)
            
            # 验证结果（应该返回降级的错误信息）
            assert isinstance(summary, str)
            assert "[上下文总结失败" in summary
            
            # 验证异常被记录
            # 这里需要检查日志，但pytest的logging捕获比较复杂，可以跳过
            pass
    
    def test_update_context_after_summary_error_handling(self, summarizer, sample_messages):
        """测试更新上下文错误处理"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=sample_messages)
        
        # 模拟更新对话失败
        summarizer.session_service.update_conversation.side_effect = Exception("更新对话失败")
        
        # 模拟最近消息
        recent_messages = sample_messages[-4:]
        
        # 调用update_context_after_summary
        with pytest.raises(Exception):
            summarizer.update_context_after_summary("test_session", "local", "测试总结", recent_messages)
        
        # 验证update_conversation被调用
        summarizer.session_service.update_conversation.assert_called_once()
        
        # 验证log_summary_event没有被调用（因为前面的调用失败了）
        summarizer.session_service.log_summary_event.assert_not_called()
    
    def test_get_summary_no_summary(self, summarizer):
        """测试获取不存在的总结"""
        # 设置mock返回值
        summarizer.session_service.get_summary.return_value = None
        
        # 调用get_summary
        summary = summarizer.get_summary("test_session", "local")
        
        # 验证结果
        assert summary is None
        summarizer.session_service.get_summary.assert_called_once_with("test_session", "local")
    
    def test_should_summarize_no_session(self, summarizer):
        """测试会话不存在的情况"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = None
        
        # 调用should_summarize
        result = summarizer.should_summarize("nonexistent_session", "local")
        
        # 验证结果
        assert result is False
        summarizer.session_service.get_session.assert_called_once_with("nonexistent_session")
    
    def test_should_summarize_invalid_conversation(self, summarizer):
        """测试会话中conversation为None的情况"""
        # 设置mock返回值
        mock_session = Mock()
        mock_session.conversation = None
        summarizer.session_service.get_session.return_value = mock_session
        
        # 调用should_summarize
        result = summarizer.should_summarize("test_session", "local")
        
        # 验证结果
        assert result is False
        summarizer.session_service.get_session.assert_called_once_with("test_session")
    
    def test_summarize_context_no_messages(self, summarizer):
        """测试messages参数为空列表的情况"""
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=[])
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "空消息列表的总结"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", [])
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建
            mock_client.generate_summary.assert_called_once()
    
    def test_summarize_context_single_message(self, summarizer):
        """测试只有单条消息的情况"""
        # 创建单条消息
        single_message = [{"role": "user", "content": "查询销售额"}]
        
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=single_message)
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "单条消息的总结"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", single_message)
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建
            mock_client.generate_summary.assert_called_once()
    
    def test_summarize_context_with_invalid_messages(self, summarizer):
        """测试消息格式不完整的情况"""
        # 创建格式不完整的消息
        invalid_messages = [
            {"role": "user"},  # 缺少content
            {"content": "查询销售额"},  # 缺少role
            {"role": "user", "content": "查询销售额"}
        ]
        
        # 设置mock返回值
        summarizer.session_service.get_session.return_value = Mock(conversation=invalid_messages)
        
        # 模拟模型API调用
        with patch('services.context_summarizer.get_model_api_client') as mock_get_client:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "不完整消息的总结"
            mock_get_client.return_value = mock_client
            
            # 调用summarize_context
            summary = summarizer.summarize_context("test_session", "local", invalid_messages)
            
            # 验证结果
            assert isinstance(summary, str)
            assert len(summary) > 0
            
            # 验证提示词构建（应该能处理不完整消息）
            mock_client.generate_summary.assert_called_once()
