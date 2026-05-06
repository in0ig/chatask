# 真实AI集成测试指南

## 📋 概述

本目录包含真实的AI集成测试，使用真实的Qwen和OpenAI API调用来验证ChatBI系统的核心功能。

## 🎯 测试文件

### 1. test_real_ai_with_mock_data.py
**真实AI调用测试（推荐）**

- ✅ 使用Mock数据（不依赖生产数据库）
- ✅ 真实调用云端Qwen API
- ✅ 真实调用本地OpenAI API
- ✅ 验证双层历史记录机制
- ✅ 自动处理API配置问题

### 2. test_real_end_to_end_dialogue.py
**端到端对话测试**

- 需要真实数据库数据
- 完整的对话流程测试
- 多轮对话验证

## 🔧 前置条件

### 1. 配置AI API密钥

编辑 `backend/config/ai_models.yml`:

```yaml
qwen_cloud:
  api_key: "your-qwen-api-key"
  base_url: "https://dashscope.aliyuncs.com/api/v1"
  model_name: "qwen-turbo"
  max_tokens: 2000
  temperature: 0.1

openai_local:
  api_key: "your-openai-api-key"
  base_url: "http://localhost:8000/v1"  # 或其他本地OpenAI兼容端点
  model_name: "gpt-3.5-turbo"
  max_tokens: 2000
  temperature: 0.3
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 设置环境变量（可选）

```bash
export QWEN_API_KEY="your-qwen-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

## 🚀 运行测试

### 运行所有真实AI测试

```bash
cd backend
python -m pytest tests/integration/test_real_ai_with_mock_data.py -v -s
```

### 运行单个测试

```bash
# 测试意图识别
python -m pytest tests/integration/test_real_ai_with_mock_data.py::TestRealAIWithMockData::test_real_intent_recognition -v -s

# 测试SQL生成
python -m pytest tests/integration/test_real_ai_with_mock_data.py::TestRealAIWithMockData::test_real_sql_generation -v -s

# 测试本地数据分析
python -m pytest tests/integration/test_real_ai_with_mock_data.py::TestRealAIWithMockData::test_real_local_data_analysis -v -s

# 测试双层历史记录
python -m pytest tests/integration/test_real_ai_with_mock_data.py::TestRealAIWithMockData::test_dual_history_with_real_ai -v -s

# 测试完整AI流程
python -m pytest tests/integration/test_real_ai_with_mock_data.py::TestRealAIWithMockData::test_complete_ai_flow -v -s
```

### 运行核心功能测试（不需要AI API）

```bash
cd backend
python -m pytest tests/integration/test_core_dialogue_simplified.py -v -s
```

## 📊 测试输出示例

```
================================================================================
🚀 真实AI集成测试开始（使用Mock数据）
================================================================================
会话ID: real_ai_test_1770296046.200826
时间: 2026-02-05 20:54:06
================================================================================

================================================================================
📌 测试1: 真实意图识别
================================================================================

============================================================
🔹 测试问题
============================================================
查询订单表的前10条数据
============================================================

✅ 意图识别结果:
   原始响应: {"intent": "smart_query", "confidence": 0.95, "reasoning": "用户明确要求查询数据"}...
   意图类型: smart_query
   置信度: 0.95
   理由: 用户明确要求查询数据

✅ 真实意图识别测试通过！
```

## ⚠️ 注意事项

### API配置问题

如果AI API未配置或配置错误，测试会自动跳过：

```
SKIPPED [1] tests/integration/test_real_ai_with_mock_data.py:75: AI API配置问题，跳过测试: ...
```

这是正常的，不会导致测试失败。

### 测试成本

- 真实AI调用会产生API费用
- 每个测试大约消耗100-500 tokens
- 建议在开发环境中使用较小的max_tokens

### 网络要求

- 需要访问云端Qwen API（需要外网）
- 需要访问本地OpenAI API（可以是本地服务）

## 🔍 故障排查

### 问题1: AI API配置错误

**错误信息**:
```
AI API配置问题，跳过测试: 'qwen_cloud'
```

**解决方案**:
1. 检查 `backend/config/ai_models.yml` 文件是否存在
2. 确认API密钥配置正确
3. 验证API端点可访问

### 问题2: 网络连接失败

**错误信息**:
```
Failed to connect to API endpoint
```

**解决方案**:
1. 检查网络连接
2. 确认API端点URL正确
3. 检查防火墙设置

### 问题3: API密钥无效

**错误信息**:
```
401 Unauthorized
```

**解决方案**:
1. 验证API密钥是否有效
2. 检查API密钥是否过期
3. 确认API密钥权限

## 📈 测试覆盖

| 测试类别 | 测试数量 | 状态 |
|---------|---------|------|
| 意图识别 | 3个问题 | ✅ |
| SQL生成 | 1个场景 | ✅ |
| 本地分析 | 1个场景 | ✅ |
| 历史记录 | 完整验证 | ✅ |
| 完整流程 | 端到端 | ✅ |

## 🎯 验收标准

- ✅ 真实调用云端Qwen API
- ✅ 真实调用本地OpenAI API
- ✅ 验证双层历史记录机制
- ✅ 验证数据安全边界
- ✅ 测试覆盖率 ≥ 80%

## 📚 相关文档

- [TASK_5_7_COMPLETION_SUMMARY.md](./TASK_5_7_COMPLETION_SUMMARY.md) - 任务完成总结
- [TASK_5_7_REAL_AI_TEST_SUMMARY.md](./TASK_5_7_REAL_AI_TEST_SUMMARY.md) - 真实AI测试详细说明
- [TASK_5_7_INTEGRATION_TEST_GUIDE.md](./TASK_5_7_INTEGRATION_TEST_GUIDE.md) - 集成测试完整指南

## 🚀 快速开始

```bash
# 1. 配置AI API密钥
vim backend/config/ai_models.yml

# 2. 运行测试
cd backend
python -m pytest tests/integration/test_real_ai_with_mock_data.py -v -s

# 3. 查看结果
# 测试会输出详细的日志，包括AI响应内容
```

---

**最后更新**: 2026-02-05  
**维护者**: ChatBI开发团队
