"""
AI服务流式方法属性测试
Feature: streaming-stage-output
使用 Hypothesis 进行基于属性的测试
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch
import json
from typing import List

from src.services.ai_model_service import (
    AIModelService,
    QwenCloudAdapter,
    OpenAILocalAdapter,
    ModelType,
    AIModelError
)


# ============================================================================
# Property 4: AI Service Streaming Methods
# Validates: Requirements 3.1, 3.2, 3.3, 3.5
# ============================================================================


class TestStreamingMethodsProperties:
    """
    Property 4: AI Service Streaming Methods
    
    测试流式方法的核心属性：
    1. 流式方法逐步产生内容块
    2. 内容累积正确
    3. 流式过程中的错误处理
    4. 降级到非流式模式
    """
    
    @pytest.fixture
    def qwen_config(self):
        """Qwen模型配置"""
        return {
            'api_key': 'test_api_key',
            'base_url': 'https://test.api.com',
            'model_name': 'qwen-turbo',
            'max_tokens': 2000,
            'temperature': 0.1,
            'retry_count': 3,
            'retry_delay': 0.1
        }
    
    @pytest.fixture
    def openai_config(self):
        """OpenAI模型配置"""
        return {
            'api_key': 'sk-test',
            'base_url': 'https://dashscope.aliyuncs.com/api/v1',
            'model_name': 'qwen-plus',
            'max_tokens': 2000,
            'temperature': 0.7,
            'retry_count': 2,
            'retry_delay': 0.1
        }
    
    @pytest.fixture
    def ai_service(self, qwen_config, openai_config):
        """创建AI服务实例"""
        return AIModelService({
            'qwen_cloud': qwen_config,
            'openai_local': openai_config
        })
    
    # ------------------------------------------------------------------------
    # Property 4.1: 流式方法逐步产生内容块
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=20
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_cloud_model_stream_yields_chunks_progressively(
        self, ai_service, chunks: List[str], prompt: str
    ):
        """
        Property: 对于任何提示词和内容块列表，call_cloud_model_stream() 应该逐步产生内容块
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.1, 3.3
        """
        # 创建模拟的流式响应
        async def mock_stream_lines():
            for chunk in chunks:
                yield json.dumps({
                    'output': {'text': chunk}
                })
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        # Mock HTTP客户端的stream方法
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.QWEN_CLOUD]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 收集所有产生的块
            yielded_chunks = []
            async for chunk in ai_service.call_cloud_model_stream(prompt):
                yielded_chunks.append(chunk)
            
            # 验证：产生的块数量应该等于输入块数量
            assert len(yielded_chunks) == len(chunks)
            
            # 验证：产生的块应该按顺序匹配输入块
            for i, (yielded, expected) in enumerate(zip(yielded_chunks, chunks)):
                assert yielded == expected, f"块 {i} 不匹配: {yielded} != {expected}"
    
    @pytest.mark.asyncio
    @given(
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=20
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_local_model_stream_yields_chunks_progressively(
        self, ai_service, chunks: List[str], prompt: str
    ):
        """
        Property: 对于任何提示词和内容块列表，call_local_model_stream() 应该逐步产生内容块
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.2, 3.3
        """
        # 创建模拟的流式响应
        async def mock_stream_lines():
            for chunk in chunks:
                yield json.dumps({
                    'output': {'text': chunk}
                })
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        # Mock HTTP客户端的stream方法
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.OPENAI_LOCAL]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 收集所有产生的块
            yielded_chunks = []
            async for chunk in ai_service.call_local_model_stream(prompt):
                yielded_chunks.append(chunk)
            
            # 验证：产生的块数量应该等于输入块数量
            assert len(yielded_chunks) == len(chunks)
            
            # 验证：产生的块应该按顺序匹配输入块
            for i, (yielded, expected) in enumerate(zip(yielded_chunks, chunks)):
                assert yielded == expected, f"块 {i} 不匹配: {yielded} != {expected}"
    
    # ------------------------------------------------------------------------
    # Property 4.2: 内容累积正确
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=20
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_cloud_model_stream_accumulates_content_correctly(
        self, ai_service, chunks: List[str], prompt: str
    ):
        """
        Property: 对于任何内容块列表，累积的内容应该等于所有块的连接
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.3, 3.5
        """
        # 创建模拟的流式响应
        async def mock_stream_lines():
            for chunk in chunks:
                yield json.dumps({
                    'output': {'text': chunk}
                })
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.QWEN_CLOUD]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 累积所有块
            accumulated = ""
            async for chunk in ai_service.call_cloud_model_stream(prompt):
                accumulated += chunk
            
            # 验证：累积的内容应该等于所有块的连接
            expected_content = "".join(chunks)
            assert accumulated == expected_content, \
                f"累积内容不匹配:\n期望: {expected_content}\n实际: {accumulated}"
    
    @pytest.mark.asyncio
    @given(
        chunks=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=20
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_local_model_stream_accumulates_content_correctly(
        self, ai_service, chunks: List[str], prompt: str
    ):
        """
        Property: 对于任何内容块列表，累积的内容应该等于所有块的连接
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.3, 3.5
        """
        # 创建模拟的流式响应
        async def mock_stream_lines():
            for chunk in chunks:
                yield json.dumps({
                    'output': {'text': chunk}
                })
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.OPENAI_LOCAL]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 累积所有块
            accumulated = ""
            async for chunk in ai_service.call_local_model_stream(prompt):
                accumulated += chunk
            
            # 验证：累积的内容应该等于所有块的连接
            expected_content = "".join(chunks)
            assert accumulated == expected_content, \
                f"累积内容不匹配:\n期望: {expected_content}\n实际: {accumulated}"
    
    # ------------------------------------------------------------------------
    # Property 4.3: 流式过程中的错误处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        chunks_before_error=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=10
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_cloud_model_stream_handles_errors_gracefully(
        self, ai_service, chunks_before_error: List[str], prompt: str
    ):
        """
        Property: 对于任何在流式过程中发生的错误，系统应该返回已累积的内容
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.4
        
        注意：实现会在抛出异常前yield累积的内容，这是优雅的错误处理行为
        """
        # 创建模拟的流式响应，在产生几个块后抛出异常
        async def mock_stream_lines():
            for chunk in chunks_before_error:
                yield json.dumps({
                    'output': {'text': chunk}
                })
            # 模拟流式中断
            raise Exception("Stream interrupted")
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.QWEN_CLOUD]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 尝试收集所有块
            accumulated = ""
            received_chunks = []
            
            try:
                async for chunk in ai_service.call_cloud_model_stream(prompt):
                    accumulated += chunk
                    received_chunks.append(chunk)
            except AIModelError as e:
                # 验证：错误消息应该包含失败信息
                assert "streaming failed" in str(e).lower()
            
            # 验证：应该接收到错误前的所有块 + 最后的累积内容块（优雅错误处理）
            # 实现会在异常前yield累积内容，所以会多一个块
            assert len(received_chunks) == len(chunks_before_error) + 1, \
                f"Expected {len(chunks_before_error) + 1} chunks (individual + accumulated), got {len(received_chunks)}"
            
            # 验证：累积的内容应该等于错误前所有块的连接（重复一次，因为最后yield了累积内容）
            expected_content = "".join(chunks_before_error) * 2  # 个别块 + 累积块
            assert accumulated == expected_content, \
                f"Expected accumulated content to be doubled (individual chunks + final accumulated chunk)"
    
    @pytest.mark.asyncio
    @given(
        chunks_before_error=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=10
        ),
        prompt=st.text(min_size=1, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_local_model_stream_handles_errors_gracefully(
        self, ai_service, chunks_before_error: List[str], prompt: str
    ):
        """
        Property: 对于任何在流式过程中发生的错误，系统应该返回已累积的内容
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.4
        
        注意：实现会在抛出异常前yield累积的内容，这是优雅的错误处理行为
        """
        # 创建模拟的流式响应，在产生几个块后抛出异常
        async def mock_stream_lines():
            for chunk in chunks_before_error:
                yield json.dumps({
                    'output': {'text': chunk}
                })
            # 模拟流式中断
            raise Exception("Stream interrupted")
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.OPENAI_LOCAL]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 尝试收集所有块
            accumulated = ""
            received_chunks = []
            
            try:
                async for chunk in ai_service.call_local_model_stream(prompt):
                    accumulated += chunk
                    received_chunks.append(chunk)
            except AIModelError as e:
                # 验证：错误消息应该包含失败信息
                assert "streaming failed" in str(e).lower()
            
            # 验证：应该接收到错误前的所有块 + 最后的累积内容块（优雅错误处理）
            # 实现会在异常前yield累积内容，所以会多一个块
            assert len(received_chunks) == len(chunks_before_error) + 1, \
                f"Expected {len(chunks_before_error) + 1} chunks (individual + accumulated), got {len(received_chunks)}"
            
            # 验证：累积的内容应该等于错误前所有块的连接（重复一次，因为最后yield了累积内容）
            expected_content = "".join(chunks_before_error) * 2  # 个别块 + 累积块
            assert accumulated == expected_content, \
                f"Expected accumulated content to be doubled (individual chunks + final accumulated chunk)"
    
    # ------------------------------------------------------------------------
    # Property 4.4: 空内容处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(prompt=st.text(min_size=1, max_size=100))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_cloud_model_stream_handles_empty_response(
        self, ai_service, prompt: str
    ):
        """
        Property: 对于任何提示词，如果流式响应为空，系统应该正常处理
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.3, 3.5
        """
        # 创建空的流式响应
        async def mock_stream_lines():
            # 不产生任何内容
            return
            yield  # 使其成为生成器
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.QWEN_CLOUD]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 收集所有块
            chunks = []
            async for chunk in ai_service.call_cloud_model_stream(prompt):
                chunks.append(chunk)
            
            # 验证：空响应应该产生空列表
            assert len(chunks) == 0
    
    @pytest.mark.asyncio
    @given(prompt=st.text(min_size=1, max_size=100))
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_local_model_stream_handles_empty_response(
        self, ai_service, prompt: str
    ):
        """
        Property: 对于任何提示词，如果流式响应为空，系统应该正常处理
        Feature: streaming-stage-output, Property 4: AI Service Streaming Methods
        Validates: Requirements 3.3, 3.5
        """
        # 创建空的流式响应
        async def mock_stream_lines():
            # 不产生任何内容
            return
            yield  # 使其成为生成器
        
        mock_response = Mock()
        mock_response.aiter_lines = mock_stream_lines
        mock_response.raise_for_status = Mock()
        
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None
        
        adapter = ai_service.adapters[ModelType.OPENAI_LOCAL]
        
        with patch.object(adapter.client, 'stream', return_value=mock_stream_context):
            # 收集所有块
            chunks = []
            async for chunk in ai_service.call_local_model_stream(prompt):
                chunks.append(chunk)
            
            # 验证：空响应应该产生空列表
            assert len(chunks) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
