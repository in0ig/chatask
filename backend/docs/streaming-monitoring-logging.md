# Streaming Monitoring and Logging Guide

## Overview

This document describes the monitoring and logging strategy for the ChatBI streaming feature. It covers metrics to track, log formats, alerting rules, and troubleshooting procedures.

## Logging Strategy

### Log Levels

The streaming feature uses standard Python logging levels:

- **DEBUG**: Detailed information for diagnosing problems (chunk details, state changes)
- **INFO**: General informational messages (streaming start/complete, performance metrics)
- **WARNING**: Warning messages for recoverable issues (slow streaming, retries)
- **ERROR**: Error messages for failures (streaming interruption, timeout)
- **CRITICAL**: Critical issues requiring immediate attention (system failures)

### Backend Logging

#### Log Format

```python
# Standard log format
[TIMESTAMP] [LEVEL] [MODULE] [SESSION_ID] MESSAGE

# Example
[2026-02-10 14:30:45] [INFO] [chat_orchestrator] [sess_abc123] 🌊 Streaming started: stage=intent_recognition
```

#### Streaming Lifecycle Logs

**Streaming Start**:
```python
logger.info(
    f"🌊 Streaming started: stage={stage_id}, session={session_id}, "
    f"prompt_length={len(prompt)}"
)
```

**Chunk Sent**:
```python
logger.debug(
    f"📦 Chunk sent: stage={stage_id}, chunk_size={len(chunk)}, "
    f"total_accumulated={len(accumulated_content)}"
)
```

**Streaming Complete**:
```python
logger.info(
    f"✅ Streaming completed: stage={stage_id}, "
    f"total_chunks={chunk_count}, "
    f"total_size={len(accumulated_content)}, "
    f"duration={duration:.2f}s, "
    f"avg_chunk_size={avg_chunk_size:.1f}"
)
```

**Streaming Error**:
```python
logger.error(
    f"❌ Streaming failed: stage={stage_id}, "
    f"error={str(e)}, "
    f"accumulated_content_length={len(accumulated_content)}, "
    f"chunks_received={chunk_count}",
    exc_info=True
)
```

#### WebSocket Logs

**Connection Established**:
```python
logger.info(f"🔌 WebSocket connected: session={session_id}, client_ip={client_ip}")
```

**Message Sent**:
```python
logger.debug(
    f"📤 WebSocket message sent: type={message_type}, "
    f"stage_id={stage_id}, "
    f"content_length={len(content)}"
)
```

**Connection Closed**:
```python
logger.info(
    f"🔌 WebSocket disconnected: session={session_id}, "
    f"duration={duration:.2f}s, "
    f"messages_sent={message_count}"
)
```

**Connection Error**:
```python
logger.error(
    f"❌ WebSocket error: session={session_id}, error={str(e)}",
    exc_info=True
)
```

#### AI Service Logs

**Model Call Start**:
```python
logger.info(
    f"🤖 AI model call started: model={model_name}, "
    f"streaming={is_streaming}, "
    f"prompt_tokens={prompt_tokens}"
)
```

**Model Call Complete**:
```python
logger.info(
    f"🤖 AI model call completed: model={model_name}, "
    f"response_tokens={response_tokens}, "
    f"duration={duration:.2f}s, "
    f"tokens_per_second={tokens_per_second:.1f}"
)
```

**Model Error**:
```python
logger.error(
    f"❌ AI model error: model={model_name}, "
    f"error={str(e)}, "
    f"retry_count={retry_count}",
    exc_info=True
)
```

### Frontend Logging

#### Console Log Format

```typescript
// Standard format
[TIMESTAMP] [LEVEL] [COMPONENT] MESSAGE

// Example
[14:30:45.123] [INFO] [ChatStore] 🌊 Stage streaming started: intent_recognition
```

#### Streaming Lifecycle Logs

**Streaming Start**:
```typescript
console.log(
  `🌊 Stage streaming started: ${stage_id}, ` +
  `message_id: ${message_id}`
)
```

**Chunk Received**:
```typescript
console.debug(
  `📦 Chunk received: ${stage_id}, ` +
  `size: ${chunk.length}, ` +
  `total: ${stage.content.length}`
)
```

**Streaming Complete**:
```typescript
console.log(
  `✅ Stage completed: ${stage_id}, ` +
  `total_content: ${stage.content.length}, ` +
  `chunks_received: ${chunk_count}`
)
```

**Streaming Error**:
```typescript
console.error(
  `❌ Streaming error: ${stage_id}, ` +
  `error: ${error.message}`,
  error
)
```

#### WebSocket Logs

**Connection Established**:
```typescript
console.log(`🔌 WebSocket connected: ${websocket.url}`)
```

**Message Received**:
```typescript
console.debug(
  `📥 WebSocket message received: type=${message.type}, ` +
  `stage_id=${message.stage_id}`
)
```

**Connection Closed**:
```typescript
console.log(`🔌 WebSocket disconnected: code=${code}, reason=${reason}`)
```

**Connection Error**:
```typescript
console.error(`❌ WebSocket error:`, error)
```

## Metrics to Track

### Performance Metrics

#### 1. Time to First Chunk (TTFC)

**Definition**: Time from streaming start to first chunk received

**Target**: < 3 seconds

**Measurement**:
```python
ttfc = first_chunk_timestamp - streaming_start_timestamp
logger.info(f"⏱️ TTFC: {ttfc:.2f}s for stage={stage_id}")
```

**Alert**: If TTFC > 5 seconds for > 10% of requests

#### 2. Chunk Delivery Rate

**Definition**: Average time between chunks

**Target**: 50-200ms per chunk

**Measurement**:
```python
chunk_rate = total_duration / chunk_count
logger.info(f"📊 Chunk rate: {chunk_rate:.2f}ms for stage={stage_id}")
```

**Alert**: If chunk rate > 500ms for > 10% of requests

#### 3. Total Streaming Duration

**Definition**: Time from streaming start to completion

**Target**: < 30 seconds per stage

**Measurement**:
```python
duration = streaming_end_timestamp - streaming_start_timestamp
logger.info(f"⏱️ Total duration: {duration:.2f}s for stage={stage_id}")
```

**Alert**: If duration > 60 seconds (timeout threshold)

#### 4. Streaming Success Rate

**Definition**: Percentage of successful streaming operations

**Target**: > 95%

**Measurement**:
```python
success_rate = successful_streams / total_streams * 100
logger.info(f"📊 Streaming success rate: {success_rate:.1f}%")
```

**Alert**: If success rate < 90%

### Error Metrics

#### 1. Streaming Interruption Rate

**Definition**: Percentage of streams interrupted mid-process

**Target**: < 2%

**Measurement**:
```python
interruption_rate = interrupted_streams / total_streams * 100
logger.warning(f"⚠️ Interruption rate: {interruption_rate:.1f}%")
```

**Alert**: If interruption rate > 5%

#### 2. WebSocket Disconnection Rate

**Definition**: Percentage of WebSocket connections that disconnect unexpectedly

**Target**: < 5%

**Measurement**:
```python
disconnection_rate = unexpected_disconnections / total_connections * 100
logger.warning(f"⚠️ Disconnection rate: {disconnection_rate:.1f}%")
```

**Alert**: If disconnection rate > 10%

#### 3. Timeout Rate

**Definition**: Percentage of streams that timeout

**Target**: < 1%

**Measurement**:
```python
timeout_rate = timed_out_streams / total_streams * 100
logger.warning(f"⚠️ Timeout rate: {timeout_rate:.1f}%")
```

**Alert**: If timeout rate > 3%

#### 4. Fallback Activation Rate

**Definition**: Percentage of streams that fall back to non-streaming

**Target**: < 1%

**Measurement**:
```python
fallback_rate = fallback_activations / total_streams * 100
logger.info(f"📊 Fallback rate: {fallback_rate:.1f}%")
```

**Alert**: If fallback rate > 5%

### User Experience Metrics

#### 1. Stage Completion Time

**Definition**: Time for each stage to complete

**Measurement**:
```python
stage_times = {
    'intent_recognition': [],
    'sql_generation': [],
    'data_analysis': []
}
logger.info(f"📊 Avg stage times: {avg_stage_times}")
```

#### 2. User Engagement

**Definition**: User interactions during streaming (scroll, collapse/expand)

**Measurement**:
```typescript
console.log(`📊 User interactions: ${interaction_count} during streaming`)
```

#### 3. Query Completion Rate

**Definition**: Percentage of queries that complete successfully

**Target**: > 98%

**Measurement**:
```python
completion_rate = completed_queries / total_queries * 100
logger.info(f"📊 Query completion rate: {completion_rate:.1f}%")
```

## Monitoring Dashboard

### Key Metrics to Display

1. **Real-time Metrics**:
   - Active streaming sessions
   - Current TTFC (average)
   - Current chunk delivery rate
   - Active WebSocket connections

2. **Historical Metrics** (last 24 hours):
   - Total streaming operations
   - Success rate trend
   - Error rate trend
   - Average duration per stage

3. **Error Tracking**:
   - Recent errors (last 100)
   - Error rate by type
   - Most common error messages
   - Affected sessions

4. **Performance Trends**:
   - TTFC over time
   - Chunk delivery rate over time
   - Streaming duration distribution
   - Success rate over time

### Recommended Tools

- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **ELK Stack**: Log aggregation and analysis
- **Sentry**: Error tracking and alerting

## Alerting Rules

### Critical Alerts (Immediate Action Required)

1. **Streaming Success Rate < 80%**
   - Severity: Critical
   - Action: Investigate immediately, consider disabling streaming

2. **WebSocket Disconnection Rate > 20%**
   - Severity: Critical
   - Action: Check WebSocket server, network issues

3. **Timeout Rate > 10%**
   - Severity: Critical
   - Action: Check AI model performance, increase timeout

### Warning Alerts (Monitor Closely)

1. **TTFC > 5 seconds for > 10% of requests**
   - Severity: Warning
   - Action: Investigate AI model latency

2. **Chunk Delivery Rate > 500ms**
   - Severity: Warning
   - Action: Check network performance, AI model speed

3. **Interruption Rate > 5%**
   - Severity: Warning
   - Action: Investigate streaming stability

### Info Alerts (Informational)

1. **Fallback Activation Rate > 5%**
   - Severity: Info
   - Action: Monitor, may indicate AI model issues

2. **Average Streaming Duration > 20 seconds**
   - Severity: Info
   - Action: Consider optimization opportunities

## Troubleshooting Procedures

### High TTFC (Time to First Chunk)

**Symptoms**: First chunk takes > 5 seconds to arrive

**Investigation Steps**:
1. Check AI model response time in logs
2. Verify network latency between backend and AI service
3. Check AI service load and queue length
4. Review prompt complexity and length

**Solutions**:
- Optimize prompts to reduce processing time
- Scale AI service if overloaded
- Implement caching for common queries
- Consider using faster AI model

### High Interruption Rate

**Symptoms**: Streams frequently interrupted mid-process

**Investigation Steps**:
1. Check AI model error logs
2. Verify network stability
3. Review timeout settings
4. Check for resource constraints (memory, CPU)

**Solutions**:
- Increase timeout if legitimate long-running queries
- Fix AI model stability issues
- Improve error handling and retry logic
- Scale resources if constrained

### High WebSocket Disconnection Rate

**Symptoms**: WebSocket connections frequently drop

**Investigation Steps**:
1. Check WebSocket server logs
2. Verify network stability
3. Review load balancer configuration
4. Check client-side connection handling

**Solutions**:
- Implement WebSocket reconnection logic
- Adjust load balancer timeout settings
- Fix network issues
- Improve client-side error handling

### Slow Chunk Delivery

**Symptoms**: Long delays between chunks

**Investigation Steps**:
1. Check AI model streaming performance
2. Verify network bandwidth
3. Review backend processing overhead
4. Check for bottlenecks in message queue

**Solutions**:
- Optimize AI model streaming
- Increase network bandwidth
- Reduce backend processing overhead
- Scale WebSocket servers

## Log Retention and Rotation

### Retention Policy

- **DEBUG logs**: 7 days
- **INFO logs**: 30 days
- **WARNING logs**: 90 days
- **ERROR logs**: 180 days
- **CRITICAL logs**: 365 days

### Rotation Strategy

- **Daily rotation**: Logs rotated at midnight UTC
- **Size-based rotation**: Rotate when log file exceeds 100MB
- **Compression**: Rotated logs compressed with gzip
- **Backup**: Logs backed up to S3 or equivalent

### Log File Locations

**Backend**:
- Main log: `/var/log/chatbi/backend.log`
- Streaming log: `/var/log/chatbi/streaming.log`
- Error log: `/var/log/chatbi/error.log`

**Frontend** (browser console):
- Logs stored in browser memory
- Can be exported for debugging
- Not persisted by default

## Performance Benchmarks

### Baseline Performance (Expected)

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| TTFC | < 2s | < 3s | > 5s |
| Chunk Rate | 50-200ms | 200-500ms | > 500ms |
| Total Duration | < 20s | < 30s | > 60s |
| Success Rate | > 98% | > 95% | < 90% |
| Interruption Rate | < 1% | < 2% | > 5% |
| Disconnection Rate | < 3% | < 5% | > 10% |
| Timeout Rate | < 0.5% | < 1% | > 3% |

### Load Testing Results

**Test Configuration**:
- Concurrent users: 100
- Query rate: 10 queries/second
- Test duration: 10 minutes

**Expected Results**:
- TTFC: 2.5s (average)
- Success rate: 97%
- Error rate: 3%
- Average duration: 25s per query

## Security Monitoring

### Security Events to Log

1. **Authentication Failures**:
   ```python
   logger.warning(f"🔒 Auth failed: session={session_id}, ip={client_ip}")
   ```

2. **Rate Limit Exceeded**:
   ```python
   logger.warning(f"⚠️ Rate limit exceeded: session={session_id}, ip={client_ip}")
   ```

3. **Suspicious Activity**:
   ```python
   logger.warning(f"🚨 Suspicious activity: session={session_id}, reason={reason}")
   ```

4. **Data Access**:
   ```python
   logger.info(f"🔍 Data accessed: session={session_id}, tables={tables}")
   ```

### Security Alerts

1. **Multiple Authentication Failures**:
   - Threshold: > 5 failures in 5 minutes
   - Action: Block IP temporarily

2. **Unusual Query Patterns**:
   - Threshold: > 100 queries in 1 minute
   - Action: Investigate for abuse

3. **Data Exfiltration Attempts**:
   - Threshold: Large result sets (> 10,000 rows)
   - Action: Review and alert security team

## Compliance and Audit

### Audit Log Requirements

1. **User Actions**:
   - Query submissions
   - Data access
   - Configuration changes

2. **System Events**:
   - Streaming operations
   - Errors and failures
   - Performance degradation

3. **Security Events**:
   - Authentication attempts
   - Authorization failures
   - Suspicious activity

### Audit Log Format

```json
{
  "timestamp": "2026-02-10T14:30:45.123Z",
  "event_type": "streaming_started",
  "session_id": "sess_abc123",
  "user_id": "user_123",
  "stage_id": "intent_recognition",
  "metadata": {
    "prompt_length": 150,
    "model": "qwen-plus"
  }
}
```

### Compliance Requirements

- **GDPR**: Personal data in logs must be anonymized
- **SOC 2**: Audit logs must be tamper-proof
- **HIPAA**: PHI must not be logged (if applicable)

## Continuous Improvement

### Regular Reviews

1. **Weekly**: Review error rates and performance trends
2. **Monthly**: Analyze user experience metrics
3. **Quarterly**: Comprehensive performance review and optimization

### Optimization Opportunities

1. **Identify Bottlenecks**: Use metrics to find slow stages
2. **Optimize Prompts**: Reduce AI processing time
3. **Improve Caching**: Cache common queries
4. **Scale Resources**: Add capacity where needed

### Feedback Loop

1. **Collect Metrics**: Continuous monitoring
2. **Analyze Trends**: Identify patterns and issues
3. **Implement Fixes**: Address identified problems
4. **Measure Impact**: Verify improvements

---

**Version**: 1.0.0  
**Last Updated**: February 10, 2026  
**Next Review**: March 10, 2026
