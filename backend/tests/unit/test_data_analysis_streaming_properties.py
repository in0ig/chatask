"""
数据分析流式输出属性测试
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
# Property 5: Streaming for AI-Generated Stages (Data Analysis)
# Validates: Requirements 4.3, 4.5
# ============================================================================


class TestDataAnalysisStreamingProperties:
    """
    Property 5: Streaming for AI-Generated Stages (Data Analysis)
    
    测试数据分析流式输出的核心属性：
    1. stage_start, stage_update, stage_complete 消息序列正确
    2. 内容累积正确
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
        context = ChatContext(session_id="test_session_123")
        # 设置查询结果
        context.query_result = {
            "columns": ["name", "count"],
            "rows": [
                {"name": "张三", "count": 5},
                {"name": "李四", "count": 3}
            ],
            "total_rows": 2,
            "execution_time": 0.05
        }
        return context
    
    # ------------------------------------------------------------------------
    # Property 5.1: stage_start, stage_update, stage_complete 消息序列
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=2,
            max_size=15
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_data_analysis_sends_correct_message_sequence(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        chunks: List[str]
    ):
        """
        Property: 对于任何用户问题，数据分析应该发送正确的消息序列：
        stage_start (空内容) → stage_update (多个块) → stage_complete (完整内容)
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 模拟流式响应
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证消息序列
        # 1. 应该发送 stage_start（空内容）
        assert mock_websocket_service.send_stage_start.called
        start_call = mock_websocket_service.send_stage_start.call_args
        assert start_call[1]['session_id'] == chat_context.session_id
        assert start_call[1]['stage_id'] == "data_analysis"
        assert start_call[1]['stage_name'] == "数据分析"
        assert start_call[1]['content'] == ""
        
        # 2. 应该发送多个 stage_update（增量块）
        assert mock_websocket_service.send_stage_update.call_count >= len(chunks)
        
        # 验证每个 stage_update 调用
        for i, call in enumerate(mock_websocket_service.send_stage_update.call_args_list):
            assert call[1]['session_id'] == chat_context.session_id
            assert call[1]['stage_id'] == "data_analysis"
            assert 'content' in call[1]
            assert len(call[1]['content']) > 0
        
        # 3. 应该发送 stage_complete（完整内容）
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        assert complete_call[1]['session_id'] == chat_context.session_id
        assert complete_call[1]['stage_id'] == "data_analysis"
        assert complete_call[1]['stage_name'] == "数据分析"
        assert len(complete_call[1]['content']) > 0
        
        # 验证返回结果
        assert result['success'] is True
        assert 'analysis' in result
        assert len(result['analysis']) > 0
    
    # ------------------------------------------------------------------------
    # Property 5.2: 内容累积
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=10
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_data_analysis_accumulates_content_correctly(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        chunks: List[str]
    ):
        """
        Property: 对于任何分块的响应，系统应该正确累积内容
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 使用预定义的块列表，避免chunking逻辑问题
        full_response = ''.join(chunks)
        
        # 模拟流式响应
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证：应该成功
        assert result['success'] is True
        
        # 验证：累积的内容应该等于完整响应
        assert result['analysis'] == full_response
        
        # 验证：stage_complete 的内容应该是完整响应
        complete_call = mock_websocket_service.send_stage_complete.call_args
        assert complete_call[1]['content'] == full_response
        
        # 验证：所有 stage_update 的内容累加应该等于完整响应
        all_updates = []
        for call in mock_websocket_service.send_stage_update.call_args_list:
            all_updates.append(call[1]['content'])
        
        accumulated = ''.join(all_updates)
        assert accumulated == full_response
    
    # ------------------------------------------------------------------------
    # Property 5.3: 错误处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        chunks_before_error=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_data_analysis_handles_streaming_errors(
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
        Validates: Requirements 4.3, 4.5
        """
        # 模拟流式响应，在产生几个块后抛出异常
        async def mock_stream():
            for chunk in chunks_before_error:
                yield chunk
            raise Exception("Simulated streaming error")
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证：应该发送 stage_start
        assert mock_websocket_service.send_stage_start.called
        
        # 验证：应该发送一些 stage_update（错误前的块）
        assert mock_websocket_service.send_stage_update.call_count >= len(chunks_before_error)
        
        # 验证：应该发送 stage_complete（即使出错）
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：如果有部分内容，应该返回部分内容
        if chunks_before_error:
            accumulated = ''.join(chunks_before_error)
            assert result['success'] is True
            assert result['analysis'] == accumulated
        else:
            # 如果没有内容，应该返回失败
            assert result['success'] is False
    
    # ------------------------------------------------------------------------
    # Property 5.4: 空响应处理
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
    async def test_data_analysis_handles_empty_response(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str
    ):
        """
        Property: 对于任何空响应，系统应该优雅处理
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 模拟空的流式响应
        async def mock_stream():
            return
            yield  # 使其成为生成器
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证：应该发送消息序列
        assert mock_websocket_service.send_stage_start.called
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：应该返回成功（空内容）
        assert result['success'] is True
        assert result['analysis'] == ""
    
    # ------------------------------------------------------------------------
    # Property 5.5: 消息内容非空性（正常情况）
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        analysis_text=st.text(min_size=10, max_size=200)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_stage_complete_content_matches_accumulated(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        analysis_text: str
    ):
        """
        Property: 对于任何成功的数据分析，stage_complete 的内容应该等于累积的内容
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 模拟流式响应
        async def mock_stream():
            yield analysis_text
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证：stage_complete 的内容应该等于分析文本
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        content = complete_call[1]['content']
        
        assert content == analysis_text
        assert result['analysis'] == analysis_text
    
    # ------------------------------------------------------------------------
    # Property 5.6: 历史消息上下文处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        history_count=st.integers(min_value=1, max_value=15),
        analysis_text=st.text(min_size=10, max_size=200)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_data_analysis_handles_history_context(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        history_count: int,
        analysis_text: str
    ):
        """
        Property: 对于任何包含历史消息的上下文，系统应该正确处理
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 添加历史消息到上下文
        history_messages = []
        for i in range(history_count):
            history_messages.append({
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Message {i}',
                'timestamp': f'2024-01-01T00:00:{i:02d}'
            })
        
        chat_context.metadata['history_messages'] = history_messages
        
        # 模拟流式响应
        async def mock_stream():
            yield analysis_text
        
        mock_ai_service.call_model_stream = Mock(return_value=mock_stream())
        
        # 执行数据分析
        result = await orchestrator._analyze_data(chat_context, user_question)
        
        # 验证：应该成功
        assert result['success'] is True
        assert result['analysis'] == analysis_text
        
        # 验证：应该发送完整的消息序列
        assert mock_websocket_service.send_stage_start.called
        assert mock_websocket_service.send_stage_update.called
        assert mock_websocket_service.send_stage_complete.called
    
    # ------------------------------------------------------------------------
    # Property 5.7: 多次调用的一致性
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        analysis_text=st.text(min_size=10, max_size=200)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_data_analysis_consistency_across_calls(
        self,
        chat_context,
        user_question: str,
        analysis_text: str
    ):
        """
        Property: 对于相同的输入，多次调用应该产生一致的结果
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.3, 4.5
        """
        # 创建第一个 orchestrator 和 mocks
        mock_websocket_service_1 = Mock(spec=WebSocketStreamService)
        mock_websocket_service_1.send_stage_start = AsyncMock()
        mock_websocket_service_1.send_stage_update = AsyncMock()
        mock_websocket_service_1.send_stage_complete = AsyncMock()
        
        mock_ai_service_1 = Mock(spec=AIModelService)
        
        orchestrator_1 = ChatOrchestrator()
        orchestrator_1.websocket_service = mock_websocket_service_1
        orchestrator_1.ai_service = mock_ai_service_1
        
        # 模拟流式响应（第一次调用）
        async def mock_stream_1():
            yield analysis_text
        
        mock_ai_service_1.call_model_stream = Mock(return_value=mock_stream_1())
        
        # 第一次调用
        result1 = await orchestrator_1._analyze_data(chat_context, user_question)
        call_count_1 = mock_websocket_service_1.send_stage_update.call_count
        
        # 创建第二个 orchestrator 和 mocks（完全独立）
        mock_websocket_service_2 = Mock(spec=WebSocketStreamService)
        mock_websocket_service_2.send_stage_start = AsyncMock()
        mock_websocket_service_2.send_stage_update = AsyncMock()
        mock_websocket_service_2.send_stage_complete = AsyncMock()
        
        mock_ai_service_2 = Mock(spec=AIModelService)
        
        orchestrator_2 = ChatOrchestrator()
        orchestrator_2.websocket_service = mock_websocket_service_2
        orchestrator_2.ai_service = mock_ai_service_2
        
        # 模拟流式响应（第二次调用 - 创建新的生成器）
        async def mock_stream_2():
            yield analysis_text
        
        mock_ai_service_2.call_model_stream = Mock(return_value=mock_stream_2())
        
        # 第二次调用
        result2 = await orchestrator_2._analyze_data(chat_context, user_question)
        call_count_2 = mock_websocket_service_2.send_stage_update.call_count
        
        # 验证：两次调用应该产生相同的结果
        assert result1['success'] == result2['success']
        assert result1['analysis'] == result2['analysis']
        
        # 验证：两次调用应该发送相同数量的 stage_update
        assert call_count_1 == call_count_2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
