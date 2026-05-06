# 新消息组件使用示例

## 组件说明

### 1. ThinkingProcess.vue
展示 AI 的思考过程，类似 Figma 演示中的 "Deep Thinking Process"

### 2. HighlightedText.vue
对文本中的重要内容进行高亮显示（地区名称、百分比、数字等）

### 3. AIMessage.vue
完整的 AI 消息组件，整合了思考过程、文本描述和图表展示

---

## 使用方法

### 在 MessageStream.vue 中使用

```vue
<template>
  <div class="message-stream">
    <div v-for="message in messages" :key="message.id">
      <!-- 用户消息 -->
      <div v-if="message.role === 'user'" class="user-message">
        {{ message.content }}
      </div>
      
      <!-- AI 消息 -->
      <AIMessage
        v-else
        :thinking-steps="message.thinkingSteps"
        :thinking-time="message.thinkingTime"
        :text-content="message.textContent"
        :chart-data="message.chartData"
        :chart-type="message.chartType"
        :timestamp="message.timestamp"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import AIMessage from './AIMessage.vue'
// ...
</script>
```

---

## 数据结构示例

### 消息对象结构

```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  timestamp: Date
  
  // 用户消息
  content?: string
  
  // AI 消息
  thinkingSteps?: ThinkingStep[]
  thinkingTime?: string
  textContent?: string
  chartData?: ChartData
  chartType?: string
}

interface ThinkingStep {
  title: string              // 步骤标题，如 "Understand Question"
  type?: 'text' | 'sql'      // 内容类型
  content?: string           // 步骤内容
  status: 'pending' | 'running' | 'completed' | 'error'
}
```

### 完整示例数据

```typescript
const exampleMessage: Message = {
  id: 'msg_001',
  role: 'assistant',
  timestamp: new Date(),
  
  // 思考过程
  thinkingSteps: [
    {
      title: 'Understand Question',
      type: 'text',
      content: '用户询问上周各地区的游客数量',
      status: 'completed'
    },
    {
      title: 'Analyze Metrics',
      type: 'text',
      content: '需要分析：地区、游客数量、时间范围（上周）',
      status: 'completed'
    },
    {
      title: 'Generate SQL',
      type: 'sql',
      content: `SELECT region, 
       SUM(CASE WHEN date >= DATE('now', '-7 days') THEN visitor_count ELSE 0 END) as current_week,
       SUM(CASE WHEN date >= DATE('now', '-1 year', '-7 days') AND date < DATE('now', '-1 year') THEN visitor_count ELSE 0 END) as fy25_week
FROM park_attendance
WHERE region IN ('SH', 'NP', 'OC', 'INT', 'GC')
GROUP BY region;`,
      status: 'completed'
    },
    {
      title: 'Execute SQL',
      type: 'text',
      content: '查询成功，返回 5 条记录',
      status: 'completed'
    }
  ],
  thinkingTime: '1.4s',
  
  // 数据结果描述
  textContent: `Here is the attendance data for last week compared to FY25 across key regions.

<text>Shanghai (SH)</text> showed strong growth with a <num>+13.6%</num> YoY increase. <text>International (INT)</text> visitors also surged by <num>+10.5%</num>.

<text>Neighboring Provinces (NP)</text> and <text>Greater China (GC)</text> saw moderate gains of <num>+3.7%</num> and <num>+6.5%</num> respectively, while <text>Other China (OC)</text> experienced a slight decline of <num>-2.5%</num>.`,
  
  // 图表数据
  chartData: {
    title: 'Weekly Attendance by Region (vs FY25)',
    columns: ['Region', 'Current Week', 'FY25'],
    rows: [
      ['Shanghai', 12500, 11000],
      ['Neighboring Prov.', 8400, 8100],
      ['Other China', 15600, 16000],
      ['International', 4200, 3800],
      ['Greater China', 9800, 9200]
    ]
  },
  chartType: 'bar'
}
```

---

## 高亮规则说明

`HighlightedText.vue` 会自动识别并高亮模型输出的标记：

1. **数字标记**（红色加粗）
   - 格式：`<num>12,500</num>` 或 `<num>+13.6%</num>`
   - 效果：<span style="color: #ff4d4f; font-weight: 600;">12,500</span>
   - 用于：金额、百分比、数量、比率等所有数值

2. **文本标记**（蓝色加粗）
   - 格式：`<text>上海</text>` 或 `<text>进口食品</text>`
   - 效果：<span style="color: #1154cc; font-weight: 600;">上海</span>
   - 用于：地区名、产品名、类别名、指标名等关键业务术语

### 模型输出格式要求

后端模型在生成数据结果描述时，必须按照以下格式标记内容：

```
2023年各商品品类的销售额已通过数据查询得出。具体来看，<text>进口食品</text>的销售额最高，达到<num>XXX元</num>，占总销售额的<num>XX%</num>。其次是<text>国产食品</text>，销售额为<num>XXX元</num>。从数据可以看出，<text>进口食品</text>在2023年表现突出，销售额远超其他品类。
```

### Prompt 配置

在 `backend/src/services/chat_orchestrator.py` 的 `_describe_result` 方法中，已经配置了模型输出格式要求：

```python
⚠️ **重要格式要求**：
- 使用 `<num>数字</num>` 标记所有重要数值（如：<num>12,500</num>元、<num>+13.6%</num>）
- 使用 `<text>文本</text>` 标记所有重要文本（如：<text>上海</text>、<text>进口食品</text>）
- 不要标记普通的连接词、介词等（如"的"、"和"、"在"等）
- 数字包括：金额、百分比、数量、比率等
- 重要文本包括：地区名、产品名、类别名、指标名等关键业务术语
```

---

## 与后端集成

### 后端返回格式建议

```json
{
  "message_id": "msg_001",
  "role": "assistant",
  "timestamp": "2024-02-12T10:30:00Z",
  
  "thinking_process": {
    "steps": [
      {
        "title": "Understand Question",
        "type": "text",
        "content": "...",
        "status": "completed"
      },
      {
        "title": "Generate SQL",
        "type": "sql",
        "content": "SELECT ...",
        "status": "completed"
      }
    ],
    "total_time": "1.4s"
  },
  
  "result": {
    "description": "Here is the attendance data...",
    "chart": {
      "type": "bar",
      "data": {
        "title": "Weekly Attendance by Region",
        "columns": ["Region", "Current Week", "FY25"],
        "rows": [...]
      }
    }
  }
}
```

### 前端转换逻辑

```typescript
// 将后端数据转换为前端消息格式
function transformBackendMessage(backendMsg: any): Message {
  return {
    id: backendMsg.message_id,
    role: backendMsg.role,
    timestamp: new Date(backendMsg.timestamp),
    
    // 思考过程
    thinkingSteps: backendMsg.thinking_process?.steps || [],
    thinkingTime: backendMsg.thinking_process?.total_time,
    
    // 结果
    textContent: backendMsg.result?.description,
    chartData: backendMsg.result?.chart?.data,
    chartType: backendMsg.result?.chart?.type
  }
}
```

---

## 流式输出支持

如果需要支持流式输出（逐步显示思考过程），可以这样实现：

```typescript
// 在 Pinia Store 中
const currentMessage = ref<Message>({
  id: 'streaming',
  role: 'assistant',
  timestamp: new Date(),
  thinkingSteps: [],
  textContent: ''
})

// 接收流式数据
function handleStreamChunk(chunk: any) {
  if (chunk.type === 'thinking_step') {
    // 添加或更新思考步骤
    const existingIndex = currentMessage.value.thinkingSteps?.findIndex(
      s => s.title === chunk.step.title
    )
    
    if (existingIndex >= 0) {
      // 更新现有步骤
      currentMessage.value.thinkingSteps[existingIndex] = chunk.step
    } else {
      // 添加新步骤
      currentMessage.value.thinkingSteps?.push(chunk.step)
    }
  } else if (chunk.type === 'result_text') {
    // 追加文本内容
    currentMessage.value.textContent += chunk.text
  } else if (chunk.type === 'chart_data') {
    // 设置图表数据
    currentMessage.value.chartData = chunk.data
    currentMessage.value.chartType = chunk.chart_type
  }
}
```

---

## 样式定制

如果需要调整样式，可以修改各组件的 `<style scoped>` 部分：

### 调整思考过程颜色
```css
/* ThinkingProcess.vue */
.thinking-process {
  background: #f0f4f8; /* 改为浅蓝色背景 */
}
```

### 调整高亮颜色
```css
/* HighlightedText.vue */
:deep(.highlight-region) {
  color: #0066cc; /* 改为更深的蓝色 */
}
```

### 调整消息气泡样式
```css
/* AIMessage.vue */
.result-description {
  border-radius: 20px; /* 更圆润的边角 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); /* 更明显的阴影 */
}
```

---

## 注意事项

1. **去除数据分析 Stage**：不再需要单独的"数据分析"阶段，所有分析内容都在 `textContent` 中展示

2. **自动折叠**：思考过程完成后会自动折叠（延迟 500ms），用户可以手动展开查看

3. **文本高亮**：确保后端返回的文本使用 Markdown 格式（`**文本**`），前端会自动识别并高亮

4. **图表独立展示**：图表不再包在 Stage 中，直接在消息体中展示，更加清晰

5. **性能优化**：如果消息很多，建议使用虚拟滚动（VirtualList）来优化性能
