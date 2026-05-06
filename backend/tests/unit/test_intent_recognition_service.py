"""
意图识别服务单元测试
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.services.intent_recognition_service import (
    IntentRecognitionService,
    IntentType,
    IntentResult,
    IntentRecognitionError
)
from src.services.ai_model_service import ModelResponse, ModelType
from src.services.prompt_manager import PromptType


@pytest.fixture
def mock_ai_service():
    """模拟AI服务"""
    mock_service = MagicMock()
    mock_service.generate_sql = AsyncMock()
    return mock_service


@pytest.fixture
def mock_prompt_manager():
    """模拟Prompt管理器"""
    mock_manager = MagicMock()
    mock_manager.render_prompt = MagicMock()
    return mock_manager


@pytest.fixture
def intent_service(mock_ai_service, mock_prompt_manager):
    """创建意图识别服务实例"""
    with patch('src.services.intent_recognition_service.get_ai_service', return_value=mock_ai_service), \
         patch('src.services.intent_recognition_service.prompt_manager', mock_prompt_manager):
        service = IntentRecognitionService()
        return service


class TestIntentRecognitionService:
    """意图识别服务测试类"""
    
    @pytest.mark.asyncio
    async def test_identify_query_intent_success(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试成功识别查询意图"""
        # 准备测试数据
        user_question = "查询最近一个月的销售数据"
        
        # 模拟prompt管理器返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        # 模拟AI服务返回
        ai_response = ModelResponse(
            content='```json\n{"intent": "query", "confidence": 0.95, "reasoning": "用户明确要求查询销售数据"}\n```',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=100,
            response_time=1.5
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(user_question)
        
        # 验证结果
        assert result.intent == IntentType.QUERY
        assert result.confidence == 0.95
        assert result.reasoning == "用户明确要求查询销售数据"
        assert result.original_question == user_question
        
        # 验证调用
        mock_prompt_manager.render_prompt.assert_called_once()
        mock_ai_service.generate_sql.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_identify_report_intent_success(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试成功识别报告意图"""
        # 准备测试数据
        user_question = "生成本季度的销售分析报告"
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "report", "confidence": 0.88, "reasoning": "用户要求生成分析报告"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=120,
            response_time=1.8
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(user_question)
        
        # 验证结果
        assert result.intent == IntentType.REPORT
        assert result.confidence == 0.88
        assert result.reasoning == "用户要求生成分析报告"
    
    @pytest.mark.asyncio
    async def test_identify_intent_with_context(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试带上下文的意图识别"""
        # 准备测试数据
        user_question = "继续分析"
        context = {
            "conversation_history": ["查询销售数据", "显示图表"],
            "user_preferences": {"language": "zh-CN"},
            "session_state": "active"
        }
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "query", "confidence": 0.75, "reasoning": "基于对话历史，用户想继续查询"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=150,
            response_time=2.0
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(user_question, context)
        
        # 验证结果
        assert result.intent == IntentType.QUERY
        assert result.confidence == 0.75
        
        # 验证prompt包含上下文信息
        call_args = mock_prompt_manager.render_prompt.call_args
        assert call_args[0][0] == PromptType.INTENT_RECOGNITION
        assert call_args[0][1]['user_question'] == user_question
    
    @pytest.mark.asyncio
    async def test_identify_intent_low_confidence(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试低置信度意图识别"""
        # 准备测试数据
        user_question = "这个怎么样？"
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "query", "confidence": 0.3, "reasoning": "问题不够明确"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=80,
            response_time=1.2
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(user_question)
        
        # 验证结果 - 低置信度应该被标记为UNKNOWN
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.3
    
    @pytest.mark.asyncio
    async def test_identify_intent_invalid_json(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试无效JSON响应"""
        # 准备测试数据
        user_question = "查询数据"
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        ai_response = ModelResponse(
            content='这不是有效的JSON格式',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=50,
            response_time=1.0
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试并验证异常
        with pytest.raises(IntentRecognitionError) as exc_info:
            await intent_service.identify_intent(user_question)
        
        assert "无法从响应中提取JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_identify_intent_missing_intent_field(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试缺少intent字段的响应"""
        # 准备测试数据
        user_question = "查询数据"
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        ai_response = ModelResponse(
            content='{"confidence": 0.8, "reasoning": "分析结果"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=60,
            response_time=1.1
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试并验证异常
        with pytest.raises(IntentRecognitionError) as exc_info:
            await intent_service.identify_intent(user_question)
        
        assert "响应中缺少intent字段" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_identify_intent_empty_question(self, intent_service):
        """测试空问题"""
        # 执行测试并验证异常
        with pytest.raises(IntentRecognitionError) as exc_info:
            await intent_service.identify_intent("")
        
        assert "用户问题不能为空" in str(exc_info.value)
        
        with pytest.raises(IntentRecognitionError) as exc_info:
            await intent_service.identify_intent("   ")
        
        assert "用户问题不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_identify_intent_ai_service_error(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试AI服务错误"""
        # 准备测试数据
        user_question = "查询数据"
        
        # 模拟返回
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{user_question}"
        
        # 模拟AI服务抛出异常
        mock_ai_service.generate_sql.side_effect = Exception("AI服务不可用")
        
        # 执行测试并验证异常
        with pytest.raises(IntentRecognitionError) as exc_info:
            await intent_service.identify_intent(user_question)
        
        assert "意图识别失败" in str(exc_info.value)
    
    def test_extract_json_from_response(self, intent_service):
        """测试JSON提取功能"""
        # 测试Markdown JSON代码块
        response1 = '```json\n{"intent": "query", "confidence": 0.9}\n```'
        result1 = intent_service._extract_json_from_response(response1)
        assert result1 == '{"intent": "query", "confidence": 0.9}'
        
        # 测试通用代码块
        response2 = '```\n{"intent": "report", "confidence": 0.8}\n```'
        result2 = intent_service._extract_json_from_response(response2)
        assert result2 == '{"intent": "report", "confidence": 0.8}'
        
        # 测试直接JSON
        response3 = '这是一个JSON: {"intent": "query", "confidence": 0.7} 结束'
        result3 = intent_service._extract_json_from_response(response3)
        assert result3 == '{"intent": "query", "confidence": 0.7}'
        
        # 测试无效响应
        response4 = '这里没有JSON'
        result4 = intent_service._extract_json_from_response(response4)
        assert result4 is None
    
    def test_parse_intent_response_success(self, intent_service):
        """测试成功解析意图响应"""
        response_content = '{"intent": "query", "confidence": 0.85, "reasoning": "测试推理"}'
        original_question = "测试问题"
        
        result = intent_service._parse_intent_response(response_content, original_question)
        
        assert result.intent == IntentType.QUERY
        assert result.confidence == 0.85
        assert result.reasoning == "测试推理"
        assert result.original_question == original_question
    
    def test_parse_intent_response_clamp_confidence(self, intent_service):
        """测试置信度范围限制"""
        # 测试超出范围的置信度
        response_content = '{"intent": "query", "confidence": 1.5, "reasoning": "测试"}'
        result = intent_service._parse_intent_response(response_content, "测试")
        assert result.confidence == 1.0
        
        response_content = '{"intent": "query", "confidence": -0.5, "reasoning": "测试"}'
        result = intent_service._parse_intent_response(response_content, "测试")
        assert result.confidence == 0.0
    
    def test_get_intent_statistics(self, intent_service):
        """测试获取统计信息"""
        # 初始统计信息
        stats = intent_service.get_intent_statistics()
        assert stats['total_requests'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['intent_distribution']['query'] == 0.0
        
        # 模拟一些统计数据
        intent_service.stats['total_requests'] = 10
        intent_service.stats['successful_recognitions'] = 8
        intent_service.stats['failed_recognitions'] = 2
        intent_service.stats['query_intents'] = 5
        intent_service.stats['report_intents'] = 3
        intent_service.stats['unknown_intents'] = 0
        
        stats = intent_service.get_intent_statistics()
        assert stats['success_rate'] == 0.8
        assert stats['failure_rate'] == 0.2
        assert stats['intent_distribution']['query'] == 0.625  # 5/8
        assert stats['intent_distribution']['report'] == 0.375  # 3/8
    
    def test_reset_statistics(self, intent_service):
        """测试重置统计信息"""
        # 设置一些统计数据
        intent_service.stats['total_requests'] = 10
        intent_service.stats['successful_recognitions'] = 8
        
        # 重置统计信息
        intent_service.reset_statistics()
        
        # 验证重置结果
        assert intent_service.stats['total_requests'] == 0
        assert intent_service.stats['successful_recognitions'] == 0
    
    def test_format_context(self, intent_service):
        """测试上下文格式化"""
        # 测试完整上下文
        context = {
            "conversation_history": ["问题1", "问题2"],
            "user_preferences": {"language": "zh-CN", "theme": "dark"},
            "session_state": "active"
        }
        
        formatted = intent_service._format_context(context)
        assert "对话历史：最近2轮对话" in formatted
        assert "用户偏好：language, theme" in formatted
        assert "会话状态：active" in formatted
        
        # 测试空上下文
        empty_context = {}
        formatted_empty = intent_service._format_context(empty_context)
        assert formatted_empty == ""
    
    def test_get_fallback_prompt(self, intent_service):
        """测试降级prompt"""
        user_question = "测试问题"
        prompt = intent_service._get_fallback_prompt(user_question)
        
        assert user_question in prompt
        assert "智能问数" in prompt
        assert "生成报告" in prompt
        assert "JSON格式" in prompt
    
    @pytest.mark.asyncio
    async def test_update_stats(self, intent_service):
        """测试统计信息更新"""
        # 创建测试结果
        intent_result = IntentResult(
            intent=IntentType.QUERY,
            confidence=0.9,
            reasoning="测试推理",
            original_question="测试问题"
        )
        
        # 更新统计信息
        intent_service._update_stats(intent_result, 1.5)
        
        # 验证统计信息
        assert intent_service.stats['successful_recognitions'] == 1
        assert intent_service.stats['query_intents'] == 1
        assert intent_service.stats['avg_confidence'] == 0.9
        assert intent_service.stats['avg_response_time'] == 1.5
        
        # 再次更新
        intent_result2 = IntentResult(
            intent=IntentType.REPORT,
            confidence=0.8,
            reasoning="测试推理2",
            original_question="测试问题2"
        )
        
        intent_service._update_stats(intent_result2, 2.0)
        
        # 验证平均值计算
        assert intent_service.stats['successful_recognitions'] == 2
        assert intent_service.stats['report_intents'] == 1
        assert abs(intent_service.stats['avg_confidence'] - 0.85) < 0.001  # (0.9 + 0.8) / 2
        assert abs(intent_service.stats['avg_response_time'] - 1.75) < 0.001  # (1.5 + 2.0) / 2


class TestIntentRecognitionEdgeCases:
    """意图识别边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_very_long_question(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试超长问题"""
        # 创建超长问题
        long_question = "查询" * 500  # 1000个字符
        
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{long_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "query", "confidence": 0.7, "reasoning": "长问题分析"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=200,
            response_time=3.0
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(long_question)
        
        # 验证结果
        assert result.intent == IntentType.QUERY
        assert result.original_question == long_question
    
    @pytest.mark.asyncio
    async def test_special_characters_question(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试包含特殊字符的问题"""
        special_question = "查询@#$%^&*()数据！？"
        
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{special_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "query", "confidence": 0.8, "reasoning": "特殊字符问题"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=100,
            response_time=1.5
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(special_question)
        
        # 验证结果
        assert result.intent == IntentType.QUERY
        assert result.original_question == special_question
    
    @pytest.mark.asyncio
    async def test_multilingual_question(self, intent_service, mock_ai_service, mock_prompt_manager):
        """测试多语言问题"""
        multilingual_question = "查询sales data销售数据"
        
        mock_prompt_manager.render_prompt.return_value = f"请分析用户问题：{multilingual_question}"
        
        ai_response = ModelResponse(
            content='{"intent": "query", "confidence": 0.85, "reasoning": "多语言查询问题"}',
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=120,
            response_time=1.8
        )
        mock_ai_service.generate_sql.return_value = ai_response
        
        # 执行测试
        result = await intent_service.identify_intent(multilingual_question)
        
        # 验证结果
        assert result.intent == IntentType.QUERY
        assert result.original_question == multilingual_question