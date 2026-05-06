# Streaming API Documentation

## Overview

The ChatBI streaming feature provides real-time progressive output for query processing stages. This document describes the streaming API methods, WebSocket protocol, and integration guidelines.

## AI Service Streaming Methods

### `call_cloud_model_stream()`

Streams content from cloud-based AI models (Qwen).

**Location**: `backend/src/services/ai_model_service.py`

**Signature**:
```python
async def call_cloud_model_stream(
    self, 
    prompt: str, 
    session_id: str = None, 
    **kwargs
) -> AsyncIterator[str]
```

**Parameters**:
- `prompt` (str): The prompt to send to the AI model
- `session_id` (str, optional): Session identifier for context tracking
- `**kwargs`: Additional parameters passed to the model adapter

**Returns**:
- `AsyncIterator[str]`: Yields content chunks as they're generated

**Example Usage**:
```python
accumulated_content = ""
async for chunk in ai_service.call_cloud_model_stream(prompt, session_id):
    accumulated_content += chunk
    # Send chunk to frontend via WebSocket
    await websocket_service.send_stage_update(session_id, stage_id, chunk)
```

**Error Handling**:
- Catches streaming exceptions and returns accumulated content
- Logs detailed error information for debugging
- Falls back to non-streaming mode if streaming is not supported

---

### `call_local_model_stream()`

Streams content from local AI models (OpenAI/Qwen).

**Location**: `backend/src/services/ai_model_service.py`

**Signature**:
```python
async def call_local_model_stream(
    self, 
    prompt: str, 
    session_id: str = None, 
    **kwargs
) -> AsyncIterator[str]
```

**Parameters**:
- `prompt` (str): The prompt to send to the AI model
- `session_id` (str, optional): Session identifier for context tracking
- `**kwargs`: Additional parameters passed to the model adapter

**Returns**:
- `AsyncIterator[str]`: Yields content chunks as they're generated

**Example Usage**:
```python
accumulated_content = ""
async for chunk in ai_service.call_local_model_stream(prompt, session_id):
    accumulated_content += chunk
    await websocket_service.send_stage_update(session_id, stage_id, chunk)
```

---

## WebSocket Message Protocol

### Message Types

The streaming protocol uses three message types:

1. **stage_start**: Indicates a stage has begun
2. **stage_update**: Delivers incremental content chunks
3. **stage_complete**: Marks stage completion with final result

### Message Format

#### `stage_start`

Sent when a processing stage begins.

```typescript
{
  type: "stage_start",
  stage_id: string,           // Unique stage identifier
  stage_name: string,         // Display name (e.g., "意图识别")
  content: "",                // Always empty for stage_start
  stage_status: "in_progress",
  collapsible: true,
  collapsed: false
}
```

**Example**:
```json
{
  "type": "stage_start",
  "stage_id": "intent_recognition",
  "stage_name": "意图识别",
  "content": "",
  "stage_status": "in_progress",
  "collapsible": true,
  "collapsed": false
}
```

---

#### `stage_update`

Sent for each content chunk during streaming.

```typescript
{
  type: "stage_update",
  stage_id: string,           // Stage identifier
  content: string,            // Incremental content chunk
  stage_status: "in_progress"
}
```

**Example**:
```json
{
  "type": "stage_update",
  "stage_id": "intent_recognition",
  "content": "用户想要查询",
  "stage_status": "in_progress"
}
```

**Important**: The frontend MUST append `content` to existing stage content, not replace it.

---

#### `stage_complete`

Sent when a stage finishes processing.

```typescript
{
  type: "stage_complete",
  stage_id: string,           // Stage identifier
  stage_name: string,         // Display name
  content: string,            // Final formatted result
  stage_status: "completed" | "error",
  collapsible: true,
  collapsed: true
}
```

**Example**:
```json
{
  "type": "stage_complete",
  "stage_id": "intent_recognition",
  "stage_name": "意图识别",
  "content": "**查询类型**: 订单统计\n**关键实体**: 张三",
  "stage_status": "completed",
  "collapsible": true,
  "collapsed": true
}
```

---

## Chat Orchestrator Integration

### Streaming Stages

The following stages use streaming:

1. **Intent Recognition** (`_recognize_intent`)
2. **SQL Generation** (`_generate_sql`)
3. **Data Analysis** (`_analyze_data`)

### Non-Streaming Stages

The following stages do NOT use streaming:

1. **Table Selection** (`_select_tables`) - Uses rule-based logic, not AI-generated
2. **SQL Execution** (`_execute_sql`) - Database query, not AI-generated

### Implementation Pattern

All streaming stages follow this pattern:

```python
async def _streaming_stage(self, params, session_id: str):
    stage_id = "stage_identifier"
    stage_name = "阶段名称"
    
    # 1. Send stage_start
    await self.websocket_service.send_stage_start(
        session_id=session_id,
        stage_id=stage_id,
        stage_name=stage_name,
        content=""
    )
    
    # 2. Stream content
    accumulated_content = ""
    try:
        async for chunk in self.ai_service.call_cloud_model_stream(prompt, session_id):
            accumulated_content += chunk
            await self.websocket_service.send_stage_update(
                session_id=session_id,
                stage_id=stage_id,
                content=chunk
            )
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        # Continue with accumulated content
    
    # 3. Parse and format result
    result = self._parse_response(accumulated_content)
    formatted_result = self._format_result(result)
    
    # 4. Send stage_complete
    await self.websocket_service.send_stage_complete(
        session_id=session_id,
        stage_id=stage_id,
        stage_name=stage_name,
        content=formatted_result
    )
    
    return result
```

---

## Configuration

### Backend Configuration

Enable/disable streaming via environment variable:

```bash
# .env
ENABLE_STREAMING=true  # Set to 'false' to disable streaming
```

**Default**: `true`

### Frontend Configuration

Enable/disable streaming via environment variable:

```bash
# .env
VITE_ENABLE_STREAMING=true  # Set to 'false' to disable streaming
```

**Default**: `true`

**Configuration File**: `frontend/src/config/streaming.ts`

```typescript
export const STREAMING_CONFIG = {
  enabled: import.meta.env.VITE_ENABLE_STREAMING !== 'false',
  chunkSize: 50,  // Characters per chunk (controlled by AI model)
  timeout: 60000  // 60 seconds
}
```

---

## Error Handling

### Streaming Interruption

**Scenario**: AI model stops streaming mid-response

**Handling**:
1. Exception is caught in the streaming loop
2. Error is logged with context (stage_id, accumulated content length)
3. `stage_complete` is sent with accumulated content
4. Stage status is marked as 'completed' (not 'error' if partial content exists)

**Example**:
```python
try:
    async for chunk in self.ai_service.call_cloud_model_stream(prompt, session_id):
        accumulated_content += chunk
        await self.websocket_service.send_stage_update(session_id, stage_id, chunk)
except Exception as e:
    logger.error(f"🔴 Streaming interrupted for stage {stage_id}: {str(e)}")
    await self.websocket_service.send_stage_complete(
        session_id, stage_id, stage_name, 
        accumulated_content or "处理过程中断，请重试"
    )
```

### WebSocket Connection Loss

**Scenario**: Client disconnects during streaming

**Handling**:
1. WebSocket service detects disconnection
2. Pending messages are stored in connection's queue
3. When client reconnects, messages are resent
4. Frontend requests missing stages if needed

### AI Model Timeout

**Scenario**: AI model takes too long to respond

**Handling**:
1. Timeout is set on streaming operations (60 seconds)
2. If timeout occurs, `stage_complete` is sent with timeout message
3. Timeout is logged for monitoring
4. User can retry the query

---

## Performance Considerations

### Chunk Size

- AI models control chunk size (typically 10-50 characters)
- No additional buffering in backend code
- Natural AI model pacing determines streaming speed

### WebSocket Message Rate

- No artificial throttling on backend
- Frontend uses `requestAnimationFrame` for smooth updates
- Multiple chunks batched if they arrive within same frame

### Memory Management

- Maximum token limit: 2000 tokens per response
- Accumulated content cleared after stage completes
- Streaming avoids holding full response in memory twice

---

## Monitoring and Logging

### Log Levels

**Backend Logs**:
```python
logger.info(f"🌊 Streaming started: stage={stage_id}, session={session_id}")
logger.debug(f"📦 Chunk sent: stage={stage_id}, size={len(chunk)}")
logger.info(f"✅ Streaming completed: stage={stage_id}, chunks={count}, duration={duration}s")
logger.error(f"❌ Streaming failed: stage={stage_id}, error={str(e)}")
```

**Frontend Logs**:
```typescript
console.log(`🌊 Stage streaming started: ${stage_id}`)
console.debug(`📦 Chunk received: ${stage_id}, size: ${chunk.length}`)
console.log(`✅ Stage completed: ${stage_id}, total_content: ${content.length}`)
console.error(`❌ Streaming error: ${stage_id}, error: ${error}`)
```

### Metrics to Track

1. **Performance Metrics**:
   - Average time to first chunk
   - Average chunk delivery rate
   - Total streaming duration per stage
   - Streaming success rate

2. **Error Metrics**:
   - Streaming interruption rate
   - WebSocket disconnection rate
   - Timeout rate
   - Fallback activation rate

---

## Testing

### Unit Tests

**Backend**:
- `backend/tests/unit/test_ai_service_streaming.py`
- `backend/tests/unit/test_chat_orchestrator_streaming.py`

**Frontend**:
- `frontend/tests/unit/test_chat_store_streaming.spec.ts`
- `frontend/tests/unit/test_collapsible_stage.spec.ts`

### Property-Based Tests

**Backend**:
- `backend/tests/unit/test_streaming_properties.py`
- `backend/tests/unit/test_streaming_error_handling_properties.py`

**Frontend**:
- `frontend/tests/unit/store/chat.streaming-properties.test.ts`

### Integration Tests

- `backend/tests/integration/test_streaming_e2e.py`
- `backend/tests/integration/test_streaming_protocol_properties.py`

### Performance Tests

- `backend/tests/performance/test_streaming_performance.py`

---

## Security Considerations

### Content Validation

- All content is sanitized before displaying in frontend
- Vue's built-in XSS protection is used
- Message format is validated on frontend

### Rate Limiting

- Existing rate limiting applies to streaming endpoints
- WebSocket connection count per user is monitored
- Maximum concurrent streaming operations is enforced

### WebSocket Security

- WSS (WebSocket Secure) is used in production
- Session tokens are validated on WebSocket connection
- CORS policies are implemented
- WebSocket messages are rate limited

---

## Backward Compatibility

### Non-Breaking Changes

1. All existing API methods remain functional
2. Stages can opt-in to streaming individually
3. New message types don't break existing handlers
4. Falls back to non-streaming if errors occur

### Migration Path

1. Streaming support added alongside existing code
2. Streaming enabled for one stage at a time
3. Each stage monitored and validated
4. All stages gradually enabled
5. Old non-streaming code paths can be removed (optional)

---

## Troubleshooting

### Issue: Streaming not working

**Symptoms**: Content appears all at once instead of progressively

**Solutions**:
1. Check `ENABLE_STREAMING` environment variable is set to `true`
2. Verify WebSocket connection is established
3. Check browser console for errors
4. Verify AI model supports streaming

### Issue: Content appears jumbled or out of order

**Symptoms**: Stage content is incorrect or duplicated

**Solutions**:
1. Verify frontend is appending content, not replacing
2. Check `stage_id` matches between messages
3. Verify message ordering in WebSocket handler
4. Check for race conditions in state management

### Issue: Stages stuck in "loading" state

**Symptoms**: Stage never completes, shows loading indicator indefinitely

**Solutions**:
1. Check backend logs for streaming errors
2. Verify `stage_complete` message is sent
3. Check for timeout issues (increase timeout if needed)
4. Verify error handling is working correctly

---

## API Reference Summary

| Method | Location | Purpose |
|--------|----------|---------|
| `call_cloud_model_stream()` | `ai_model_service.py` | Stream from cloud AI models |
| `call_local_model_stream()` | `ai_model_service.py` | Stream from local AI models |
| `send_stage_start()` | `websocket_stream_service.py` | Send stage start message |
| `send_stage_update()` | `websocket_stream_service.py` | Send content chunk |
| `send_stage_complete()` | `websocket_stream_service.py` | Send stage completion |
| `handleStageUpdate()` | `chat.ts` (Pinia store) | Handle stage update in frontend |

---

## Version History

- **v1.0.0** (2026-02-10): Initial streaming implementation
  - Added streaming methods to AI service
  - Implemented WebSocket protocol
  - Added frontend state management
  - Comprehensive testing suite
