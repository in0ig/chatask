<template>
  <div class="collapsible-stage" :class="{ 'stage-completed': stage.status === 'completed', 'stage-error': stage.status === 'error' }">
    <!-- 阶段标题栏 -->
    <div class="stage-header" @click="toggleCollapse">
      <div class="stage-title">
        <!-- 状态图标 -->
        <span class="stage-icon">
          <span v-if="stage.status === 'completed'" class="icon-completed">✅</span>
          <span v-else-if="stage.status === 'error'" class="icon-error">❌</span>
          <span v-else class="icon-progress">⏳</span>
        </span>
        
        <!-- 阶段名称 -->
        <span class="stage-name">{{ stage.name }}</span>
      </div>
      
      <!-- 折叠/展开图标 -->
      <span class="collapse-icon" :class="{ 'collapsed': isCollapsed }">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </div>
    
    <!-- 阶段内容 -->
    <transition name="collapse">
      <div v-show="!isCollapsed" class="stage-content" ref="contentRef">
        <!-- SQL 代码高亮显示 -->
        <div v-if="isSQLContent" class="sql-code-container">
          <div ref="sqlEditorRef" class="sql-editor"></div>
        </div>
        
        <!-- 普通文本内容 -->
        <div v-else-if="!hasChartData || !chartData" class="content-text" :class="{ 'content-completed': stage.status === 'completed' }">
          <!-- 🔥 使用 v-html 渲染 Markdown 格式的内容 -->
          <div v-html="renderedContent"></div>
          
          <!-- 流式输出指示器 -->
          <div v-if="stage.status === 'in_progress' && stageContent" class="streaming-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
        
        <!-- 🔥 图表显示（如果 metadata 中有 chart_config） -->
        <div v-if="hasChartData && chartData" class="chart-display-container">
          <!-- 视图切换按钮 -->
          <div class="view-toggle">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="chart">{{ $t('view.chart') }}</el-radio-button>
              <el-radio-button value="table">{{ $t('view.table') }}</el-radio-button>
              <el-radio-button value="both">{{ $t('view.both') }}</el-radio-button>
            </el-radio-group>
          </div>
          
          <!-- 图表视图 -->
          <div v-show="viewMode === 'chart' || viewMode === 'both'" class="chart-view">
            <SmartChart
              :data="chartData"
              :type="chartType || 'auto'"
              :theme="'light'"
              :responsive="true"
              :exportable="true"
              :options="{
                showToolbar: true,
                showLegend: true,
                enableDataZoom: true,
                enableContextMenu: true,
                enableDataPointSelection: true
              }"
            />
          </div>
          
          <!-- 表格视图 -->
          <div v-show="viewMode === 'table' || viewMode === 'both'" class="table-view">
            <DataTable 
              v-if="tableHeaders.length > 0 && tableRows.length > 0"
              :headers="tableHeaders" 
              :rows="tableRows"
            />
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, nextTick } from 'vue'
import type { MessageStage } from '@/types/chat'
import { EditorView, basicSetup } from 'codemirror'
import { sql } from '@codemirror/lang-sql'
import { EditorState } from '@codemirror/state'
import SmartChart from '@/components/Chart/SmartChart.vue'
import DataTable from '@/components/DataTable.vue'
import type { ChartData } from '@/types/chart'

// Props
const props = defineProps<{
  stage: MessageStage
}>()

// 组件创建（调试日志已移除）

// 本地折叠状态
// 🔥 流式输出时默认展开，完成后也保持展开状态（用户可以手动折叠）
const isCollapsed = ref(false)

// 初始折叠状态（调试日志已移除）

// SQL 编辑器引用
const sqlEditorRef = ref<HTMLElement | null>(null)
let editorView: EditorView | null = null

// 内容容器引用（用于自动滚动）
const contentRef = ref<HTMLElement | null>(null)

// 🔥 使用 computed 确保内容的响应式
const stageContent = computed(() => {
  return props.stage.content
})

// 🔥 格式化后的内容（解析 JSON、渲染 Markdown）
const formattedContent = computed(() => {
  const content = stageContent.value
  if (!content) return ''
  
  // 尝试解析 JSON
  try {
    const jsonData = JSON.parse(content)
    
    // 根据 stage ID 进行不同的格式化
    if (props.stage.id === 'intent_recognition') {
      // 意图识别：提取关键信息
      const intentMap = {
        'query': '智能问数',
        'report': '生成报告',
        'smart_query': '智能问数',
        'report_generation': '生成报告'
      }
      const intent = intentMap[jsonData.intent] || jsonData.intent
      const confidence = (jsonData.confidence * 100).toFixed(0)
      const reason = jsonData.reason || jsonData.reasoning || '无'
      
      return `**意图类型**：${intent}\n**置信度**：${confidence}%\n**原因**：${reason}`
    } else if (props.stage.id === 'sql_generation') {
      // SQL 生成：提取 SQL 和说明
      const sql = jsonData.sql || jsonData.query || ''
      const explanation = jsonData.explanation || jsonData.reasoning || ''
      
      let result = ''
      if (sql) {
        result += `**生成的 SQL**：\n\`\`\`sql\n${sql}\n\`\`\`\n`
      }
      if (explanation) {
        result += `\n**说明**：${explanation}`
      }
      return result || content
    } else {
      // 其他：美化 JSON 显示
      return `\`\`\`json\n${JSON.stringify(jsonData, null, 2)}\n\`\`\``
    }
  } catch (e) {
    // 不是 JSON，直接返回原内容（Markdown 格式）
    return content
  }
})

// 🔥 新增：渲染后的内容（将 Markdown 转换为 HTML）
const renderedContent = computed(() => {
  const markdown = formattedContent.value
  if (!markdown) return ''
  
  // 调用 renderMarkdown 方法将 Markdown 转换为 HTML
  return renderMarkdown(markdown)
})

// 🔥 新增：检测是否有图表数据
const hasChartData = computed(() => {
  const config = props.stage.metadata?.chart_config
  if (!config) return false
  
  // 如果推荐的图表类型是 "table"，不显示图表组件
  if (config.recommendedChart === 'table') return false
  
  // 如果有 chartConfig 且 series 不为空，才显示图表
  return !!(config.chartConfig && config.chartConfig.series && config.chartConfig.series.length > 0)
})

// 🔥 新增：获取图表类型
const chartType = computed(() => {
  return props.stage.metadata?.chart_type || 
         props.stage.metadata?.chart_config?.recommendedChart || 
         '未知'
})

// 🔥 新增：获取图表配置
const chartConfig = computed(() => {
  // 🔥 修复：后端使用 chart_config（下划线），不是 chartConfig（驼峰）
  return props.stage.metadata?.chart_config || {}
})

// 🔥 新增：视图模式（图表/表格/对比）
const viewMode = ref<'chart' | 'table' | 'both'>('chart')

// 🔥 新增：转换图表配置为 ChartData 格式
const chartData = computed((): ChartData | undefined => {
  const config = chartConfig.value
  
  if (!config || Object.keys(config).length === 0) {
    console.log('⚠️ [chartData] 没有图表配置')
    return undefined
  }
  
  // 🔥 优先使用 metadata.chartData（包含完整原始数据 + AI series）
  const fullChartData = props.stage.metadata?.chartData
  if (fullChartData && fullChartData.columns && fullChartData.rows && fullChartData.rows.length > 0) {
    console.log('✅ [chartData] 使用 metadata.chartData（完整原始数据）:', {
      columns: fullChartData.columns?.length,
      rows: fullChartData.rows?.length,
      hasSeries: !!fullChartData.series
    })
    const result: ChartData = {
      title: config.chartConfig?.title || fullChartData.title || '',
      columns: fullChartData.columns,
      rows: fullChartData.rows,
      metadata: fullChartData.metadata || {}
    }
    // 保留 AI 生成的 series 和推荐图表类型，供 SmartChart 使用
    // 🔥 优先使用 fullChartData 中已有的 series，否则从 chart_config 补充
    if (fullChartData.series) {
      (result as any).series = fullChartData.series
    } else if (config.chartConfig?.series && config.chartConfig.series.length > 0) {
      (result as any).series = config.chartConfig.series
      console.log('✅ [chartData] 从 chart_config.series 补充 AI series')
    }
    if (fullChartData.aiRecommendedType) {
      (result as any).aiRecommendedType = fullChartData.aiRecommendedType
    } else if (config.recommendedChart) {
      (result as any).aiRecommendedType = config.recommendedChart
    }
    return result
  }
  
  console.log('📊 [chartData] metadata.chartData 不可用，从 chart_config.series 重建')
  
  // fallback：从 chart_config.chartConfig.series 重建
  const backendChartConfig = config.chartConfig
  
  if (!backendChartConfig) {
    console.log('⚠️ [chartData] config.chartConfig 不存在')
    return undefined
  }
  
  // 如果有 series 数据，转换为 ChartData 格式
  if (backendChartConfig.series && backendChartConfig.series.length > 0) {
    const series = backendChartConfig.series[0]
    
    // 从 series.data 提取 columns 和 rows
    if (series.data && Array.isArray(series.data)) {
      const columns = ['name', 'value']
      const rows = series.data.map((item: any) => [item.name, item.value])
      
      const result: ChartData = {
        title: backendChartConfig.title || '数据图表',
        columns: columns,
        rows: rows,
        metadata: {
          columnTypes: ['string', 'number']
        }
      }
      // 保留完整的 AI series 供 SmartChart 使用
      ;(result as any).series = backendChartConfig.series
      if (config.recommendedChart) {
        (result as any).aiRecommendedType = config.recommendedChart
      }
      return result
    }
  }
  
  console.log('⚠️ [chartData] 无法转换图表数据')
  return undefined
})

// 🔥 新增：表格数据
const tableHeaders = computed(() => {
  const data = chartData.value
  if (!data || !data.columns) {
    return []
  }
  return data.columns
})

const tableRows = computed(() => {
  const data = chartData.value
  if (!data || !data.rows) {
    return []
  }
  return data.rows
})

// 判断内容是否为 SQL
const isSQLContent = computed(() => {
  const content = stageContent.value?.trim() || ''
  const contentLower = content.toLowerCase()
  
  // 🔥 更严格的 SQL 判断：必须以 SQL 关键字开头，或者被 ```sql 代码块包裹
  const startsWithSqlKeyword = 
    contentLower.startsWith('select ') || 
    contentLower.startsWith('insert ') || 
    contentLower.startsWith('update ') || 
    contentLower.startsWith('delete ') ||
    contentLower.startsWith('create ') ||
    contentLower.startsWith('alter ') ||
    contentLower.startsWith('drop ')
  
  // 检查是否是 SQL 代码块（```sql ... ```）
  const isSqlCodeBlock = content.startsWith('```sql') || content.startsWith('```SQL')
  
  return startsWithSqlKeyword || isSqlCodeBlock
})

// 初始化 SQL 编辑器
const initSQLEditor = async () => {
  if (!sqlEditorRef.value || !isSQLContent.value) {
    return
  }
  
  // 清理旧的编辑器实例
  if (editorView) {
    editorView.destroy()
    editorView = null
  }
  
  await nextTick()
  
  if (!sqlEditorRef.value) {
    return
  }
  
  // 🔥 处理 SQL 代码块格式：移除 ```sql 和 ``` 标记
  let sqlCode = stageContent.value || ''
  if (sqlCode.startsWith('```sql') || sqlCode.startsWith('```SQL')) {
    // 移除开头的 ```sql 和结尾的 ```
    sqlCode = sqlCode.replace(/^```sql\n?/i, '').replace(/\n?```$/, '')
  }
  
  const state = EditorState.create({
    doc: sqlCode,
    extensions: [
      basicSetup,
      sql(),
      EditorView.editable.of(false), // 只读模式
      EditorView.theme({
        '&': {
          fontSize: '13px',
          border: '1px solid #e0e0e0',
          borderRadius: '4px',
          backgroundColor: '#fafafa'
        },
        '.cm-content': {
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace',
          padding: '8px'
        },
        '.cm-gutters': {
          backgroundColor: '#f5f5f5',
          border: 'none'
        }
      })
    ]
  })
  
  editorView = new EditorView({
    state,
    parent: sqlEditorRef.value
  })
}

// 监听 stage.collapsed 的变化
watch(() => props.stage.collapsed, (newValue) => {
  isCollapsed.value = newValue
})

// 🔥 不再监听 status 变化自动折叠，让用户自己控制折叠状态
// 流式输出时默认展开，完成后也保持展开，用户可以手动点击折叠

// 监听内容变化，重新初始化编辑器
watch(stageContent, (newContent, oldContent) => {
  if (isSQLContent.value) {
    initSQLEditor()
  }
  
  // 自动滚动到底部（仅在流式输出时）
  if (props.stage.status === 'in_progress' && !isCollapsed.value) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})

// 自动滚动到底部
const scrollToBottom = () => {
  // 滚动到组件所在的容器底部
  const stageElement = contentRef.value?.closest('.collapsible-stage')
  if (stageElement) {
    stageElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
}

// 监听折叠状态，展开时初始化编辑器
watch(isCollapsed, async (newValue) => {
  if (!newValue && isSQLContent.value) {
    await nextTick()
    initSQLEditor()
  }
})

// 🔥 新增：监听 isSQLContent 变化，当变为 true 时初始化编辑器
watch(isSQLContent, async (newValue, oldValue) => {
  if (newValue && !isCollapsed.value) {
    await nextTick()
    await nextTick() // 🔥 双重 nextTick 确保 DOM 完全更新
    initSQLEditor()
  }
})

// 组件挂载时初始化
onMounted(() => {
  if (!isCollapsed.value && isSQLContent.value) {
    initSQLEditor()
  }
})

// 切换折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 格式化元数据值
const formatMetadataValue = (value: any): string => {
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

// HTML 转义辅助函数
const escapeHtml = (text: string): string => {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
}

// 渲染 Markdown 格式的内容
const renderMarkdown = (content: string): string => {
  if (!content) return ''
  
  let html = content
  
  // 🔥 修复1：代码块渲染（支持多行代码）- 必须最先处理，避免内部内容被其他规则处理
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || 'text'}">${escapeHtml(code.trim())}</code></pre>`
  })
  
  // 🔥 修复2：表格渲染（改进解析逻辑）
  html = html.replace(/(\|[^\n]+\|\n)+/g, (tableText) => {
    const lines = tableText.trim().split('\n').filter(line => line.trim())
    if (lines.length < 2) return tableText
    
    // 检查是否有分隔行
    const separatorIndex = lines.findIndex(line => /^\|[\s\-:|]+\|$/.test(line.trim()))
    if (separatorIndex === -1 || separatorIndex === 0) return tableText
    
    // 解析表头
    const headerLine = lines[separatorIndex - 1]
    const headers = headerLine.split('|').filter(cell => cell.trim()).map(cell => cell.trim())
    
    // 解析数据行
    const dataLines = lines.slice(separatorIndex + 1)
    const rows = dataLines.map(line => 
      line.split('|').filter(cell => cell.trim()).map(cell => cell.trim())
    )
    
    // 生成 HTML 表格
    let tableHtml = '<table class="markdown-table"><thead><tr>'
    headers.forEach(header => {
      tableHtml += `<th>${escapeHtml(header)}</th>`
    })
    tableHtml += '</tr></thead><tbody>'
    
    rows.forEach(row => {
      if (row.length > 0) {
        tableHtml += '<tr>'
        row.forEach(cell => {
          tableHtml += `<td>${escapeHtml(cell)}</td>`
        })
        tableHtml += '</tr>'
      }
    })
    
    tableHtml += '</tbody></table>'
    return tableHtml
  })
  
  // 🔥 修复3：标题（支持多级标题）- 在行内格式之前处理
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  
  // 🔥 修复4：粗体（避免与斜体冲突）- 必须在斜体之前处理
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  
  // 🔥 修复5：斜体（单星号）
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  
  // 🔥 修复6：行内代码（避免与其他标记冲突）
  html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>')
  
  // 🔥 修复7：链接
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  
  // 🔥 修复8：无序列表（支持 - 和 * 开头）
  html = html.replace(/^[*-] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  
  // 🔥 修复9：有序列表
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
  
  // 🔥 修复10：引用
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  
  // 🔥 修复11：分隔线
  html = html.replace(/^---+$/gm, '<hr>')
  html = html.replace(/^\*\*\*+$/gm, '<hr>')
  
  // 🔥 修复12：换行（保留段落结构）
  html = html.replace(/\n\n/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')
  
  // 🔥 修复13：包裹段落标签
  if (!html.startsWith('<')) {
    html = '<p>' + html + '</p>'
  }
  
  return html
}
</script>

<style scoped>
.collapsible-stage {
  margin: 8px 0;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #ffffff;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stage-completed {
  border-color: #d9d9d9;
}

.stage-error {
  border-color: #ffccc7;
  background-color: #fff2f0;
}

.stage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
  background-color: #f5f5f5; /* 🔥 修复：阶段标题栏使用灰色背景 */
}

.stage-header:hover {
  background-color: #e8e8e8;
}

.stage-completed .stage-header {
  background-color: #fafafa;
}

.stage-completed .stage-header:hover {
  background-color: #f0f0f0;
}

.stage-error .stage-header:hover {
  background-color: #fff1f0;
}

.stage-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.stage-icon {
  display: flex;
  align-items: center;
  font-size: 16px;
}

.icon-completed {
  color: #52c41a;
}

.icon-error {
  color: #ff4d4f;
}

.icon-progress {
  color: #1890ff;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.stage-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.stage-completed .stage-name {
  color: #666; /* 已完成步骤使用深灰色文字 */
}

.collapse-icon {
  display: flex;
  align-items: center;
  color: #999;
  transition: transform 0.3s ease;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.stage-content {
  padding: 0 16px 12px 16px;
  border-top: 1px solid #f0f0f0;
  background-color: #ffffff; /* 🔥 修复：展开的内容区使用白色背景 */
  
  /* 性能优化: 提示浏览器这个元素会变化 */
  will-change: transform, opacity;
  
  /* 性能优化: 使用 GPU 加速 */
  transform: translateZ(0);
  
  /* 性能优化: 避免重排 */
  contain: layout style paint;
}

.content-text {
  padding: 12px 0;
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.content-completed {
  color: #666; /* 已完成步骤的内容使用深灰色文字 */
}

/* 流式输出指示器 */
.streaming-indicator {
  display: inline-flex;
  gap: 4px;
  margin-left: 4px;
  align-items: center;
  vertical-align: middle;
  
  /* 性能优化: 动画元素使用 GPU 加速 */
  will-change: transform;
  transform: translateZ(0);
}

.streaming-indicator .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #1890ff;
  animation: bounce 1.4s infinite ease-in-out;
}

.streaming-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.streaming-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.3;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.sql-code-container {
  padding: 12px 0;
}

.sql-editor {
  border-radius: 4px;
  overflow: hidden;
}

/* 折叠动画 */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Markdown 样式 */
.content-text :deep(.inline-code) {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.9em;
  color: #d73a49;
  border: 1px solid #e1e4e8;
}

.content-text :deep(pre) {
  background-color: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.content-text :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #24292e;
  font-size: 12px;
  line-height: 1.5;
  border: none;
}

.content-text :deep(strong) {
  font-weight: 600;
  color: #24292e;
}

.content-text :deep(em) {
  font-style: italic;
  color: #586069;
}

.content-text :deep(h1),
.content-text :deep(h2),
.content-text :deep(h3),
.content-text :deep(h4) {
  margin: 16px 0 8px 0;
  font-weight: 600;
  line-height: 1.25;
  color: #24292e;
}

.content-text :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid #e1e4e8;
  padding-bottom: 8px;
}

.content-text :deep(h2) {
  font-size: 1.3em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 6px;
}

.content-text :deep(h3) {
  font-size: 1.1em;
}

.content-text :deep(h4) {
  font-size: 1em;
}

.content-text :deep(a) {
  color: #0366d6;
  text-decoration: none;
}

.content-text :deep(a:hover) {
  text-decoration: underline;
}

.content-text :deep(ul),
.content-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.content-text :deep(li) {
  margin: 4px 0;
  line-height: 1.6;
}

.content-text :deep(blockquote) {
  border-left: 4px solid #dfe2e5;
  padding-left: 16px;
  margin: 8px 0;
  color: #6a737d;
}

.content-text :deep(hr) {
  border: none;
  border-top: 1px solid #e1e4e8;
  margin: 16px 0;
}

.content-text :deep(p) {
  margin: 8px 0;
  line-height: 1.6;
}

.content-text :deep(.markdown-table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 13px;
  border: 1px solid #e1e4e8;
}

.content-text :deep(.markdown-table th),
.content-text :deep(.markdown-table td) {
  border: 1px solid #e1e4e8;
  padding: 8px 12px;
  text-align: left;
}

.content-text :deep(.markdown-table th) {
  background-color: #f6f8fa;
  font-weight: 600;
  color: #24292e;
}

.content-text :deep(.markdown-table tr:nth-child(even)) {
  background-color: #f9f9f9;
}

.content-text :deep(.markdown-table tr:hover) {
  background-color: #f5f5f5;
}

/* 图表显示容器样式 */
.chart-display-container {
  margin-top: 16px;
  padding: 16px;
  background-color: #fafafa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.view-toggle {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.chart-view {
  background-color: #ffffff;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.table-view {
  background-color: #ffffff;
  padding: 16px;
  border-radius: 8px;
}

/* 对比视图时添加明显的分隔 */
.chart-display-container .chart-view + .table-view {
  margin-top: 16px;
  border-top: 2px solid #e0e0e0;
  padding-top: 24px;
}
</style>
