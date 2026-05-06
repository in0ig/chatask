# ChatBI 性能测试框架

## 概述

本目录包含 ChatBI 增强功能的性能测试，用于验证系统是否满足性能基准要求。

## 性能基准

根据 `tasks.md` 中的要求，系统需要满足以下性能指标：

| 操作 | 基准时间 | 测试文件 |
|------|---------|---------|
| Token 计数 | < 100ms | `test_token_performance.py` |
| 上下文总结 | < 5s | `test_context_performance.py` |
| 消息保存 | < 100ms | `test_message_performance.py` |
| 对话历史检索 | < 500ms | `test_message_performance.py` |
| 流式首个 chunk | < 3s | `test_streaming_performance.py` |
| 流式 chunk 速率 | > 10 chunks/s | `test_streaming_performance.py` |
| Stage 总流式时间 | < 30s | `test_streaming_performance.py` |

## 运行性能测试

### 运行所有性能测试

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/performance/ -v
```

### 运行特定测试文件

```bash
# Token 计数性能测试
python -m pytest tests/performance/test_token_performance.py -v

# 上下文总结性能测试
python -m pytest tests/performance/test_context_performance.py -v

# 消息保存和检索性能测试
python -m pytest tests/performance/test_message_performance.py -v
```

### 显示详细输出

```bash
python -m pytest tests/performance/ -v -s
```

## 测试文件说明

### test_token_performance.py

测试 Token 计数相关的性能：
- `test_token_count_small_messages_performance`: 小量消息的 Token 计数
- `test_token_count_large_messages_performance`: 大量消息的 Token 计数
- `test_token_count_alibaba_model_performance`: 阿里云模型的 Token 计数
- `test_check_token_limit_performance`: Token 限制检查

### test_context_performance.py

测试上下文总结相关的性能：
- `test_should_summarize_check_performance`: 总结触发检查
- `test_summarize_context_performance`: 上下文总结本地处理
- `test_save_summary_performance`: 保存总结
- `test_context_update_performance`: 上下文更新

### test_message_performance.py

测试消息保存和检索相关的性能：
- `test_add_message_performance`: 添加消息
- `test_batch_add_messages_performance`: 批量添加消息
- `test_get_conversation_history_performance`: 获取对话历史
- `test_get_conversation_history_with_limit_performance`: 带限制的对话历史检索
- `test_get_last_message_performance`: 获取最后一条消息
- `test_concurrent_message_operations`: 并发消息操作

### test_streaming_performance.py

测试流式输出相关的性能：
- `test_cloud_model_streaming_performance`: 云端模型流式性能
- `test_local_model_streaming_performance`: 本地模型流式性能
- `test_intent_recognition_streaming_performance`: 意图识别 stage 流式性能
- `test_stage_update_message_overhead`: WebSocket 消息开销
- `test_complete_query_streaming_performance`: 端到端流式性能
- `test_identify_bottlenecks`: 性能瓶颈识别

详细性能报告请参考: [STREAMING_PERFORMANCE_REPORT.md](./STREAMING_PERFORMANCE_REPORT.md)

## 性能监控工具

### 使用装饰器

```python
from src.utils.performance import measure_time, memory_profile

@measure_time
def my_function():
    # 函数代码
    pass

@memory_profile
def memory_intensive_function():
    # 函数代码
    pass
```

### 使用 PerformanceMetrics

```python
from src.utils.performance import performance_metrics

# 添加指标
performance_metrics.add_metric("operation_time", 0.05)

# 获取报告
report = performance_metrics.get_report()
print(report)
```

## 待优化项

以下是已识别的潜在优化点：

### 高优先级

1. **Token 计数缓存**
   - 对于相同的消息内容，可以缓存 Token 计数结果
   - 预期改进：减少 50% 的重复计算

2. **批量消息保存**
   - 实现批量插入而不是逐条插入
   - 预期改进：减少数据库往返次数

### 中优先级

3. **对话历史分页**
   - 实现分页加载而不是一次性加载所有历史
   - 预期改进：减少内存使用和响应时间

4. **上下文总结异步处理**
   - 将总结操作移到后台任务
   - 预期改进：不阻塞用户交互

### 低优先级

5. **消息压缩**
   - 对长消息进行压缩存储
   - 预期改进：减少存储空间

6. **连接池优化**
   - 优化数据库连接池配置
   - 预期改进：减少连接建立时间

## 性能测试最佳实践

1. **预热**：在测量前运行一次预热，避免冷启动影响
2. **多次运行**：运行多次取平均值，减少随机波动
3. **隔离测试**：每个测试独立运行，避免相互影响
4. **真实数据**：使用接近生产环境的数据量进行测试
5. **监控资源**：同时监控 CPU、内存、I/O 等资源使用

## 注意事项

- 性能测试结果可能因硬件环境不同而有所差异
- 建议在与生产环境相似的硬件上运行性能测试
- 某些测试（如上下文总结）需要 LLM 服务，测试中使用 Mock 替代
- 并发测试可能受系统资源限制影响
