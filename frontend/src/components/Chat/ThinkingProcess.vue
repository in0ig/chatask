<template>
  <div class="thinking-process">
    <!-- 思考过程标题栏（可折叠） -->
    <div class="thinking-header" @click="toggleCollapse">
      <div class="header-left">
        <span class="thinking-icon">🧠</span>
        <span class="thinking-title">{{ $t('thinking.title') }}</span>
        <span class="thinking-time">{{ totalTime }}</span>
      </div>
      <span class="collapse-icon" :class="{ collapsed: isCollapsed }">
        {{ isCollapsed ? '▶' : '▼' }}
      </span>
    </div>

    <!-- 思考步骤列表 -->
    <transition name="collapse">
      <div v-show="!isCollapsed" class="thinking-content">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          class="thinking-step"
        >
          <!-- 步骤标题（可点击折叠步骤内容） -->
          <div 
            class="step-header"
            :class="{ clickable: !!step.content }"
            @click="step.content ? toggleStep(index) : null"
          >
            <span class="step-icon" :class="getStepStatusClass(step.status)">
              {{ getStepIcon(step.status) }}
            </span>
            <span class="step-title">{{ step.title }}</span>
            <!-- 步骤折叠箭头（仅在有内容时显示） -->
            <span v-if="step.content" class="step-collapse-icon" :class="{ collapsed: collapsedSteps[index] }">
              ▾
            </span>
          </div>

          <!-- 步骤内容（可折叠） -->
          <transition name="step-collapse">
            <div v-if="step.content && !collapsedSteps[index]" class="step-content">
              <!-- SQL 代码块 -->
              <div v-if="step.type === 'sql'" class="sql-block">
                <pre><code>{{ cleanSqlContent(step.content) }}</code></pre>
              </div>
              
              <!-- 模型思考：内容是 markdown，用 v-html 渲染 -->
              <div v-else-if="step.title === '模型思考'" class="text-content markdown-content" v-html="renderMarkdown(step.content)">
              </div>
              
              <!-- 普通文本：过滤掉原始 JSON，只展示有意义的文字 -->
              <div v-else class="text-content">
                {{ extractDisplayText(step.content, step.title) }}
              </div>
            </div>
          </transition>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

// 步骤接口
interface ThinkingStep {
  title: string
  type?: 'text' | 'sql'
  content?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

// Props
const props = defineProps<{
  steps: ThinkingStep[]
  totalTime?: string
  autoCollapse?: boolean // 完成后自动折叠
  collapsed?: boolean // 外部控制折叠状态
}>()

// 整体折叠状态
const isCollapsed = ref(props.collapsed || false)

// 每个步骤的折叠状态（key: 步骤 index，value: 是否折叠）
const collapsedSteps = ref<Record<number, boolean>>({})

// 内部追踪上一次各步骤的状态（用于检测 running → completed 转变）
const prevStatuses = ref<string[]>([])

// 监听外部 collapsed prop 的变化
watch(() => props.collapsed, (newValue) => {
  if (newValue !== undefined) {
    isCollapsed.value = newValue
  }
})

// 初始化：有内容的步骤默认折叠（历史消息场景，仅在挂载时执行一次）
onMounted(() => {
  const initial: Record<number, boolean> = {}
  props.steps.forEach((step, index) => {
    if (step.content && collapsedSteps.value[index] === undefined) {
      initial[index] = true
    }
  })
  if (Object.keys(initial).length > 0) {
    collapsedSteps.value = { ...collapsedSteps.value, ...initial }
  }
  // 初始化 prevStatuses
  prevStatuses.value = props.steps.map(s => s.status)
})

// 监听步骤状态变化：步骤从 running 变为 completed 时自动折叠
// 使用内部 prevStatuses 追踪，避免 watch oldValue 在新数组引用时不可靠的问题
watch(
  () => props.steps.map(s => s.status),
  (newStatuses) => {
    const updates: Record<number, boolean> = {}
    newStatuses.forEach((status, index) => {
      const oldStatus = prevStatuses.value[index]
      // running → completed：自动折叠
      if (oldStatus === 'running' && status === 'completed') {
        updates[index] = true
      }
      // 新增步骤且有内容：默认折叠（处理历史消息中新增步骤的情况）
      if (oldStatus === undefined && status === 'completed' && props.steps[index]?.content) {
        updates[index] = true
      }
    })
    if (Object.keys(updates).length > 0) {
      collapsedSteps.value = { ...collapsedSteps.value, ...updates }
    }
    // 更新 prevStatuses
    prevStatuses.value = [...newStatuses]
  },
  { deep: true }
)

// 计算总时间
const totalTime = computed(() => {
  return props.totalTime || '1.4s'
})

// 切换整体折叠
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 切换单个步骤折叠
const toggleStep = (index: number) => {
  collapsedSteps.value = {
    ...collapsedSteps.value,
    [index]: !collapsedSteps.value[index]
  }
}

// 获取步骤状态图标
const getStepIcon = (status: string) => {
  const icons = {
    pending: '⏸',
    running: '⏳',
    completed: '✅',
    error: '❌'
  }
  return icons[status as keyof typeof icons] || '⏸'
}

// 获取步骤状态样式类
const getStepStatusClass = (status: string) => {
  return `status-${status}`
}

// 清理 SQL 内容，去除 markdown 代码块标记；如果是 JSON 包裹则提取 sql 字段
const cleanSqlContent = (content: string) => {
  if (!content) return ''
  let cleaned = content.trim()
  // 去掉 markdown 代码块标记
  cleaned = cleaned.replace(/^```(?:sql|json)?\s*/i, '').replace(/\s*```$/, '').trim()
  // 如果是 JSON 格式（{"sql": "..."}），提取 sql 字段
  if (cleaned.startsWith('{')) {
    try {
      const parsed = JSON.parse(cleaned)
      if (parsed.sql) return parsed.sql
    } catch {
      // 流式中 JSON 不完整，尝试正则提取
      const m = cleaned.match(/"sql"\s*:\s*"([\s\S]+?)(?:"|$)/)
      if (m && m[1].length > 5) return m[1].replace(/\\n/g, '\n')
      return '正在生成 SQL...'
    }
  }
  return cleaned
}

/**
 * 简单的 markdown 渲染：处理 **加粗**、*斜体*、换行
 * 不引入额外依赖，只处理思考过程中常见的格式
 */
const renderMarkdown = (content: string): string => {
  if (!content) return ''
  return content
    // 先转义 HTML 特殊字符，防止 XSS
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // **加粗**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // *斜体*
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 换行
    .replace(/\n/g, '<br>')
}
const extractDisplayText = (content: string, title?: string): string => {
  if (!content) return ''
  const trimmed = content.trim()

  // 去掉 markdown 代码块标记
  const stripMarkdown = (s: string) =>
    s.replace(/^```(?:json|sql)?\s*/i, '').replace(/\s*```$/, '').trim()

  const jsonStr = stripMarkdown(trimmed)
  const looksLikeJson = jsonStr.startsWith('{') || jsonStr.startsWith('[') || trimmed.startsWith('```')

  // ── SQL生成：提取 sql 字段（但 type=sql 的 step 走 cleanSqlContent，这里处理 JSON 包裹的情况）
  if (title === 'SQL生成' && looksLikeJson) {
    try {
      const parsed = JSON.parse(jsonStr)
      if (parsed.sql) return parsed.sql
      if (parsed.explanation) return parsed.explanation
    } catch {
      // 流式中，尝试正则提取 sql 字段
      const m = jsonStr.match(/"sql"\s*:\s*"([\s\S]+?)(?:"|$)/)
      if (m && m[1].length > 5) return m[1].replace(/\\n/g, '\n')
    }
    return '正在生成 SQL...'
  }

  // ── 意图澄清：内容可能是"前缀文字 + ```json{...}"，提取 clarificationText
  if (title === '意图澄清') {
    // 先尝试从混合内容里找 JSON 块
    const jsonBlockMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)(?:```|$)/i)
    const jsonCandidate = jsonBlockMatch ? jsonBlockMatch[1].trim() : (looksLikeJson ? jsonStr : '')
    if (jsonCandidate) {
      try {
        const parsed = JSON.parse(jsonCandidate)
        if (parsed.clarificationText) return parsed.clarificationText
        if (parsed.analysis) return parsed.analysis
        if (parsed.needsClarification !== undefined) {
          return parsed.clarificationText || parsed.analysis || '分析完成'
        }
      } catch {
        // 流式中，尝试正则提取 clarificationText
        const m = jsonCandidate.match(/"clarificationText"\s*:\s*"([\s\S]+?)(?:"|$)/)
        if (m && m[1].length > 10) return m[1].replace(/\\n/g, '\n')
        // 如果已经开始输出 JSON 块，显示等待
        if (jsonCandidate.length > 5) return '正在分析...'
      }
    }
    // 纯文字前缀（还没到 JSON 部分），直接展示
    const textBeforeJson = trimmed.replace(/```[\s\S]*$/, '').trim()
    return textBeforeJson || '正在分析...'
  }

  // ── 智能选表：提取 overallReasoning
  if (title === '智能选表' && looksLikeJson) {
    try {
      const parsed = JSON.parse(jsonStr)
      if (parsed.overallReasoning) return parsed.overallReasoning
    } catch {
      const m = jsonStr.match(/"overallReasoning"\s*:\s*"([\s\S]+?)(?:"|$)/)
      if (m && m[1].length > 10) return m[1].replace(/\\n/g, '\n')
    }
    return '正在分析...'
  }

  // ── 其他 stage（意图识别、模型思考等）：如果是 JSON 就提取有意义字段，否则直接展示
  if (looksLikeJson) {
    try {
      const parsed = JSON.parse(jsonStr)
      return parsed.overallReasoning || parsed.reasoning || parsed.analysis ||
             parsed.summary || parsed.clarificationText || parsed.text || '正在分析...'
    } catch {
      const m = jsonStr.match(/"(?:overallReasoning|reasoning|analysis|clarificationText)"\s*:\s*"([\s\S]+?)(?:"|$)/)
      if (m && m[1].length > 10) return m[1].replace(/\\n/g, '\n')
      return '正在分析...'
    }
  }

  return content
}
</script>

<style scoped>
.thinking-process {
  width: 100%;
  background: #ffffff;  /* 改为白色背景 */
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

.thinking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.thinking-header:hover {
  background: #f8f9fa;  /* hover 时使用浅灰色 */
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.thinking-icon {
  font-size: 16px;
}

.thinking-title {
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.thinking-time {
  font-size: 11px;
  color: #6c757d;
  background: #e9ecef;
  padding: 2px 8px;
  border-radius: 10px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.collapse-icon {
  color: #6c757d;
  font-size: 12px;
  transition: transform 0.3s;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.thinking-content {
  padding: 0 14px 12px 14px;
  border-top: 1px solid #e9ecef;
}

.thinking-step {
  margin-top: 12px;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.step-header.clickable {
  cursor: pointer;
  user-select: none;
  border-radius: 4px;
  padding: 2px 4px;
  margin-left: -4px;
  transition: background 0.15s;
}

.step-header.clickable:hover {
  background: #f0f0f0;
}

.step-collapse-icon {
  margin-left: auto;
  color: #adb5bd;
  font-size: 14px;
  transition: transform 0.2s;
  line-height: 1;
}

.step-collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.step-icon {
  font-size: 14px;
}

.step-icon.status-completed {
  color: #28a745;
}

.step-icon.status-running {
  color: #007bff;
  animation: pulse 1.5s ease-in-out infinite;
}

.step-icon.status-error {
  color: #dc3545;
}

.step-icon.status-pending {
  color: #6c757d;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.step-title {
  font-size: 13px;
  font-weight: 500;
  color: #212529;
}

.step-content {
  margin-left: 22px;
  font-size: 12px;
  color: #495057;
}

.text-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.markdown-content {
  line-height: 1.6;
  white-space: normal;
}

.markdown-content strong {
  font-weight: 600;
  color: #212529;
}

.markdown-content em {
  font-style: italic;
}

.sql-block {
  background: #282c34;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  margin-top: 6px;
}

.sql-block pre {
  margin: 0;
}

.sql-block code {
  color: #abb2bf;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* 整体折叠动画 */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  max-height: 800px;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

/* 步骤内容折叠动画 */
.step-collapse-enter-active,
.step-collapse-leave-active {
  transition: all 0.2s ease;
  max-height: 600px;
  overflow: hidden;
}

.step-collapse-enter-from,
.step-collapse-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
