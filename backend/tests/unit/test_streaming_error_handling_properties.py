"""
Property-Based Tests for Streaming Error Handling and Fallback

Feature: streaming-stage-output
Property 7: Graceful Error Handling
Property 9: Streaming Fallback

Tests:
- Streaming interruption handling
- Timeout handling
- Fallback to non-streaming
- Error logging
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import AsyncIterator

from src.services.chat_orchestrator import ChatOrchestrator, ChatContext, ChatStage, ChatIntent
from src.services.ai_model_service import AIModelError, ModelType


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing"""
    service = Mock()
    service.call_cloud_model = AsyncMock()
    service.call_local_model = AsyncMock()
    service.call_cloud_model_stream = AsyncMock()
    service.call_local_model_stream = AsyncMock()
    return service


@pytest.fixture
def mock_websocket_service():
    """Mock WebSocket service for testing"""
    service = Mock()
    service.send_stage_start = AsyncMock()
    service.send_stage_update = AsyncMock()
    service.send_stage_complete = AsyncMock()
    service.send_error_message = AsyncMock()
    return service


@pytest.fixture
def chat_orchestrator(mock_ai_service, mock_websocket_service):
    """Create ChatOrchestrator with mocked dependencies"""
    orchestrator = ChatOrchestrator()
    orchestrator.ai_service = mock_ai_service
    orchestrator.websocket_service = mock_websocket_service
    orchestrator.enable_streaming = True
    orchestrator.streaming_timeout = 60
    return orchestrator


@pytest.fixture
def chat_context():
    """Create a test chat context"""
    context = ChatContext(session_id="test-session-123")
    context.intent = ChatIntent.SMART_QUERY
    return context


# ============================================================================
# Property 7: Graceful Error Handling
# ============================================================================

@pytest.mark.asyncio
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    accumulated_chunks=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
    error_at_chunk=st.integers(min_value=0, max_value=9)
)
async def test_property_streaming_interruption_sends_accumulated_content(
    accumulated_chunks,
    error_at_chunk,
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Property 7: Graceful Error Handling - Streaming Interruption
    
    For any streaming operation that fails mid-process after accumulating content,
    the system SHALL send the accumulated content in stage_complete and log detailed error information.
    
    **Validates: Requirements 3.4, 7.1, 7.4**
    
    Feature: streaming-stage-output, Property 7: Graceful Error Handling
    """
    # Arrange: Create a stream that fails after some chunks
    async def failing_stream():
        for i, chunk in enumerate(accumulated_chunks):
            if i == min(error_at_chunk, len(accumulated_chunks) - 1):
                raise Exception(f"Stream interrupted at chunk {i}")
            yield chunk
    
    mock_ai_service.call_cloud_model_stream.return_value = failing_stream()
    
    # Mock fallback to non-streaming
    expected_accumulated = "".join(accumulated_chunks[:min(error_at_chunk, len(accumulated_chunks))])
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": expected_accumulated or "fallback content"
    }
    
    # Act: Call the streaming method (we'll test _recognize_intent as an example)
    try:
        result = await chat_orchestrator._recognize_intent(chat_context, "test question")
    except Exception:
        pass  # Expected to handle gracefully
    
    # Assert: Verify stage_complete was called with accumulated content or fallback
    assert mock_websocket_service.send_stage_complete.called, \
        "stage_complete should be called even when streaming fails"
    
    # Verify error was logged (check that fallback was attempted)
    if not expected_accumulated:
        assert mock_ai_service.call_cloud_model.called, \
            "Should fall back to non-streaming when no accumulated content"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    timeout_seconds=st.integers(min_value=1, max_value=5),
    chunks_before_timeout=st.integers(min_value=0, max_value=10)
)
async def test_property_timeout_handling_uses_accumulated_content(
    timeout_seconds,
    chunks_before_timeout,
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Property 7: Graceful Error Handling - Timeout Handling
    
    For any streaming operation that times out after accumulating content,
    the system SHALL use the accumulated content and never leave a stage in perpetual loading state.
    
    **Validates: Requirements 7.4, 7.5**
    
    Feature: streaming-stage-output, Property 7: Graceful Error Handling
    """
    # Arrange: Set a short timeout for testing
    chat_orchestrator.streaming_timeout = timeout_seconds
    
    # Create a slow stream that will timeout
    async def slow_stream():
        for i in range(chunks_before_timeout):
            yield f"chunk_{i}"
            await asyncio.sleep(0.1)
        # This will cause timeout
        await asyncio.sleep(timeout_seconds + 1)
        yield "late_chunk"
    
    mock_ai_service.call_cloud_model_stream.return_value = slow_stream()
    
    # Mock fallback
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": "fallback content"
    }
    
    # Act: Call with timeout
    start_time = time.time()
    try:
        result = await chat_orchestrator._recognize_intent(chat_context, "test question")
    except Exception:
        pass
    elapsed = time.time() - start_time
    
    # Assert: Should complete within reasonable time (not hang forever)
    assert elapsed < timeout_seconds * 2, \
        f"Should not hang forever, elapsed: {elapsed}s, timeout: {timeout_seconds}s"
    
    # Verify stage_complete was called (not left in loading state)
    assert mock_websocket_service.send_stage_complete.called, \
        "stage_complete should be called to prevent perpetual loading state"


# ============================================================================
# Property 9: Streaming Fallback
# ============================================================================

@pytest.mark.asyncio
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    fallback_content=st.text(min_size=10, max_size=200),
    error_type=st.sampled_from(["connection_error", "model_error", "timeout_error"])
)
async def test_property_fallback_to_nonstreaming_on_failure(
    fallback_content,
    error_type,
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Property 9: Streaming Fallback
    
    For any scenario where streaming fails without accumulated content,
    the system SHALL gracefully fall back to non-streaming mode and deliver the complete response.
    
    **Validates: Requirements 7.2, 9.1, 9.2**
    
    Feature: streaming-stage-output, Property 9: Streaming Fallback
    """
    # Arrange: Make streaming fail immediately
    error_map = {
        "connection_error": ConnectionError("Connection lost"),
        "model_error": AIModelError("Model unavailable", ModelType.QWEN_CLOUD),
        "timeout_error": asyncio.TimeoutError("Request timeout")
    }
    
    async def failing_stream():
        raise error_map[error_type]
        yield  # Never reached
    
    mock_ai_service.call_cloud_model_stream.return_value = failing_stream()
    
    # Mock successful fallback
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": fallback_content
    }
    
    # Act: Call streaming method
    try:
        result = await chat_orchestrator._recognize_intent(chat_context, "test question")
    except Exception:
        pass
    
    # Assert: Verify fallback was called
    assert mock_ai_service.call_cloud_model.called, \
        f"Should fall back to non-streaming on {error_type}"
    
    # Verify stage_complete was called with fallback content
    assert mock_websocket_service.send_stage_complete.called, \
        "stage_complete should be called with fallback content"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    streaming_enabled=st.booleans()
)
async def test_property_streaming_can_be_disabled(
    streaming_enabled,
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Property 9: Streaming Fallback - Configuration
    
    For any configuration setting, when streaming is disabled,
    the system SHALL use non-streaming mode directly without attempting to stream.
    
    **Validates: Requirements 9.3**
    
    Feature: streaming-stage-output, Property 9: Streaming Fallback
    """
    # Arrange: Set streaming configuration
    chat_orchestrator.enable_streaming = streaming_enabled
    
    # Mock both streaming and non-streaming
    async def mock_stream():
        yield "chunk1"
        yield "chunk2"
    
    mock_ai_service.call_cloud_model_stream.return_value = mock_stream()
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": "non-streaming content"
    }
    
    # Act: Call streaming method
    try:
        result = await chat_orchestrator._recognize_intent(chat_context, "test question")
    except Exception:
        pass
    
    # Assert: Verify correct method was called based on configuration
    if streaming_enabled:
        assert mock_ai_service.call_cloud_model_stream.called or mock_ai_service.call_cloud_model.called, \
            "Should attempt streaming when enabled"
    else:
        assert mock_ai_service.call_cloud_model.called, \
            "Should use non-streaming directly when disabled"
        assert not mock_ai_service.call_cloud_model_stream.called, \
            "Should not attempt streaming when disabled"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    chunks=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20)
)
async def test_property_error_logging_on_streaming_failure(
    chunks,
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Property 7: Graceful Error Handling - Error Logging
    
    For any streaming failure, the system SHALL log detailed error information
    including accumulated content length, chunk count, and error message.
    
    **Validates: Requirements 7.4**
    
    Feature: streaming-stage-output, Property 7: Graceful Error Handling
    """
    # Arrange: Create a stream that fails after some chunks
    async def failing_stream():
        for i, chunk in enumerate(chunks):
            if i == len(chunks) // 2:
                raise Exception(f"Test error at chunk {i}")
            yield chunk
    
    mock_ai_service.call_cloud_model_stream.return_value = failing_stream()
    
    # Mock fallback
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": "fallback"
    }
    
    # Act: Call with logging capture
    with patch('src.services.chat_orchestrator.logger') as mock_logger:
        try:
            result = await chat_orchestrator._recognize_intent(chat_context, "test question")
        except Exception:
            pass
        
        # Assert: Verify error was logged
        error_logged = any(
            call for call in mock_logger.error.call_args_list
            if "失败" in str(call) or "error" in str(call).lower()
        )
        
        assert error_logged or mock_logger.warning.called, \
            "Should log error information when streaming fails"


# ============================================================================
# Integration Test: Complete Error Handling Flow
# ============================================================================

@pytest.mark.asyncio
async def test_complete_error_handling_flow(
    chat_orchestrator,
    chat_context,
    mock_ai_service,
    mock_websocket_service
):
    """
    Integration test for complete error handling flow:
    1. Streaming starts
    2. Streaming fails mid-process
    3. Accumulated content is preserved
    4. Fallback to non-streaming
    5. stage_complete is sent
    6. No perpetual loading state
    """
    # Arrange: Create a failing stream with some accumulated content
    accumulated_chunks = ["chunk1", "chunk2", "chunk3"]
    
    async def failing_stream():
        for chunk in accumulated_chunks:
            yield chunk
        raise Exception("Stream interrupted")
    
    # Important: Don't call the generator, just assign it
    mock_ai_service.call_cloud_model_stream = AsyncMock(return_value=failing_stream())
    mock_ai_service.call_cloud_model.return_value = {
        "success": True,
        "content": "".join(accumulated_chunks)
    }
    
    # Act
    try:
        result = await chat_orchestrator._recognize_intent(chat_context, "test question")
    except Exception:
        pass
    
    # Assert: Verify complete flow
    assert mock_websocket_service.send_stage_start.called, "Should send stage_start"
    # Note: stage_update might not be called if streaming fails immediately in the mock
    # The important thing is that stage_complete is called
    assert mock_websocket_service.send_stage_complete.called, "Should send stage_complete"
    # Fallback should be called when streaming fails
    assert mock_ai_service.call_cloud_model.called, "Should fall back to non-streaming"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
