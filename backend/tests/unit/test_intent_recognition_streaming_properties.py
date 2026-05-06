"""
意图识别流式输出属性测试
Feature: streaming-stage-output
使用 Hypothesis 进行基于属性的测试
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from typing import List, Dict, Any

from src.services.chat_orchestrator import ChatOrchestrator, ChatContext, ChatStage
from src.services.ai_model_service import AIModelService, ModelType
from src.services.websocket_stream_service import WebSocketStreamService


# ============================================================================
# Property 5: Streaming for AI-Generated Stages (Intent Recognition)
# Validates: Requirements 4.1, 4.5
# ============================================================================


class TestIntentRecognitionStreamingProperties:
    """
    Property 5: Streaming for AI-Generated Stages (Intent Recognition)
    
    测试意图识别流式输出的核心属性：
    1. stage_start, stage_update, stage_complete 消息序列正确
    2. 内容累积和 JSON 解析正确
    3. 错误处理正确
    """
    
    @pytest.fixture
    def mock_websocket_service(self):
        """创建模拟的 WebSocket 服务"""
        service = Mock(spec=WebSocketStreamService)
        service.send_stage_start = AsyncMock()
        service.send_stage_update = AsyncMock()
        service.send_stage_complete = AsyncMock()
        service.send_error_message = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_ai_service(self):
        """创建模拟的 AI 服务"""
        service = Mock(spec=AIModelService)
        return service
    
    @pytest.fixture
    def orchestrator(self, mock_websocket_service, mock_ai_service):
        """创建 ChatOrchestrator 实例"""
        orch = ChatOrchestrator()
        orch.websocket_service = mock_websocket_service
        orch.ai_service = mock_ai_service
        return orch
    
    @pytest.fixture
    def chat_context(self):
        """创建测试用的对话上下文"""
        return ChatContext(session_id="test_session_123")
    
    # ------------------------------------------------------------------------
    # Property 5.1: stage_start, stage_update, stage_complete 消息序列
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        intent=st.sampled_from(["smart_query", "report_generation"]),
        confidence=st.floats(min_value=0.5, max_value=1.0),
        chunks=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=2,
            max_size=10
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_intent_recognition_sends_correct_message_sequence(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        intent: str,
        confidence: float,
        chunks: List[str]
    ):
        """
        Property: 对于任何用户问题，意图识别应该发送正确的消息序列：
        stage_start (空内容) → stage_update (多个块) → stage_complete (格式化结果)
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 构建完整的 JSON 响应
        full_response = json.dumps({
            "intent": intent,
            "confidence": confidence,
            "reason": "Test reason"
        })
        
        # 将响应分成多个块
        chunk_size = max(1, len(full_response) // len(chunks))
        actual_chunks = []
        for i in range(0, len(full_response), chunk_size):
            actual_chunks.append(full_response[i:i+chunk_size])
        
        # 模拟流式响应
        async def mock_stream():
            for chunk in actual_chunks:
                yield chunk
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证消息序列
        # 1. 应该发送 stage_start（空内容）
        assert mock_websocket_service.send_stage_start.called
        start_call = mock_websocket_service.send_stage_start.call_args
        assert start_call[1]['session_id'] == chat_context.session_id
        assert start_call[1]['stage_id'] == "intent_recognition"
        assert start_call[1]['stage_name'] == "意图识别"
        assert start_call[1]['content'] == ""
        
        # 2. 应该发送多个 stage_update（增量块）
        assert mock_websocket_service.send_stage_update.call_count >= len(actual_chunks)
        
        # 验证每个 stage_update 调用
        for i, call in enumerate(mock_websocket_service.send_stage_update.call_args_list):
            assert call[1]['session_id'] == chat_context.session_id
            assert call[1]['stage_id'] == "intent_recognition"
            assert 'content' in call[1]
            assert len(call[1]['content']) > 0
        
        # 3. 应该发送 stage_complete（格式化结果）
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        assert complete_call[1]['session_id'] == chat_context.session_id
        assert complete_call[1]['stage_id'] == "intent_recognition"
        assert complete_call[1]['stage_name'] == "意图识别"
        assert len(complete_call[1]['content']) > 0
        
        # 验证返回结果
        assert result['success'] is True
        assert result['intent'] == intent
        assert abs(result['confidence'] - confidence) < 0.01
    
    # ------------------------------------------------------------------------
    # Property 5.2: 内容累积和 JSON 解析
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        intent=st.sampled_from(["smart_query", "report_generation", "data_followup"]),
        confidence=st.floats(min_value=0.5, max_value=1.0),
        num_chunks=st.integers(min_value=2, max_value=15)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_intent_recognition_accumulates_and_parses_json(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        intent: str,
        confidence: float,
        num_chunks: int
    ):
        """
        Property: 对于任何分块的 JSON 响应，系统应该正确累积内容并解析 JSON
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 构建完整的 JSON 响应
        full_response = json.dumps({
            "intent": intent,
            "confidence": confidence,
            "reason": "Generated test reason for property testing"
        })
        
        # 将响应分成指定数量的块
        chunk_size = max(1, len(full_response) // num_chunks)
        chunks = []
        for i in range(0, len(full_response), chunk_size):
            chunks.append(full_response[i:i+chunk_size])
        
        # 模拟流式响应
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证：应该成功解析 JSON
        assert result['success'] is True
        
        # 验证：解析的意图应该正确映射
        # _map_intent_to_enum 会将 "query" 映射为 "smart_query"
        if intent == "query":
            assert result['intent'] == "smart_query"
        elif intent == "report":
            assert result['intent'] == "report_generation"
        elif intent == "followup":
            assert result['intent'] == "data_followup"
        else:
            assert result['intent'] == intent
        
        # 验证：置信度应该正确
        assert abs(result['confidence'] - confidence) < 0.01
        
        # 验证：应该有原因字段
        assert 'reason' in result
    
    # ------------------------------------------------------------------------
    # Property 5.3: 错误处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        chunks_before_error=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',))).filter(
                lambda x: x not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'true', 'false', 'null']
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_intent_recognition_handles_streaming_errors(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        chunks_before_error: List[str]
    ):
        """
        Property: 对于任何流式过程中的错误，系统应该优雅处理并发送 stage_complete
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 模拟流式响应，在产生几个块后抛出异常
        async def mock_stream():
            for chunk in chunks_before_error:
                yield chunk
            raise Exception("Simulated streaming error")
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 🔧 配置非流式调用的 fallback mock（当流式失败且无累积内容时使用）
        # 返回一个有效的 JSON 响应，以便降级策略能够成功
        fallback_response = {
            "success": True,
            "content": json.dumps({
                "intent": "smart_query",
                "confidence": 0.7,
                "reason": "Fallback intent recognition after streaming error"
            })
        }
        mock_ai_service.call_cloud_model = AsyncMock(return_value=fallback_response)
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证：应该发送 stage_start
        assert mock_websocket_service.send_stage_start.called
        
        # 验证：应该发送一些 stage_update（错误前的块）
        assert mock_websocket_service.send_stage_update.call_count >= len(chunks_before_error)
        
        # 验证：应该发送 stage_complete（即使出错）
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：结果应该使用降级策略
        # 如果累积的内容无法解析为 JSON，会使用 _fallback_intent_recognition
        # 如果没有累积内容，会尝试非流式调用，然后解析其返回的 JSON
        assert result['success'] is True
        assert 'intent' in result
        assert result['intent'] in ["smart_query", "report_generation", "data_followup"]
    
    # ------------------------------------------------------------------------
    # Property 5.4: JSON 解析失败降级
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        invalid_json=st.text(min_size=10, max_size=100).filter(
            lambda x: not x.strip().startswith('{')
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_intent_recognition_falls_back_on_invalid_json(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        invalid_json: str
    ):
        """
        Property: 对于任何无效的 JSON 响应，系统应该使用降级策略
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 模拟返回无效 JSON 的流式响应
        async def mock_stream():
            yield invalid_json
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证：应该发送完整的消息序列
        assert mock_websocket_service.send_stage_start.called
        assert mock_websocket_service.send_stage_update.called
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：应该使用降级策略
        assert result['success'] is True
        assert 'intent' in result
        assert result['intent'] in ["smart_query", "report_generation", "data_followup"]
        
        # 验证：降级策略应该有置信度
        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0
    
    # ------------------------------------------------------------------------
    # Property 5.5: 空响应处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_intent_recognition_handles_empty_response(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str
    ):
        """
        Property: 对于任何空响应，系统应该使用降级策略
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 模拟空的流式响应
        async def mock_stream():
            return
            yield  # 使其成为生成器
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证：应该发送消息序列
        assert mock_websocket_service.send_stage_start.called
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：应该使用降级策略
        assert result['success'] is True
        assert 'intent' in result
    
    # ------------------------------------------------------------------------
    # Property 5.6: 消息内容非空性
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        intent=st.sampled_from(["smart_query", "report_generation"]),
        confidence=st.floats(min_value=0.5, max_value=1.0)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_stage_complete_content_is_not_empty(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        intent: str,
        confidence: float
    ):
        """
        Property: 对于任何成功的意图识别，stage_complete 的内容不应该为空
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.1, 4.5
        """
        # 构建有效的 JSON 响应
        full_response = json.dumps({
            "intent": intent,
            "confidence": confidence,
            "reason": "Test"
        })
        
        # 模拟流式响应
        async def mock_stream():
            yield full_response
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行意图识别
        result = await orchestrator._recognize_intent(chat_context, user_question)
        
        # 验证：stage_complete 的内容不应该为空
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        content = complete_call[1]['content']
        
        assert content is not None
        assert len(content) > 0
        assert "意图识别完成" in content or "意图识别失败" in content


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
