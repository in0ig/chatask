"""
多轮对话处理处理器单元测试
"""

import pytest
from src.services.multi_turn_conversation_processor import MultiTurnConversationProcessor
from src.services.multi_turn_handler import multi_turn_handler
from src.services.context_summarizer import ContextSummarizer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def processor():
    """创建处理器实例"""
    return MultiTurnConversationProcessor()

@pytest.fixture
def mock_session_id():
    """提供测试会话ID"""
    return "test_session_123"

@pytest.fixture(autouse=True)
def enable_test_mode():
    """在所有测试前启用测试模式"""
    # 设置multi_turn_handler为测试模式
    multi_turn_handler.test_mode = True
    # 清空测试消息
    multi_turn_handler.test_messages = {}
    yield
    # 测试后重置
    multi_turn_handler.test_mode = False
    multi_turn_handler.test_messages = {}

class TestMultiTurnConversationProcessor:
    
    def test_init(self, processor):
        """测试初始化"""
        assert processor is not None
        assert hasattr(processor, 'context_summarizer')
        assert isinstance(processor.context_summarizer, ContextSummarizer)
    
    def test_intent_recognition_query(self, processor):
        """测试意图识别：查询"""
        # 测试普通查询
        intent = processor.intent_recognition("销售额是多少？")
        assert intent == "query"
        
        # 测试包含查询关键词
        intent = processor.intent_recognition("显示上个月的销售数据")
        assert intent == "query"
    
    def test_intent_recognition_interpretation(self, processor):
        """测试意图识别：解读"""
        # 测试包含解读关键词
        intent = processor.intent_recognition("为什么销售额下降了？")
        assert intent == "interpretation"
        
        intent = processor.intent_recognition("解释一下这个趋势")
        assert intent == "interpretation"
        
        intent = processor.intent_recognition("分析一下原因")
        assert intent == "interpretation"
    
    def test_intent_recognition_report(self, processor):
        """测试意图识别：报告"""
        # 测试包含报告关键词
        intent = processor.intent_recognition("生成销售报表")
        assert intent == "report"
        
        intent = processor.intent_recognition("统计一下月度数据")
        assert intent == "report"
        
        intent = processor.intent_recognition("做一个图表分析")
        assert intent == "report"
    
    def test_query_flow(self, processor, mock_session_id):
        """测试查询流程"""
        result = processor.query_flow("销售额是多少？", mock_session_id)
        
        assert result["type"] == "query"
        assert "response" in result
        assert "data" in result
        assert "chart_type" in result
        assert isinstance(result["data"], dict)
        assert result["chart_type"] == "table"
    
    def test_interpretation_flow(self, processor, mock_session_id):
        """测试解读流程"""
        result = processor.interpretation_flow("为什么销售额下降了？", mock_session_id)
        
        assert result["type"] == "interpretation"
        assert "response" in result
        assert "insights" in result
        assert "suggestions" in result
        assert isinstance(result["insights"], list)
        assert isinstance(result["suggestions"], list)
    
    def test_report_flow(self, processor, mock_session_id):
        """测试报告流程"""
        result = processor.report_flow("生成销售报表", mock_session_id)
        
        assert result["type"] == "report"
        assert "response" in result
        assert "summary" in result
        assert "charts" in result
        assert "tables" in result
        assert isinstance(result["charts"], list)
        assert isinstance(result["tables"], list)
    
    def test_save_message(self, processor, mock_session_id):
        """测试消息保存"""
        # 创建一个模拟结果
        result = {
            "type": "query",
            "response": "这是响应内容",
            "data": {},
            "chart_type": "table"
        }
        
        # 调用保存方法
        processor.save_message("用户查询", result, mock_session_id)
        
        # 验证消息被添加到内存中
        assert len(multi_turn_handler.test_messages[mock_session_id]) == 2
        
        # 验证第一个消息是用户消息
        first_message = multi_turn_handler.test_messages[mock_session_id][0]
        assert first_message["role"] == "user"
        assert first_message["content"] == "用户查询"
        
        # 验证第二个消息是助手消息
        second_message = multi_turn_handler.test_messages[mock_session_id][1]
        assert second_message["role"] == "assistant"
        assert "这是响应内容" in second_message["content"]
        
        # 验证返回值
        assert True  # 方法执行没有抛出异常
        
        # 验证上下文总结检查被触发（通过日志）
        # 这里不直接验证，因为日志是副作用
        
        # 验证日志记录
        logger.info("save_message test completed")