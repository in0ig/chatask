<template>
  <div class="home-container">
    <!-- 主内容区域 -->
    <div class="home-main-content">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-inner">
          <div class="toolbar-spacer"></div>
          <!-- 右侧按钮区域 -->
          <div class="toolbar-right">
            <!-- 语言切换按钮 -->
            <el-button
              text
              class="lang-button"
              :title="$t('header.language')"
              @click="localeStore.toggleLocale()"
            >
              <span class="lang-icon">🌐</span>
              <span class="lang-label">{{ localeStore.localeLabel }}</span>
            </el-button>
            <el-button 
              class="config-button" 
              @click="toggleConfigDrawer"
            >
              <el-icon style="margin-right: 4px;"><Setting /></el-icon>
              {{ $t('header.settings') }}
            </el-button>
          </div>
        </div>
      </div>
    
    <!-- 欢迎语 -->
    <div class="welcome-section" v-if="!hasActiveSession">
      <div class="welcome-header">
        <h1>{{ $t('home.welcome') }}</h1>
        <p>{{ $t('home.subtitle') }}</p>
      </div>
    </div>

    <!-- 消息流区域 -->
    <div class="messages-container" v-else ref="messagesContainerRef">
      <div class="messages-list">
        <!-- 数据源加载中状态 -->
        <div v-if="isLoading && !error" class="message ai-message">
          <div class="avatar ai-avatar">🤖</div>
          <div class="message-content ai-content">
            <div class="loading-indicator">
              <div class="loading-dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </div>
              <p>{{ $t('home.loadingDataSource') }}</p>
            </div>
          </div>
        </div>
        
        <!-- 数据源加载错误状态 -->
        <div v-else-if="error" class="message ai-message">
          <div class="avatar ai-avatar">🤖</div>
          <div class="message-content ai-content">
            <p class="error-message">{{ error }}</p>
          </div>
        </div>
        
        <!-- 正常消息列表 -->
        <div 
          v-for="message in messages" 
          :key="message.id"
          v-show="!isLoading || error"
        >
          <!-- 用户消息 -->
          <div v-if="message.role === 'user'" class="message user-message">
            <div class="avatar user-avatar">👤</div>
            <div class="message-content user-content">
              <p>{{ message.content }}</p>
            </div>
          </div>
          
          <!-- AI 消息 -->
          <AIMessage
            v-else
            :thinking-steps="message.stages?.length ? convertStagesToThinkingSteps(message.stages) : parseOldContentToThinkingSteps(message.content || '')"
            :thinking-time="message.thinkingTime"
            :thinking-collapsed="message.stages?.length ? (message.thinkingCollapsed === true) : false"
            :text-content="getResultDescription(message.stages || [])"
            :chart-data="getMessageChartData(message)"
            :chart-type="getMessageChartType(message)"
            :is-generating-chart="isChartGenerating(message.stages || [])"
            :timestamp="message.timestamp"
          />
        </div>
        
        <!-- 加载状态 -->
        <div v-if="uiStore.isLoading" class="message ai-message">
          <div class="avatar ai-avatar">🤖</div>
          <div class="message-content ai-content">
            <div class="loading-indicator">
              <div class="loading-dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </div>
              <p>{{ uiStore.loadingMessage }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入控制区 -->
    <div class="input-container">
        <!-- 隐藏的文件上传输入 -->
        <input 
          type="file" 
          id="file-upload" 
          style="display: none;" 
          @change="handleFileUpload" 
          accept=".csv,.xlsx,.xls,.txt,.json" 
        />
        
        <!-- 第一行：数据源、数据表、模式选择器在一行 -->
        <div class="input-row input-controls-row">
          <div class="data-source-selector">
            <label class="label">{{ $t('home.dataSource') }}</label>
            <el-select 
              v-model="currentDataSource" 
              :placeholder="$t('home.selectDataSource')" 
              class="source-select"
              size="small"
              @change="handleDataSourceChange"
            >
              <el-option 
                v-for="item in dataSources" 
                :key="item.id" 
                :label="item.name" 
                :value="item.id" 
              />
            </el-select>
          </div>
          
          <div class="data-table-selector">
            <label class="label">{{ $t('home.dataTable') }}</label>
            <el-select 
              v-model="currentDataTables" 
              :placeholder="$t('home.selectDataTable')" 
              class="table-select"
              size="small"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :disabled="!currentDataSource"
              @change="handleDataTableChange"
            >
              <el-option 
                v-for="item in availableDataTables" 
                :key="item.id" 
                :label="item.name" 
                :value="item.id" 
              />
            </el-select>
          </div>
          
          <el-button 
            type="primary" 
            size="small" 
            class="preview-btn"
            :disabled="!currentDataTables || currentDataTables.length === 0"
            @click="openDataTablePreview"
          >
            {{ $t('home.preview') }}
          </el-button>
          
          <div class="mode-toggle">
            <label class="label" style="margin-right: 8px;">{{ $t('chat.queryMode') }}</label>
            <el-switch
              v-model="chatMode"
              active-text=""
              inactive-text=""
              :active-color="'#1890ff'"
              :inactive-color="'#ccc'"
              size="small"
            />
            <label class="label" style="margin-left: 8px;">{{ $t('chat.reportMode') }}</label>
          </div>
        </div>
        
        <!-- 第二行：输入框和发送按钮 -->
        <div class="input-row input-message-row">
          <el-input
            v-model="inputText"
            :placeholder="$t('home.inputPlaceholder')"
            class="message-input"
            @keydown.enter.exact.prevent="sendMessage"
          />
          
          <!-- 发送按钮 -->
          <button 
            type="button" 
            class="custom-btn send-btn" 
            :disabled="!canSend"
            @click="sendMessage"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </div>
    </div>
    
    <!-- 数据源选择弹窗 -->
    <DataSourceSelector
      v-model="dataSourceSelectorVisible"
      :data-sources="dataSources"
      :is-loading="isLoading"
      :error="error"
      @confirm="handleDataSourceConfirm"
      @preview="handleDataSourcePreview"
      @retry="handleDataSourceRetry"
    />
    
    <!-- 数据预览模态框 -->
    <DataPreviewModal
      v-model="dataPreviewModalVisible"
      :preview-data="previewData"
      :is-multi-table="isMultiTable"
      :selected-tables="selectedTablesForPreview"
      @table-change="handlePreviewTableChange"
    />
    </div> <!-- 关闭 home-main-content -->
  </div> <!-- 关闭 home-container -->
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useChatStore } from '@/store/modules/chat'
import { useUIStore } from '@/store/modules/ui'
import { useLocaleStore } from '@/store/modules/locale'
import { useRoute } from 'vue-router'
import { Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import ChartRenderer from '@/components/ChartRenderer.vue'
import DataTable from '@/components/DataTable.vue'
import SmartChart from '@/components/Chart/SmartChart.vue'
import DataSourceSelector from '@/components/DataSource/DataSourceSelector.vue'
import DataPreviewModal from '@/components/DataSource/DataPreviewModal.vue'
import ExecutionSteps from '@/components/Chat/ExecutionSteps.vue'
import AIMessage from '@/components/Chat/AIMessage.vue'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { websocketService, createWebSocketService } from '@/services/websocketService'
import { type WSMessage } from '@/types/chat'
import { type ChartData } from '@/types/chart'
import { aiChartSelector } from '@/services/aiChartSelector'
import { dataTableApi } from '@/services/dataTableApi'
import axios from 'axios'

const chatStore = useChatStore()
const uiStore = useUIStore()
const localeStore = useLocaleStore()
const route = useRoute()
const { t: $t } = useI18n()

// 当前流式消息ID
let currentStreamingMessageId: string | null = null

// 当前 WebSocket 服务实例
let currentWSService: any = null

// 🆕 消息容器引用（用于自动滚动）
const messagesContainerRef = ref<HTMLElement | null>(null)

// 配置抽屉控制
const toggleConfigDrawer = () => {
  uiStore.toggleConfigDrawer()
}

// 🆕 自动滚动到底部
const scrollToBottom = () => {
  if (messagesContainerRef.value) {
    // 使用 nextTick 确保 DOM 已更新
    nextTick(() => {
      if (messagesContainerRef.value) {
        messagesContainerRef.value.scrollTo({
          top: messagesContainerRef.value.scrollHeight,
          behavior: 'smooth'
        })
      }
    })
  }
}

// 状态
const inputText = ref('')
const currentDataSource = ref<string | null>(null)
const currentDataTables = ref<string[]>([])

// 从 store 获取 chatMode
const chatMode = computed({
  get: () => chatStore.chatMode === 'report',
  set: (value) => {
    // Switch 组件会传入 boolean 值
    // true = 生成报告, false = 智能问数
    if (value) {
      chatStore.chatMode = 'report'
    } else {
      chatStore.chatMode = 'query'
    }
  }
})

// 数据源选择弹窗状态
const dataSourceSelectorVisible = ref(false)
const dataPreviewModalVisible = ref(false)
const previewData = ref({
  schema: [],
  data: []
})
const isMultiTable = ref(false)
const selectedTablesForPreview = ref([])

// 获取数据源列表
const dataPrepStore = useDataPrepStore()
const dataSources = computed(() => {
  // 从 dataPrepStore 获取真实的数据源列表，并确保每个数据源都有 type 字段
  return dataPrepStore.dataSources.map(ds => ({
    ...ds,
    // 确保 type 字段存在，如果不存在则设置默认值
    type: ds.type || 'mysql'
  }))
})

// 根据选中的数据源获取可用的数据表
const availableDataTables = computed(() => {
  if (!currentDataSource.value) {
    return []
  }
  // 获取单个数据源下的数据表
  return dataPrepStore.getDataTablesBySourceId(currentDataSource.value) || []
})

// 加载状态和错误处理
const isLoading = computed(() => {
  return dataPrepStore.isLoadingDataSources || uiStore.isLoading
})

const error = computed(() => {
  return dataPrepStore.dataSourceError
})

// 消息列表 - 确保响应式更新
const messages = computed(() => {
  // 直接访问 currentMessages getter，确保每次都重新计算
  const currentMsgs = chatStore.currentMessages
  console.log('📨 messages computed 重新计算，当前消息数:', currentMsgs.length)
  return currentMsgs
})

// 是否有活跃会话（有消息时显示消息流，否则显示欢迎页）
const hasActiveSession = computed(() => {
  const hasMessages = messages.value && messages.value.length > 0
  console.log('🔄 hasActiveSession 重新计算:', hasMessages, '消息数:', messages.value?.length || 0)
  return hasMessages
})

// 输入框占位符
const inputPlaceholder = computed(() => {
  if (!currentDataSource.value) {
    return '请先选择数据源...'
  }
  if (currentDataTables.value.length === 0) {
    return '正在加载数据表...'
  }
  return chatStore.chatMode === 'query' 
    ? '输入您的问题，让 AI 分析数据...' 
    : '输入您想要生成的报告内容...'
})

// 是否可以发送消息
const canSend = computed(() => {
  // 必须有输入内容且至少选择了一个数据表
  const hasInput = inputText.value.trim().length > 0
  const hasDataSource = !!currentDataSource.value
  const hasTable = currentDataTables.value.length > 0
  const result = hasInput && hasDataSource && hasTable
  console.log('🔍 canSend 计算:', { 
    inputText: inputText.value, 
    hasInput, 
    hasDataSource,
    hasTable,
    tableCount: currentDataTables.value.length,
    result 
  })
  return result
})

// 格式化内容（支持 Markdown 渲染）
const formatContent = (content) => {
  if (!content) return ''
  
  // 简单的 Markdown 渲染
  let html = content
  
  // 代码块 ```language\ncode\n```
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || 'text'}">${escapeHtml(code.trim())}</code></pre>`
  })
  
  // 表格渲染（必须在行内代码之前处理）
  html = html.replace(/(\|.+\|[\r\n]+)+/g, (tableText) => {
    const lines = tableText.trim().split('\n')
    if (lines.length < 2) return tableText
    
    // 检查是否有分隔行（第二行应该是 |---|---|）
    const separatorLine = lines[1]
    if (!separatorLine.match(/^\|[\s\-:|]+\|$/)) return tableText
    
    // 解析表头
    const headers = lines[0].split('|').filter(cell => cell.trim()).map(cell => cell.trim())
    
    // 解析数据行
    const rows = lines.slice(2).map(line => 
      line.split('|').filter(cell => cell.trim()).map(cell => cell.trim())
    )
    
    // 生成 HTML 表格
    let tableHtml = '<table class="markdown-table"><thead><tr>'
    headers.forEach(header => {
      tableHtml += `<th>${header}</th>`
    })
    tableHtml += '</tr></thead><tbody>'
    
    rows.forEach(row => {
      tableHtml += '<tr>'
      row.forEach(cell => {
        tableHtml += `<td>${cell}</td>`
      })
      tableHtml += '</tr>'
    })
    
    tableHtml += '</tbody></table>'
    return tableHtml
  })
  
  // 行内代码 `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  
  // 粗体 **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  
  // 斜体 *text*
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  
  // 标题 ### text
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  
  // 链接 [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
  
  // 列表项 - item 或 * item
  html = html.replace(/^[*-] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  
  // 引用 > text
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  
  // 分隔线 ---
  html = html.replace(/^---$/gm, '<hr>')
  
  // 换行
  html = html.replace(/\n/g, '<br>')
  
  return html
}

// HTML 转义辅助函数
const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
}

/**
 * 检测文本语言
 * 规则：非空白字符中 ASCII 字母占比 > 0.5 → 'en'，否则 → 'zh'
 */
const detectLanguage = (text: string): string => {
  if (!text) return 'zh'
  const nonWhitespace = [...text].filter(ch => !/\s/.test(ch))
  if (nonWhitespace.length === 0) return 'zh'
  const asciiAlphaCount = nonWhitespace.filter(ch => /[a-zA-Z]/.test(ch)).length
  return asciiAlphaCount / nonWhitespace.length > 0.5 ? 'en' : 'zh'
}

/**
 * 从 stage 的原始 content 中提取适合展示的摘要文本
 * 不同 stage 的 content 格式不同，需要针对性提取
 */
const extractStageDisplayContent = (stage: any): string => {
  const content = stage.content || ''
  const stageName = stage.name || ''
  const stageId = stage.id || ''

  // 意图识别：stage_complete 发送格式化文本，流式阶段是 JSON 片段
  if (stageId === 'intent_recognition' || stageName === '意图识别' || stageName === 'Intent Recognition') {
    const isEn = stageName === 'Intent Recognition'
    // 优先用 metadata 中的结构化信息（stage_complete 后有 metadata）
    if (stage.metadata?.intent_name && stage.metadata?.confidence !== undefined) {
      return isEn
        ? `Intent recognized: ${stage.metadata.intent_name}\nConfidence: ${stage.metadata.confidence}`
        : `意图识别完成：${stage.metadata.intent_name}\n置信度：${stage.metadata.confidence}`
    }
    if (!content) return ''
    const trimmed = content.trim()
    // 流式阶段：如果看起来像 JSON，尝试提取有意义字段
    if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
      const jsonStr = trimmed.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim()
      try {
        const parsed = JSON.parse(jsonStr)
        const intent = parsed.intent || parsed.intentType
        const confidence = parsed.confidence
        if (intent) return isEn
          ? `Intent recognized: ${intent}${confidence ? `\nConfidence: ${confidence}` : ''}`
          : `意图识别完成：${intent}${confidence ? `\n置信度：${confidence}` : ''}`
        if (parsed.reasoning) return parsed.reasoning
      } catch {
        if (jsonStr.length > 5) return isEn ? 'Recognizing intent...' : '正在识别意图...'
      }
    }
    return content
  }

  // 智能选表：content 是流式 JSON，提取 overallReasoning
  if (stageId === 'table_selection' || stageName === '智能选表' || stageName === 'Table Selection') {
    // 优先用 metadata 中的 reason（stage_complete 后有 metadata）
    if (stage.metadata?.reason) {
      return stage.metadata.reason
    }
    if (!content) return ''
    // 尝试从 content 中解析 JSON 提取 overallReasoning
    try {
      const jsonMatch = content.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0])
        if (parsed.overallReasoning) return parsed.overallReasoning
      }
    } catch {
      // JSON 解析失败（流式中不完整），尝试正则提取
    }
    // 正则提取 overallReasoning（流式中 JSON 不完整时）
    const match = content.match(/"overallReasoning"\s*:\s*"([\s\S]+?)(?:"|$)/)
    if (match && match[1].length > 5) return match[1].replace(/\\n/g, '\n')
    // 如果已经开始输出 JSON，显示等待
    const isEnTS = stageName === 'Table Selection'
    if (content.trim().startsWith('{') && content.length > 5) return isEnTS ? 'Analyzing tables...' : '正在分析数据表...'
    return content
  }

  // 意图澄清：stage_complete 发送的是 clarificationText（自然语言）
  // 但流式阶段 content 是累积的 JSON 片段，需要提取 clarificationText
  if (stageId === 'stage_clarification' || stageName === '意图澄清' || stageName === 'Intent Clarification') {
    if (!content) return ''
    const trimmed = content.trim()
    // 如果看起来像 JSON，尝试提取 clarificationText
    if (trimmed.startsWith('{') || trimmed.startsWith('```')) {
      const jsonStr = trimmed.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim()
      try {
        const parsed = JSON.parse(jsonStr)
        if (parsed.clarificationText) return parsed.clarificationText
      } catch {
        // 流式中 JSON 不完整，尝试正则提取
        const m = jsonStr.match(/"clarificationText"\s*:\s*"([\s\S]+?)(?:"|$)/)
        if (m && m[1].length > 5) return m[1].replace(/\\n/g, '\n')
        const isEnCl = stageName === 'Intent Clarification'
        if (jsonStr.length > 5) return isEnCl ? 'Analyzing...' : '正在分析...'
      }
    }
    return content
  }

  // 模型思考：content 是自然语言，直接展示
  if (stageId === 'stage_thinking' || stageName === '模型思考' || stageName === 'Model Thinking') {
    return content
  }

  // SQL生成：stage_complete 发送的是 ```sql\n...\n```，流式阶段是 JSON 片段
  // 提取 sql 字段或去除 markdown 代码块标记
  if (stageName === 'SQL生成' || stageName === 'SQL Generation' || stageId === 'sql_generation') {
    if (!content) return ''
    const trimmed = content.trim()
    // 去掉 markdown 代码块标记（stage_complete 发送的格式）
    const stripped = trimmed.replace(/^```(?:sql|json)?\s*/i, '').replace(/\s*```$/, '').trim()
    // 如果是 JSON 格式（流式阶段），提取 sql 字段
    if (stripped.startsWith('{')) {
      try {
        const parsed = JSON.parse(stripped)
        if (parsed.sql) return parsed.sql
        if (parsed.explanation) return parsed.explanation
      } catch {
        const m = stripped.match(/"sql"\s*:\s*"([\s\S]+?)(?:"|$)/)
        if (m && m[1].length > 5) return m[1].replace(/\\n/g, '\n')
        if (stripped.length > 5) return stageName === 'SQL Generation' ? 'Generating SQL...' : '正在生成 SQL...'
      }
    }
    return stripped || content
  }

  // SQL执行：展示执行结果摘要
  if (stageId === 'stage_execute' || stageName === 'SQL执行' || stageName === 'SQL Execution') {
    if (stage.metadata?.queryResult) {
      const qr = stage.metadata.queryResult
      if (qr.rows && qr.columns) {
        // 🆕 i18n：根据 stage 名称判断语言
        const isEn = stageName === 'SQL Execution'
        return isEn
          ? `Query complete: ${qr.rows.length} row(s), ${qr.columns.length} column(s)`
          : `查询完成：返回 ${qr.rows.length} 行，${qr.columns.length} 列`
      }
    }
    return content
  }

  return content
}

// 将 stages 转换为 thinkingSteps 格式
const convertStagesToThinkingSteps = (stages: any[]) => {
  if (!stages || stages.length === 0) return []
  
  // 过滤掉"数据结果描述"stage，只保留思考过程相关的 stages
  // 同时支持中英文 stage 名称（i18n）
  const thinkingStageNames = [
    '意图识别', 'Intent Recognition',
    '智能选表', 'Table Selection',
    '意图澄清', 'Intent Clarification',
    '模型思考', 'Model Thinking',
    'SQL生成', 'SQL Generation',
    'SQL执行', 'SQL Execution'
  ]
  
  // SQL stage 名称集合（用于判断 type）
  const sqlStageNames = new Set(['SQL生成', 'SQL Generation'])
  
  return stages
    .filter(stage => thinkingStageNames.includes(stage.name))
    .map(stage => ({
      title: stage.name,
      type: sqlStageNames.has(stage.name) ? 'sql' : 'text',
      content: extractStageDisplayContent(stage),
      status: stage.status === 'completed' ? 'completed' : 
              stage.status === 'error' ? 'error' :
              stage.status === 'in_progress' ? 'running' : 'pending'
    }))
}

// 🔥 兜底：将旧格式 content（【标记】段落拼接）解析为 thinkingSteps
// 用于没有 stages 的历史 assistant 消息
const parseOldContentToThinkingSteps = (content: string) => {
  if (!content) return []
  
  // 匹配 【标记名称】 开头的段落
  const markerRegex = /【(意图识别|智能选表|意图澄清|模型思考|SQL生成|SQL执行)】\n?([\s\S]*?)(?=【|$)/g
  const steps: any[] = []
  let match
  
  while ((match = markerRegex.exec(content)) !== null) {
    const name = match[1]
    const text = match[2].trim()
    if (!text) continue
    steps.push({
      title: name,
      type: name === 'SQL生成' ? 'sql' : 'text',
      content: text,
      status: 'completed'
    })
  }
  
  return steps
}

// 从 stages 中提取数据结果描述
const getResultDescription = (stages: any[]) => {
  if (!stages || stages.length === 0) return ''
  
  // 🔥 修复：查找 stage_description 阶段的内容（支持中英文 stage 名称）
  const descStage = stages.find(stage => 
    stage.id === 'stage_description' || 
    stage.name === '数据结果描述' ||
    stage.name === 'Result Description' ||
    stage.id === 'data_analysis' || 
    stage.name === '数据分析' ||
    stage.name === 'Data Analysis'
  )
  return descStage?.content || ''
}

// 判断图表是否正在生成中（stage_chart 存在但未完成）
const isChartGenerating = (stages: any[]) => {
  if (!stages || stages.length === 0) return false
  const chartStage = stages.find(s => s.id === 'stage_chart')
  if (!chartStage) return false
  // status 为 'completed' 时图表已生成完毕
  return chartStage.status !== 'completed'
}

// 切换会话后再切回时，优先用 message.chartData，若无则从 stage_chart.metadata.chartData 取，保证与 AI 下发的数据源一致
const getMessageChartData = (message: any) => {
  if (message.chartData && message.chartData.columns && message.chartData.rows) return message.chartData
  const stages = message.stages || []
  const chartStage = stages.find((s: any) => s.id === 'stage_chart')
  if (chartStage?.metadata?.chartData) return chartStage.metadata.chartData
  return undefined
}

// 图表类型与数据源一致：优先 message.chartType，否则从 stage_chart 取
const getMessageChartType = (message: any) => {
  if (message.chartType) return message.chartType
  const chartStage = (message.stages || []).find((s: any) => s.id === 'stage_chart')
  return chartStage?.metadata?.chart_type || chartStage?.metadata?.chart_config?.recommendedChart
}

// 处理回车键
const handleShiftEnter = (event) => {
  // 允许 Shift+Enter 插入换行
  event.preventDefault()
  const textarea = event.target
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const text = textarea.value
  textarea.value = text.substring(0, start) + '\n' + text.substring(end)
  textarea.selectionStart = textarea.selectionEnd = start + 1
}

// 数据源变更
const handleDataSourceChange = async (value: string | null) => {
  currentDataSource.value = value
  // 清空数据表选择
  currentDataTables.value = []
  
  // 更新 chatStore（需要传递数组格式以保持兼容性）
  chatStore.setDataSource(value ? [value] : [])
  
  // 加载选中数据源下的数据表
  if (value) {
    await dataPrepStore.loadDataTables(value)
    
    // 🆕 自动选择第一个表作为默认值
    const tables = dataPrepStore.getDataTablesBySourceId(value)
    if (tables && tables.length > 0) {
      currentDataTables.value = [tables[0].id]
      chatStore.setDataTables([tables[0].id])
      console.log('✅ 自动选择第一个表作为默认值:', tables[0].name)
    }
  }
}

// 数据表变更
const handleDataTableChange = (values) => {
  currentDataTables.value = values
  chatStore.setDataTables(values)
}

// 打开数据表预览
const openDataTablePreview = () => {
  // 获取选中的数据表信息
  const selectedTables = availableDataTables.value.filter(table =>
    currentDataTables.value.includes(table.id)
  )
  
  console.log('=== 数据表预览调试信息 ===')
  console.log('currentDataTables:', currentDataTables.value)
  console.log('availableDataTables:', availableDataTables.value)
  console.log('selectedTables:', selectedTables)
  
  if (selectedTables.length === 0) {
    ElMessage.warning('请先选择数据表')
    return
  }
  
  // 设置选中的表列表供预览模态框使用
  selectedTablesForPreview.value = selectedTables
  
  // 如果只选择了一张表，直接预览
  if (selectedTables.length === 1) {
    isMultiTable.value = false
    console.log('预览单表:', selectedTables[0])
    handleDataSourcePreview(selectedTables[0])
  } else {
    // 多张表，显示选择对话框
    isMultiTable.value = true
    // 默认预览第一张表
    console.log('预览多表，默认第一张:', selectedTables[0])
    handleDataSourcePreview(selectedTables[0])
  }
  
  // 打开预览模态框
  dataPreviewModalVisible.value = true
}

// 处理预览表切换
const handlePreviewTableChange = async (tableId) => {
  // 根据表ID找到对应的表对象
  const table = selectedTablesForPreview.value.find(t => t.id === tableId)
  if (table) {
    await handleDataSourcePreview(table)
  }
}

// 处理数据源重试
const handleDataSourceRetry = () => {
  dataPrepStore.resetDataSourceState()
  dataPrepStore.loadDataSources()
}

// 处理数据源选择确认
const handleDataSourceConfirm = (selectedTables) => {
  // 更新当前选择的数据源
  currentDataSource.value = selectedTables.map(table => table.id)
  chatStore.setDataSource(currentDataSource.value)
  dataSourceSelectorVisible.value = false
}

// 处理数据源预览
const handleDataSourcePreview = async (table) => {
  try {
    // 防御性检查：确保 table 对象存在且有 id
    if (!table || !table.id) {
      console.error('无效的表对象:', table)
      ElMessage.error('无效的表对象，无法预览')
      return
    }
    
    // 显示加载状态
    uiStore.setLoading(true, '正在加载表预览数据...')
    
    // 调用后端 API 获取表字段信息
    // 注意：后端 API 端点是 /data-tables/{table_id}/columns，不是 /fields
    const fields = await dataTableApi.getFields(table.id)
    
    // 调用后端 API 获取表数据预览
    // 注意：后端可能还没有实现 preview 端点
    const data = await dataTableApi.getPreview(table.id, 100)
    
    // 转换字段信息为预览格式
    const schema = fields.map(field => ({
      name: field.field_name,
      type: field.data_type,
      description: field.description || '',
      unit: '',
      category: '',
      isPrimaryKey: field.is_primary_key
    }))
    
    // 更新预览数据
    previewData.value = {
      schema,
      data
    }
    
    // 打开预览模态框
    dataPreviewModalVisible.value = true
    
  } catch (error) {
    console.error('加载表预览数据失败:', error)
    
    // 检查是否是 404 错误（API 端点不存在）
    if (error.response?.status === 404) {
      ElMessage.warning('预览功能暂未实现，请等待后端 API 开发完成')
    } else {
      ElMessage.error(`加载表预览数据失败: ${error.message || '未知错误'}`)
    }
    
    // 即使失败也显示空数据，避免界面卡住
    previewData.value = {
      schema: [],
      data: []
    }
    
    // 仍然打开模态框，显示"暂无数据"
    dataPreviewModalVisible.value = true
  } finally {
    uiStore.setLoading(false)
  }
}

// 上传图片
const uploadImage = () => {
  console.log('上传图片')
}

// 上传文件
const uploadFile = () => {
  const fileInput = document.getElementById('file-upload')
  if (fileInput) {
    fileInput.click()
  }
}

// 处理文件上传
const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    // 验证文件类型
    const allowedTypes = ['.csv', '.xlsx', '.xls', '.txt', '.json']
    const fileExtension = file.name.substring(file.name.lastIndexOf('.'))
    
    if (!allowedTypes.includes(fileExtension.toLowerCase())) {
      console.warn('不支持的文件类型:', file.name)
      alert('仅支持 .csv, .xlsx, .xls, .txt, .json 文件格式')
      event.target.value = '' // 清空文件输入
      return
    }
    
    // 在控制台显示文件信息
    console.log('上传文件信息:', {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    })
    
    // 这里可以调用后端 API 上传文件
    // uploadFileToServer(file)
    
    // 清空文件输入
    event.target.value = ''
  }
}

// 生成会话标题
const generateSessionTitle = async (firstMessage: string) => {
  try {
    const sessionId = chatStore.currentSessionId
    if (!sessionId) return
    
    console.log('🎯 开始生成会话标题...')
    
    const response = await axios.post(`/api/sessions/generate-title`, {
      session_id: sessionId,
      first_message: firstMessage,
      language: localeStore.locale === 'en-US' ? 'en' : 'zh'  // 转换为后端期望的格式
    })
    
    if (response.data.success) {
      const title = response.data.data.title
      console.log('✅ 会话标题已生成:', title)
      
      // 更新本地会话标题
      const session = chatStore.sessions[sessionId]
      if (session) {
        session.title = title
        console.log('✅ 本地会话标题已更新')
      }
    }
  } catch (error) {
    console.error('生成会话标题失败:', error)
  }
}

// 发送消息
const sendMessage = async () => {
  console.log('=== 📤 sendMessage 开始执行 ===')
  console.log('⏱️ 时间戳:', new Date().toLocaleTimeString())
  console.log('📋 canSend.value:', canSend.value)
  console.log('📝 inputText.value:', inputText.value)
  console.log('🔗 currentDataSource.value:', currentDataSource.value)
  console.log('🆔 chatStore.currentSessionId:', chatStore.currentSessionId)
  console.log('📚 chatStore.sessions 数量:', Object.keys(chatStore.sessions).length)
  
  // 检查输入是否为空
  const text = inputText.value.trim()
  if (!text) {
    console.log('⚠️ 输入为空，退出发送')
    return
  }

  // 强校验：没有数据源时禁止发送，避免后端报“未提供数据源ID”
  if (!currentDataSource.value) {
    ElMessage.warning('请先选择数据源')
    console.warn('⚠️ 未选择数据源，取消发送')
    return
  }
  
  // 📝 前端日志：记录用户输入
  console.log('=' .repeat(80))
  console.log('👤 用户操作')
  console.log('操作: 发送消息')
  console.log('详情:', {
    user_input: text,
    data_source_id: currentDataSource.value,
    data_tables: currentDataTables.value,
    chat_mode: chatStore.chatMode,
    session_id: chatStore.currentSessionId,
    timestamp: new Date().toISOString()
  })
  console.log('=' .repeat(80))
  
  console.log('✅ 输入检查通过，继续发送')
  console.log('🔍 当前 currentDataSource:', currentDataSource.value)
  console.log('🔍 当前 dataSources:', dataSources.value)
  
  // 1. 🔒 关键：确保会话在发送消息前就已创建（即使 AI 失败，会话也会保留）
  let backendSessionCreated = false
  
  if (!chatStore.currentSessionId) {
    console.log('📝 无活跃会话，创建新会话（标题：新对话）')
    const newSessionId = chatStore.createSession('新对话')
    console.log('✅ 前端会话已创建，ID:', newSessionId)
    
    // 同步创建后端会话（使用默认标题"新对话"）
    // 🔴 重要：必须等待后端会话创建成功，否则后续保存消息会失败
    try {
      const response = await axios.post(`/api/sessions/create`, {
        session_id: newSessionId,
        title: '新对话'  // 明确指定默认标题
      })
      console.log('✅ 后端会话已创建（标题：新对话）', response.data)
      backendSessionCreated = response.data.success === true
    } catch (error) {
      console.error('❌ 后端会话创建失败:', error)
      backendSessionCreated = false
      // 🔴 如果后端会话创建失败，不能继续保存消息到后端
      // 但前端会话已创建，用户仍然可以看到会话
      ElMessage.warning('会话创建失败，消息将仅保存在本地')
    }
  } else {
    // 已有会话，需要验证后端会话是否存在
    console.log('📝 检测到已有会话，验证后端会话是否存在...')
    const existingSessionId = chatStore.currentSessionId
    
    try {
      // 尝试获取后端会话，验证是否存在
      const checkResponse = await axios.get(`/api/sessions/${existingSessionId}`)
      
      if (checkResponse.data.success) {
        console.log('✅ 后端会话已存在:', existingSessionId)
        backendSessionCreated = true
      } else {
        console.log('⚠️ 后端会话不存在，需要创建')
        backendSessionCreated = false
      }
    } catch (error) {
      // 如果获取失败（404），说明后端会话不存在，需要创建
      if (error.response?.status === 404) {
        console.log('⚠️ 后端会话不存在（404），创建新的后端会话...')
        
        try {
          // 获取前端会话的标题
          const session = chatStore.sessions[existingSessionId]
          const title = session?.title || '新对话'
          
          const createResponse = await axios.post(`/api/sessions/create`, {
            session_id: existingSessionId,
            title: title
          })
          
          console.log('✅ 后端会话已创建:', createResponse.data)
          backendSessionCreated = createResponse.data.success === true
        } catch (createError) {
          console.error('❌ 创建后端会话失败:', createError)
          backendSessionCreated = false
          ElMessage.warning('会话同步失败，消息将仅保存在本地')
        }
      } else {
        console.error('❌ 检查后端会话失败:', error)
        backendSessionCreated = false
        ElMessage.warning('无法连接到服务器，消息将仅保存在本地')
      }
    }
  }
  
  console.log('✅ 会话已就绪，Session ID:', chatStore.currentSessionId)
  console.log('🔍 后端会话状态:', backendSessionCreated ? '已创建' : '未创建')
  
  console.log('💾 保存消息内容:', text)
  inputText.value = '' // 先清空输入框提升用户体验
  console.log('✅ 输入框已清空')
  
  // 2. 添加用户消息到 Store
  console.log('📝 正在添加用户消息到 Store...')
  const userMessageId = chatStore.addMessage({
    role: 'user',
    type: 'text',
    content: text,
    status: 'sent'
  })
  console.log('✅ 用户消息已添加，ID:', userMessageId)
  console.log('📊 当前消息列表长度:', chatStore.currentMessages.length)
  
  // 2.1 不再在前端保存用户消息到后端数据库
  // 后端会在 chat_orchestrator.py 中统一保存所有消息
  console.log('ℹ️ 用户消息将由后端统一保存（chat_orchestrator.py）')
  
  // 2.5. 如果是第一条消息，异步生成会话标题（不阻塞主流程）
  const isFirstMessage = chatStore.currentMessages.length === 1
  if (isFirstMessage && backendSessionCreated) {
    console.log('🎯 检测到首条消息，准备生成会话标题')
    generateSessionTitle(text).catch(error => {
      console.warn('生成会话标题失败（不影响前端）:', error)
    })
  }
  
  // 3. 建立 WebSocket 连接（用于接收执行过程消息）
  console.log('🔌 建立 WebSocket 连接...')
  const sessionId = chatStore.currentSessionId!;
  
  try {
    // 🔥 修复：如果已有 WebSocket 实例，先断开
    if (currentWSService) {
      console.log('⚠️ 检测到已有 WebSocket 实例，先断开...')
      try {
        currentWSService.disconnect()
      } catch (e) {
        console.warn('断开旧 WebSocket 失败:', e)
      }
      currentWSService = null
    }
    
    // 创建 WebSocket 服务实例
    const wsService = createWebSocketService(sessionId)
    
    // 连接 WebSocket
    await wsService.connect()
    console.log('✅ WebSocket 连接成功')
    
    // 注册消息处理器
    wsService.onMessage(handleWSMessage)
    
    // 保存 WebSocket 实例（用于后续清理）
    currentWSService = wsService
    
    // 等待一小段时间确保连接完全建立
    await new Promise(resolve => setTimeout(resolve, 200))
    console.log('✅ WebSocket 连接已稳定')
  } catch (error) {
    console.warn('⚠️ WebSocket 连接失败，将无法显示执行过程:', error)
    // WebSocket 失败不影响主流程，继续执行
  }
  
  // 4. 设置流式状态
  console.log('⏳ 设置流式状态为 true')
  chatStore.setStreaming(true)
  console.log('✅ 流式状态已设置，isStreaming:', chatStore.isStreaming)
  
  // 5. 发起请求
  
  // 🆕 收集最近 30 轮对话历史（最多 60 条消息：30 轮 = 30 个用户消息 + 30 个 AI 回复）
  // ⚠️ 排除最后一条消息（即刚添加的当前用户消息），避免重复发送
  const currentMessages = chatStore.currentMessages

  // 🔥 修复：AI 消息的 content 在 store 里是空字符串，实际内容在 stages 里
  // 需要从 stages 中提取关键阶段内容（意图澄清 + SQL生成），作为历史上下文
  // 注意：跳过 stage_thinking（内容过长），SQL 里已包含具体日期范围
  const extractAssistantContent = (msg: any): string => {
    // 优先用 content（如果非空）
    if (msg.content && msg.content.trim()) return msg.content

    // 从 stages 提取关键阶段内容（意图澄清 + SQL生成，不含 thinking 避免过长）
    if (msg.stages && msg.stages.length > 0) {
      const keyStages = ['stage_clarification', 'sql_generation']
      const parts = msg.stages
        .filter((s: any) => keyStages.includes(s.id) && s.content)
        .map((s: any) => `【${s.name || s.id}】\n${s.content}`)
      if (parts.length > 0) return parts.join('\n\n')
    }
    return ''
  }

  const historyMessages = currentMessages.slice(0, -1).slice(-60)
    .map(msg => ({
      role: msg.role,
      content: msg.role === 'assistant' ? extractAssistantContent(msg) : (msg.content || ''),
      timestamp: new Date(msg.timestamp).toISOString()
    }))
    .filter(msg => msg.content.trim() !== '')  // 过滤掉内容为空的消息
  
  console.log('📚 收集历史消息:', historyMessages.length, '条（已排除当前消息）')
  
  // 构建请求体
  const fallbackDataSource = Array.isArray(chatStore.dataSource) && chatStore.dataSource.length > 0
    ? chatStore.dataSource[0]
    : null
  const resolvedDataSourceId = currentDataSource.value || fallbackDataSource

  const requestBody = {
    user_question: text,
    data_source_id: resolvedDataSourceId || null,
    selected_tables: currentDataTables.value.length > 0 ? currentDataTables.value : null,  // 🆕 传递选择的表 ID
    history_messages: historyMessages.length > 0 ? historyMessages : null,
    response_language: localeStore.locale === 'en-US' ? 'en' : 'zh'  // 🆕 i18n: 使用 UI 语言设置，而非检测输入文本语言
  }
  
  const url = `/api/chat/start/${sessionId}`;
  console.log('🌐 发起请求 URL:', url)
  console.log('🌐 请求方法: POST')
  console.log('🌐 请求体:', requestBody)
  
  // 📝 前端日志：记录 API 请求
  console.log('=' .repeat(80))
  console.log('📥 API 请求')
  console.log('端点: POST', url)
  console.log('请求体:', JSON.stringify(requestBody, null, 2))
  console.log('=' .repeat(80))
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    })
    
    console.log('🌐 响应状态:', response.status)
    console.log('🌐 响应状态文本:', response.statusText)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('🌐 错误响应体:', errorText)
      throw new Error(`服务器响应异常: ${response.status} ${response.statusText}`)
    }
    
    const result = await response.json()
    console.log('✅ 请求成功，后端返回:', result)
    
    // 📝 前端日志：记录 API 响应
    console.log('=' .repeat(80))
    console.log('📤 API 响应')
    console.log('端点:', url)
    console.log('状态码:', response.status)
    console.log('响应:', JSON.stringify(result, null, 2))
    console.log('=' .repeat(80))
    
    // 5. 处理后端返回的不同响应类型
    console.log('📝 处理后端返回数据...')
    console.log('📊 返回数据结构:', result)
    
    if (!result.success) {
      // 处理错误响应
      console.error('❌ 后端返回错误:', result.message || result.error)
      
      // 添加错误消息到前端（不抛出异常，让会话保留）
      chatStore.addMessage({
        role: 'assistant',
        type: 'error',
        content: result.message || result.error || '对话处理失败，请重试',
        status: 'error'
      })
      
      // 关闭流式状态
      chatStore.setStreaming(false)
      
      // 不抛出异常，让会话保留
      console.log('⚠️ AI 处理失败，但会话已保留')
      return
    }
    
    if (result.data) {
      const data = result.data
      
      // 检查是否需要澄清
      if (data.needs_clarification && data.clarification_question) {
        console.log('🤔 需要澄清，显示澄清问题')
        
        // 收集思考步骤（如果有）
        const thinkingSteps = []
        
        if (data.intent) {
          const intentMap = {
            'smart_query': '智能问数',
            'report_generation': '生成报告',
            'data_followup': '数据追问',
            'clarification': '澄清确认',
            'unknown': '未知意图'
          }
          const intentText = intentMap[data.intent] || data.intent
          thinkingSteps.push({
            title: '意图识别',
            content: `识别到您的问题类型为：**${intentText}**`,
            stage: 'intent_recognition'
          })
        }
        
        if (data.tables && data.tables.length > 0) {
          thinkingSteps.push({
            title: '智能选表',
            content: `已选择相关数据表：\n${data.tables.map(t => `- ${t}`).join('\n')}`,
            stage: 'table_selection'
          })
        }
        
        // 添加澄清消息
        chatStore.addMessage({
          role: 'assistant',
          type: 'clarification',
          content: data.clarification_question,
          status: 'received',
          metadata: {
            tables: data.tables,
            intent: data.intent,
            steps: thinkingSteps,
            stepsCollapsed: false,
            needsClarification: true
          }
        })
        
        // 保存澄清消息到数据库
        try {
          await axios.post(`/api/sessions/${chatStore.currentSessionId}/messages`, {
            role: 'assistant',
            content: data.clarification_question,
            message_type: 'cloud'
          })
          console.log('✅ 澄清消息已保存到数据库')
        } catch (error) {
          console.warn('⚠️ 保存澄清消息到数据库失败:', error)
        }
        
        console.log('✅ 澄清问题已显示')
      } else if (currentStreamingMessageId) {
        // 🔥 如果已经有流式消息（通过 WebSocket 创建），说明流式处理已完成
        console.log('ℹ️ 已有流式消息，流式处理已完成，ID:', currentStreamingMessageId)
        
        // 只需要标记流式消息为完成状态
        chatStore.updateMessage(currentStreamingMessageId, {
          status: 'completed'
        })
        
        // ⚠️ 不在这里保存消息！由 complete 事件统一保存（包含 stages）
        console.log('ℹ️ 等待 complete 事件保存消息（包含 stages）')
        
        console.log('✅ AI 回复已完成（使用流式消息）')
      } else if (data.analysis) {
        // 处理正常分析结果（降级方案：WebSocket 失败时使用）
        console.log('📝 处理正常分析结果（降级方案）')
        
        // 如果没有流式消息（WebSocket 失败），则创建一个新消息
        console.log('ℹ️ 没有流式消息，创建新消息（降级方案）')
        
        // 收集思考步骤
        const thinkingSteps = []
        
        // 步骤1: 意图识别
        if (data.intent) {
          console.log('📝 收集意图识别步骤')
          const intentMap = {
            'smart_query': '智能问数',
            'report_generation': '生成报告',
            'data_followup': '数据追问',
            'clarification': '澄清确认',
            'unknown': '未知意图'
          }
          const intentText = intentMap[data.intent] || data.intent
          thinkingSteps.push({
            title: '意图识别',
            content: `识别到您的问题类型为：**${intentText}**`,
            stage: 'intent_recognition'
          })
        }
        
        // 步骤2: 智能选表
        if (data.tables && data.tables.length > 0) {
          console.log('📝 收集智能选表步骤')
          thinkingSteps.push({
            title: '智能选表',
            content: `已选择相关数据表：\n${data.tables.map(t => `- ${t}`).join('\n')}`,
            stage: 'table_selection'
          })
        }
        
        // 步骤3: SQL生成
        if (data.sql) {
          console.log('📝 收集SQL生成步骤')
          thinkingSteps.push({
            title: 'SQL生成',
            content: `\`\`\`sql\n${data.sql}\n\`\`\``,
            stage: 'sql_generation'
          })
        }
        
        // 创建包含思考步骤和分析结果的完整 AI 消息
        console.log('📝 添加完整AI消息（包含思考步骤和分析结果）')
        const fullText = data.analysis
        let currentText = ''
        
        // 添加 AI 消息，包含思考步骤
        const aiMessageId = chatStore.addMessage({
          role: 'assistant',
          type: 'text',
          content: '',
          status: 'streaming',
          metadata: {
            sql: data.sql,
            tables: data.tables,
            intent: data.intent,
            steps: thinkingSteps,
            stepsCollapsed: false // 默认展开
          }
        })
        
        // 打字机效果显示分析结果
        const charsPerStep = 10
        const delay = 30
        
        for (let i = 0; i < fullText.length; i += charsPerStep) {
          currentText = fullText.substring(0, i + charsPerStep)
          chatStore.updateMessage(aiMessageId, {
            content: currentText,
            status: i + charsPerStep >= fullText.length ? 'received' : 'streaming'
          })
          await new Promise(resolve => setTimeout(resolve, delay))
        }
        
        // 保存完整的 AI 分析消息到数据库
        try {
          await axios.post(`/api/sessions/${chatStore.currentSessionId}/messages`, {
            role: 'assistant',
            content: fullText,
            message_type: 'local'
          })
          console.log('✅ AI 分析消息已保存到数据库')
        } catch (error) {
          console.warn('⚠️ 保存 AI 消息到数据库失败:', error)
        }
        
        console.log('✅ AI 回复已完成（降级方案）')
      } else {
        // 没有流式消息，也没有 analysis，也没有 clarification_question
        // 这种情况通常不应该发生，记录警告但不添加额外消息
        console.warn('⚠️ 后端返回数据不完整：没有流式消息、analysis 或 clarification_question')
        console.warn('📊 当前状态: currentStreamingMessageId =', currentStreamingMessageId)
        console.warn('📊 返回数据:', data)
      }
    }
    
    // 6. 关闭流式状态
    chatStore.setStreaming(false)
    console.log('✅ 流式状态已关闭')
    
    console.log('=== ✅ sendMessage 执行完成 ===')
    
  } catch (err) {
    console.error('=== ❌ sendMessage 执行出错 ===')
    console.error('❌ 错误信息:', (err as Error).message)
    console.error('❌ 错误堆栈:', (err as Error).stack)
    
    ElMessage.error('发送失败: ' + (err as Error).message)
    chatStore.setStreaming(false)
    
    // 添加错误消息
    chatStore.addMessage({
      role: 'system',
      type: 'error',
      content: '消息发送失败，请重试',
      status: 'error'
    })
  }
}

// 刷新消息
const refreshMessage = (message) => {
  // 实现刷新逻辑
  console.log('刷新消息:', message)
}

// 点赞消息
const likeMessage = (message) => {
  // 实现点赞逻辑
  console.log('点赞消息:', message)
}

// 点踩消息
const dislikeMessage = (message) => {
  // 实现点踩逻辑
  console.log('点踩消息:', message)
}

// 切换思考步骤的折叠/展开
const toggleThinkingSteps = (message) => {
  if (message.metadata) {
    message.metadata.stepsCollapsed = !message.metadata.stepsCollapsed
  }
}

// 处理 WebSocket 消息
const handleWSMessage = async (wsMessage: WSMessage) => {
  switch (wsMessage.type) {
    case 'stage_start':
      // 处理阶段开始消息
      console.log('🚀 [Home.vue] 接收到 stage_start 消息:', {
        stage_id: wsMessage.stage_id,
        stage_name: wsMessage.stage_name,
        content: wsMessage.content,
        reset: wsMessage.metadata?.reset,
        currentStreamingMessageId,
        timestamp: Date.now()
      })
      
      if (!currentStreamingMessageId) {
        // 如果还没有流式消息，创建一个
        currentStreamingMessageId = chatStore.addMessage({
          role: 'assistant',
          type: 'stage',
          content: '',
          status: 'streaming',
          stages: []
        })
        console.log('🆕 [Home.vue] 创建新的流式消息:', currentStreamingMessageId)
      }

      // 🔄 reset=true 时：SQL执行失败后重新生成，清空旧 stage 内容重新流式输出
      if (wsMessage.metadata?.reset && wsMessage.stage_id) {
        console.log('🔄 [Home.vue] SQL执行失败重试，重置 stage 内容:', wsMessage.stage_id)
        chatStore.updateStageInMessage(currentStreamingMessageId, wsMessage.stage_id, {
          content: '',
          status: 'in_progress',
          collapsed: false
        })
      } else {
        // 正常首次创建 stage
        chatStore.addStageToMessage(currentStreamingMessageId, {
          id: wsMessage.stage_id!,
          name: wsMessage.stage_name!,
          content: wsMessage.content,
          status: wsMessage.stage_status || 'in_progress',
          collapsed: wsMessage.collapsed || false,
          timestamp: Date.now()
        })
        console.log('✅ [Home.vue] stage_start 已添加到 store')
      }
      
      // 🆕 自动滚动到底部
      scrollToBottom()
      break

    case 'stage_update':
      // 🔍 调试日志：接收到 stage_update WebSocket 消息
      console.log('🌊 [Home.vue] 接收到 stage_update 消息:', {
        stage_id: wsMessage.stage_id,
        contentLength: wsMessage.content?.length,
        contentPreview: wsMessage.content?.substring(0, 50) + (wsMessage.content && wsMessage.content.length > 50 ? '...' : ''),
        timestamp: Date.now()
      })
      
      // 🔥 关键修复：如果还没有流式消息，先创建一个带 stages 数组的消息
      if (!currentStreamingMessageId) {
        console.log('🆕 [Home.vue] 创建新的流式消息（因为收到 stage_update）')
        currentStreamingMessageId = chatStore.addMessage({
          role: 'assistant',
          type: 'stage',
          content: '',
          status: 'streaming',
          stages: []
        })
      }
      
      // 🔥 检查当前消息是否有对应的 stage，如果没有则创建
      const streamingMessage = chatStore.currentMessages.find(m => m.id === currentStreamingMessageId)
      if (streamingMessage && streamingMessage.stages) {
        const stageExists = streamingMessage.stages.some(s => s.id === wsMessage.stage_id)
        if (!stageExists && wsMessage.stage_id) {
          console.log('🆕 [Home.vue] 创建新的 stage:', wsMessage.stage_id)
          // 创建新的 stage
          chatStore.addStageToMessage(currentStreamingMessageId, {
            id: wsMessage.stage_id,
            name: wsMessage.stage_name || wsMessage.stage_id,
            content: '',
            status: 'in_progress',
            collapsed: false,
            timestamp: Date.now()
          })
        }
      }
      
      // 处理阶段更新消息（流式内容）
      if (wsMessage.stage_id) {
        if (wsMessage.content) {
          chatStore.handleStageUpdate(wsMessage.stage_id, wsMessage.content)
          // 🆕 自动滚动到底部
          scrollToBottom()
        }
        // 空 content 的 stage_update 是正常的流式开始信号，不需要警告
      } else {
        console.warn('⚠️ [Home.vue] stage_update 消息缺少必要字段:', wsMessage)
      }
      break

    case 'stage_complete':
      // 处理阶段完成消息
      console.log('🏁 [Home.vue] 接收到 stage_complete 消息:', {
        stage_id: wsMessage.stage_id,
        stage_name: wsMessage.stage_name,
        hasContent: !!wsMessage.content,
        hasMetadata: !!wsMessage.metadata,
        timestamp: Date.now()
      })
      
      if (currentStreamingMessageId && wsMessage.stage_id) {
        // 🔥 关键修复：如果 stage_complete 的 content 为空，保留原有内容
        const updateData: any = {
          status: wsMessage.stage_status || 'completed',
          collapsed: wsMessage.collapsed !== undefined ? wsMessage.collapsed : false
        }
        
        // 只有当 content 不为空时才更新内容
        if (wsMessage.content && wsMessage.content.length > 0) {
          // SQL 生成阶段：若已在流式阶段拿到内容（通常包含更好的换行格式），
          // 则不要在 stage_complete 用单行 SQL 覆盖它。
          const currentMessage = chatStore.currentMessages.find(m => m.id === currentStreamingMessageId)
          const existingStage = currentMessage?.stages?.find((s: any) => s.id === wsMessage.stage_id)
          const hasStreamingContent = !!existingStage?.content && existingStage.content.trim().length > 0
          const isSqlGenerationStage = wsMessage.stage_id === 'sql_generation'
          if (!(isSqlGenerationStage && hasStreamingContent)) {
            updateData.content = wsMessage.content
          }
        }
        
        // 如果有 metadata，也要更新
        if (wsMessage.metadata) {
          updateData.metadata = wsMessage.metadata
        }
        
        chatStore.updateStageInMessage(currentStreamingMessageId, wsMessage.stage_id, updateData)
        
        console.log('✅ [Home.vue] stage_complete 已更新到 store')
        
        // 🔥 SQL执行完成后立即折叠 Deep Thinking Process（不等数据结果描述）
        if (wsMessage.stage_id === 'stage_execute') {
          chatStore.updateMessage(currentStreamingMessageId, { thinkingCollapsed: true })
          console.log('🔽 [Home.vue] SQL执行完成，折叠 Deep Thinking Process')
        }
        
        // 🆕 自动滚动到底部
        scrollToBottom()
      } else {
        console.warn('⚠️ [Home.vue] stage_complete 缺少必要信息:', {
          hasMessageId: !!currentStreamingMessageId,
          hasStageId: !!wsMessage.stage_id
        })
      }
      break

    case 'thinking':
      // 如果还没有流式消息，创建一个
      if (!currentStreamingMessageId) {
        currentStreamingMessageId = chatStore.addMessage({
          role: 'assistant',
          type: 'thinking',
          content: wsMessage.content,
          status: 'streaming',
          metadata: {
            steps: []
          }
        })
      }
      
      // 🆕 构建步骤对象
      const data = wsMessage.metadata || {}
      const stage = data.stage || 'unknown'
      
      // 获取步骤标题和图标
      const getStepTitle = (stage: string) => {
        const titles: Record<string, string> = {
          'intent_recognition': '意图识别',
          'table_selection': '智能选表',
          'sql_generation': 'SQL生成',
          'sql_execution': 'SQL执行',
          'data_analysis': '数据分析'
        }
        return titles[stage] || stage
      }
      
      const getStepIcon = (stage: string) => {
        const icons: Record<string, string> = {
          'intent_recognition': '🔍',
          'table_selection': '📊',
          'sql_generation': '⚙️',
          'sql_execution': '🚀',
          'data_analysis': '📈'
        }
        return icons[stage] || '📝'
      }
      
      // 构建步骤对象
      const step = {
        title: getStepTitle(stage),
        icon: getStepIcon(stage),
        stage: stage,
        status: 'success' as const,
        content: wsMessage.content,
        collapsed: false,
        sql: data.sql,
        tables: data.tables,  // 🆕 包含完整的表信息（字段、数据字典、表关联）
        executionTime: data.executionTime,
        totalRows: data.totalRows
      }
      
      // 添加步骤到当前消息
      const currentMessage = chatStore.messages.find(m => m.id === currentStreamingMessageId)
      if (currentMessage && currentMessage.metadata) {
        if (!currentMessage.metadata.steps) {
          currentMessage.metadata.steps = []
        }
        currentMessage.metadata.steps.push(step)
      }
      break

    case 'status':
      // 状态更新也追加到流式消息中
      if (currentStreamingMessageId) {
        chatStore.appendMessageContent(currentStreamingMessageId, '\n' + wsMessage.content)
      }
      break

    case 'message':
      // 追加流式内容
      if (currentStreamingMessageId) {
        chatStore.appendMessageContent(currentStreamingMessageId, wsMessage.content)
        
        // 🆕 自动滚动到底部
        scrollToBottom()
      }
      break

    case 'result':
      // 完成当前思考消息
      if (currentStreamingMessageId) {
        chatStore.updateMessage(currentStreamingMessageId, {
          status: 'completed'
        })
      }

      // 处理查询结果数据
      let chartData: ChartData | undefined
      let chartType: string | undefined
      let tableData: any[] | undefined
      let tableHeaders: string[] | undefined
      let viewMode = 'chart' // 默认显示图表视图

      // 如果元数据包含查询结果
      if (wsMessage.metadata?.queryResult) {
        const queryResult = wsMessage.metadata.queryResult
        
        // 提取表格数据
        if (queryResult.columns && queryResult.rows) {
          tableHeaders = queryResult.columns
          tableData = queryResult.rows
          
          // 构建 ChartData 格式
          chartData = {
            title: wsMessage.metadata.chartTitle || '查询结果',
            columns: queryResult.columns,
            rows: queryResult.rows,
            metadata: {
              columnTypes: queryResult.columnTypes || []
            }
          }
          
          // 使用 AI 智能选择图表类型
          try {
            const chartSelection = await aiChartSelector.selectChartType({
              data: chartData,
              userQuestion: wsMessage.metadata.userQuestion,
              context: wsMessage.metadata.context
            })
            
            chartType = chartSelection.primary.type
            console.log('AI Chart Selection:', chartSelection)
          } catch (error) {
            console.warn('Failed to select chart type with AI:', error)
            chartType = 'auto' // 降级到自动选择
          }
        }
      }

      // 🔥 修复：将图表数据合并到已有的 stage 消息，而不是新建消息
      // 避免历史恢复时出现两条 assistant 消息（顺序错乱）
      if (currentStreamingMessageId) {
        chatStore.updateMessage(currentStreamingMessageId, {
          chartData,
          chartType,
          tableData,
          tableHeaders,
          viewMode,
          content: wsMessage.content || ''
        })
      } else {
        // 兜底：如果没有流式消息，才新建（理论上不应走到这里）
        currentStreamingMessageId = chatStore.addMessage({
          role: 'assistant',
          type: 'text',
          content: wsMessage.content,
          status: 'completed',
          metadata: wsMessage.metadata,
          chartData,
          chartType,
          tableData,
          tableHeaders,
          viewMode
        })
      }
      break

    case 'error':
      // 创建错误消息
      chatStore.addMessage({
        role: 'system',
        type: 'error',
        content: wsMessage.content,
        status: 'error'
      })
      chatStore.setStreaming(false)
      currentStreamingMessageId = null
      ElMessage.error(`错误: ${wsMessage.content}`)
      break

    case 'complete':
      // 完成流式输出
      if (currentStreamingMessageId) {
        // 🔥 如果 complete 消息包含图表数据，更新到消息对象
        const updateData: any = {
          status: 'completed',
          thinkingCollapsed: true  // 🔥 标记思考过程应该折叠
        }
        
        if (wsMessage.metadata?.chartData) {
          updateData.chartData = wsMessage.metadata.chartData
          console.log('📊 [complete] 接收到图表数据:', {
            columns: wsMessage.metadata.chartData.columns?.length,
            rows: wsMessage.metadata.chartData.rows?.length,
            fullData: wsMessage.metadata.chartData  // 🔍 打印完整数据
          })
        }
        
        if (wsMessage.metadata?.chartType) {
          updateData.chartType = wsMessage.metadata.chartType
          console.log('📊 [complete] 图表类型:', wsMessage.metadata.chartType)
        }
        
        chatStore.updateMessage(currentStreamingMessageId, updateData)
        
        // 🔥 关键修复：图表数据到达时，将 stage_chart 标记为 completed
        // 否则 isChartGenerating 始终返回 true，AIMessage 的 watch 会一直保持 showChart=false
        if (wsMessage.metadata?.chartData) {
          chatStore.updateStageInMessage(currentStreamingMessageId, 'stage_chart', {
            status: 'completed'
          })
          console.log('✅ [complete] stage_chart 已标记为 completed，图表将显示')
        }
        
        // 🔥 保存消息到数据库（包含 stages 数据）
        const message = chatStore.currentMessages.find(m => m.id === currentStreamingMessageId)
        if (message && message.role === 'assistant' && chatStore.currentSessionId) {
          // 🔥 关键修复：将 chartData 保存到 stage_chart 的 metadata 中
          if (message.stages && wsMessage.metadata?.chartData) {
            const chartStage = message.stages.find(s => s.id === 'stage_chart')
            if (chartStage) {
              // 确保 metadata 对象存在
              if (!chartStage.metadata) {
                chartStage.metadata = {}
              }
              // 保存完整的图表数据到 metadata
              chartStage.metadata.chartData = wsMessage.metadata.chartData
              console.log('✅ [complete] 已将 chartData 保存到 stage_chart.metadata:', {
                columns: wsMessage.metadata.chartData.columns?.length,
                rows: wsMessage.metadata.chartData.rows?.length,
                fullData: wsMessage.metadata.chartData  // 🔍 打印完整数据
              })
            } else {
              console.warn('⚠️ [complete] 未找到 stage_chart，无法保存 chartData')
            }
          }
          
          // 🔍 调试日志：检查消息对象
          console.log('💾 [complete] 准备保存消息到数据库:', {
            messageId: message.id,
            role: message.role,
            contentLength: message.content?.length || 0,
            stagesCount: message.stages?.length || 0,
            hasChartData: !!message.chartData,
            chartType: message.chartType,
            stages: message.stages,
            sessionId: chatStore.currentSessionId
          })
          
          try {
            // 🔥 先保存对应的用户消息到 local_messages（确保历史对话顺序正确）
            // 找到当前 assistant 消息之前的最后一条 user 消息
            const allMessages = chatStore.currentMessages
            const assistantIndex = allMessages.findIndex(m => m.id === currentStreamingMessageId)
            const userMessage = assistantIndex > 0
              ? [...allMessages].slice(0, assistantIndex).reverse().find(m => m.role === 'user')
              : null

            if (userMessage) {
              await fetch(`/api/sessions/${chatStore.currentSessionId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  role: 'user',
                  content: userMessage.content,
                  message_type: 'local'
                })
              })
              console.log('✅ [complete] 用户消息已保存到 local_messages')
            }

            // 🆕 从 stages 中提取云端 AI 的回答内容（Thinking 阶段）
            // 这些内容将用于历史对话上下文，不包含敏感的数据分析结果
            let contentForHistory = message.content || ''
            
            if (!contentForHistory && message.stages && message.stages.length > 0) {
              // 收集云端 AI 的思考过程（意图识别、智能选表、意图澄清、模型思考、SQL生成）
              const cloudStages = [
                'intent_recognition',    // 意图识别
                'stage_table',           // 智能选表
                'stage_clarification',   // 意图澄清
                'stage_thinking',        // 模型思考
                'sql_generation'         // SQL生成
              ]
              
              const cloudContent = message.stages
                .filter(s => cloudStages.includes(s.id))
                .map(s => {
                  const stageName = s.name || s.id
                  return `【${stageName}】\n${s.content || ''}`
                })
                .filter(c => c.length > 0)
                .join('\n\n')
              
              if (cloudContent) {
                contentForHistory = cloudContent
                console.log('✅ [complete] 使用云端 AI 思考过程作为历史记录')
              }
            }
            
            const payload = {
              role: message.role,
              content: contentForHistory,  // 🔥 使用云端 AI 的回答内容
              message_type: 'local',       // 🔥 修复：保存到 local_messages（包含完整的 stages 数据）
              stages: message.stages || []
            }
            
            console.log('📤 [complete] 发送到后端的数据:', {
              ...payload,
              contentLength: contentForHistory.length,
              contentPreview: contentForHistory.substring(0, 100) + '...'
            })
            
            const response = await fetch(`/api/sessions/${chatStore.currentSessionId}/messages`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(payload)
            })
            
            const result = await response.json()
            console.log('✅ 消息已保存到数据库，响应:', result)
            console.log(`📊 保存了 ${payload.stages.length} 个 stages`)
          } catch (error) {
            console.error('❌ 保存消息失败:', error)
          }
        } else {
          console.warn('⚠️ [complete] 无法保存消息:', {
            hasMessage: !!message,
            role: message?.role,
            hasSession: !!chatStore.currentSessionId
          })
        }
      }
      chatStore.setStreaming(false)
      currentStreamingMessageId = null
      break
  }
}

// 处理连接状态变化
const handleConnectionChange = (connected: boolean) => {
  chatStore.setConnected(connected)
  if (connected) {
    ElMessage.success('连接已建立')
  } else {
    ElMessage.warning('连接已断开')
  }
}

// 处理错误
const handleError = (error: Error) => {
  chatStore.setError(error.message)
  ElMessage.error(`连接错误: ${error.message}`)
}

// 初始化
onMounted(async () => {
  console.log('=== Home.vue onMounted 开始 ===')
  
  // 加载会话和历史记录
  chatStore.loadSessions()
  chatStore.loadHistory()
  
  // 加载数据源（等待完成）
  await dataPrepStore.loadDataSources()
  console.log('数据源加载完成，数量:', dataPrepStore.dataSources.length)
  
  // 设置默认数据源（如果存在）
  if (dataPrepStore.dataSources.length > 0) {
    const activeSource = dataPrepStore.dataSources.find(ds => ds.isActive)
    const defaultSourceId = activeSource ? activeSource.id : dataPrepStore.dataSources[0].id
    
    currentDataSource.value = defaultSourceId
    chatStore.setDataSource([defaultSourceId])
    
    // 加载该数据源下的数据表
    await dataPrepStore.loadDataTables(defaultSourceId)
    
    // 🆕 自动选择第一个表作为默认值
    const tables = dataPrepStore.getDataTablesBySourceId(defaultSourceId)
    if (tables && tables.length > 0) {
      currentDataTables.value = [tables[0].id]
      chatStore.setDataTables([tables[0].id])
      console.log('✅ 自动选择第一个表作为默认值:', tables[0].name)
    }
    
    console.log('默认数据源已设置:', currentDataSource.value)
    console.log('默认数据表已设置:', currentDataTables.value)
  }
  
  console.log('=== Home.vue onMounted 完成 ===')
  
  // 🔧 不再自动连接 WebSocket，改为在发送消息时按需连接
  // WebSocket 用于实时流式输出，当前使用 HTTP 轮询，所以 WebSocket 是可选的
  
  // 🔧 调试工具：暴露到全局作用域
  if (typeof window !== 'undefined') {
    (window as any).__chatDebug = {
      // 获取当前状态
      getState: () => ({
        currentSessionId: chatStore.currentSessionId,
        isStreaming: chatStore.isStreaming,
        isConnected: chatStore.isConnected,
        messagesCount: chatStore.currentMessages.length,
        messages: chatStore.currentMessages,
        sessions: chatStore.sessions,
        inputText: inputText.value,
        currentDataSource: currentDataSource.value,
        currentDataTables: currentDataTables.value
      }),
      
      // 手动发送消息（用于测试）
      sendTestMessage: async (msg: string) => {
        console.log('🧪 发送测试消息:', msg)
        inputText.value = msg
        await sendMessage()
      },
      
      // 查看所有消息
      listMessages: () => {
        console.table(chatStore.currentMessages)
      },
      
      // 清空所有消息
      clearMessages: () => {
        chatStore.clearCurrentSession()
        console.log('✅ 消息已清空')
      },
      
      // 创建新会话
      newSession: () => {
        const sessionId = chatStore.createSession()
        console.log('✅ 新会话已创建:', sessionId)
        return sessionId
      },
      
      // 查看 WebSocket 连接状态
      getWSStatus: () => ({
        isConnected: chatStore.isConnected,
        isStreaming: chatStore.isStreaming
      })
    }
    console.log('🔧 调试工具已加载，使用 window.__chatDebug 访问')
    console.log('📋 可用命令:')
    console.log('  - __chatDebug.getState() - 获取当前状态')
    console.log('  - __chatDebug.sendTestMessage("消息") - 发送测试消息')
    console.log('  - __chatDebug.listMessages() - 查看所有消息')
    console.log('  - __chatDebug.clearMessages() - 清空消息')
    console.log('  - __chatDebug.newSession() - 创建新会话')
    console.log('  - __chatDebug.getWSStatus() - 查看 WebSocket 状态')
  }
})

// 清理
onUnmounted(() => {
  // 断开 WebSocket
  if (currentWSService) {
    console.log('🔌 清理 WebSocket 连接...')
    try {
      currentWSService.disconnect()
    } catch (e) {
      console.warn('断开 WebSocket 失败:', e)
    }
    currentWSService = null
  }
  
  // 清理全局 WebSocket 服务（如果存在）
  websocketService.disconnect()
  
  // 断开当前会话的 WebSocket
  if (currentWSService) {
    currentWSService.disconnect()
    currentWSService = null
  }
})
</script>

<style scoped>
.home-container {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

/* 主内容区域 */
.home-main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #fff;
}

/* 顶部工具栏样式 */
.toolbar {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  width: 100%;
  box-sizing: border-box;
  flex-shrink: 0;
}

/* 工具栏内容居中容器，与下方内容对齐 */
.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lang-button {
  padding: 0 10px;
  height: 36px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.lang-icon {
  font-size: 16px;
}

.lang-label {
  font-size: 13px;
  font-weight: 500;
  color: #666;
}

.toolbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-button {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  background-color: #ffffff;
  color: #666;
  font-size: 14px;
  border-radius: 4px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.config-button:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.config-button .el-icon {
  font-size: 16px;
}

/* 欢迎页面样式 */
.welcome-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 40px 20px;
  color: #666;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.welcome-header h1 {
  font-size: 36px;
  font-weight: 700;
  color: #1890ff;
  margin-bottom: 10px;
}

.welcome-header p {
  font-size: 18px;
  color: #444;
  margin-bottom: 40px;
}


/* 消息流区域样式 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #f9f9f9;
  width: 100%;
  display: flex;
  justify-content: center;
}

.messages-list {
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.message {
  display: flex;
  margin-bottom: 24px;
}

.user-message {
  flex-direction: row-reverse;
}

.ai-message {
  flex-direction: row;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-left: 12px;
  flex-shrink: 0;
}

.user-avatar {
  background-color: #6C5CE7;  /* 使用截图中的紫色 */
  color: white;
}

.ai-avatar {
  background-color: #f0f0f0;
  color: #333;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 56px);
  min-width: 0; /* 允许内容收缩 */
}

.user-message .message-content {
  flex: 0 1 auto; /* 不拉伸，根据内容自适应 */
  max-width: 70%; /* 最大宽度70% */
  min-width: 100px; /* 最小宽度 */
}

.user-content {
  background-color: #6C5CE7;  /* 使用截图中的紫色 */
  color: #fff;  /* 白色文字 */
  padding: 16px;
  border-radius: 16px 0 16px 16px;  /* 右上角是尖角 */
  box-shadow: 0 2px 8px rgba(108, 92, 231, 0.2);
}

.ai-content {
  background-color: white;
  color: #333;
  padding: 16px;
  border-radius: 16px 16px 0 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.message-content p {
  font-size: 15px;
  line-height: 1.6;
  margin: 0;
}

.message-content p:not(:last-child) {
  margin-bottom: 12px;
}

.message-content p {
  word-wrap: break-word;
  white-space: pre-wrap;
}

/* 图表容器 */
.chart-container {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.view-toggle {
  margin-bottom: 12px;
  display: flex;
  justify-content: center;
}

.table-view {
  margin-top: 16px;
}

/* 对比视图布局 */
.message-content .chart-container > div:not(.view-toggle) {
  margin-bottom: 16px;
}

.message-content .chart-container .table-view {
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
}

/* 数据表格容器 */
.table-container {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* 消息操作按钮 */
.message-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  background-color: #f0f0f0;
  color: #333;
  border: none;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background-color: #e0e0e0;
}

/* 加载指示器 */
.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.loading-dots {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background-color: #1890ff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

/* 底部输入控制区样式 */
.input-container {
  padding: 16px 20px;
  border-top: 1px solid #eee;
  background-color: #fff;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  flex-shrink: 0;
}

/* 第一行：控制项在一行 */
.input-controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: nowrap;
  width: 100%;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  overflow: hidden;
}

.data-source-selector,
.data-table-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}

.source-select {
  width: 160px;
  min-width: 100px;
  flex-shrink: 1;
}

.table-select {
  width: 200px;
  min-width: 120px;
  flex-shrink: 1;
}

.preview-btn {
  flex-shrink: 0;
}

.mode-toggle {
  display: flex;
  align-items: center;
  margin-left: auto;
  gap: 8px;
  flex-shrink: 0;
  white-space: nowrap;
}

/* 第二行：输入框和发送按钮 */
.input-message-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
}

.message-input {
  flex: 1;
}

.message-input :deep(.el-input__wrapper) {
  border-radius: 24px;
  border: 1px solid #ddd;
  padding: 10px 20px;
  height: 48px;
  box-shadow: none;
}

.message-input :deep(.el-input__inner) {
  font-size: 15px;
  line-height: 28px;
  height: 28px;
}

.message-input :deep(.el-input__wrapper):hover {
  border-color: #1890ff;
}

.message-input :deep(.el-input__wrapper.is-focus) {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

/* Custom SVG buttons styles */
.custom-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: #1890ff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
  color: white;
}

.custom-btn svg {
  color: white;
}

.attachment-btn:hover {
  background-color: #096dd9;
  transform: scale(1.05);
}

.send-btn:hover {
  background-color: #096dd9;
  transform: scale(1.05);
}

.send-btn:disabled {
  background-color: #f0f0f0;
  color: #999;
  cursor: not-allowed;
  transform: none;
}



/* 响应式设计 */
@media (max-width: 768px) {
  .home-container {
    padding: 10px;
  }
  
  .toolbar {
    padding: 0 10px;
    gap: 16px;
  }
  
  .welcome-section {
    padding: 20px;
  }
  
  .welcome-header h1 {
    font-size: 28px;
  }
  
  .welcome-header p {
    font-size: 16px;
  }
  
  .question-list {
    gap: 8px;
  }
  
  .question-btn {
    padding: 8px 12px;
    font-size: 12px;
  }
  
  .input-row {
    flex-direction: column;
    align-items: flex-start;
    padding: 0 10px;
  }
  
  .data-source-selector {
    margin-right: 0;
    margin-bottom: 8px;
    width: 100%;
  }
  
  .source-select {
    width: 100%;
  }
  
  .preview-btn {
    margin-right: 0;
    margin-bottom: 8px;
    width: 100%;
  }
  
  .mode-toggle {
    margin-left: 0;
    margin-bottom: 8px;
    width: 100%;
  }
  
  .message-input {
    padding: 10px 14px;
    font-size: 14px;
    width: 100%;
  }
  
  .photo-btn, .attachment-btn, .send-btn {
    margin-left: 0;
    margin-top: 8px;
  }
}
</style>

/* 思考状态样式 */
.thinking-message {
  color: #999;
  font-style: italic;
}

.thinking-text {
  margin: 0 0 8px 0;
  color: #999;
}

.thinking-indicator {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.thinking-indicator .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #999;
  animation: thinking-pulse 1.4s infinite ease-in-out;
}

.thinking-indicator .dot:nth-child(1) {
  animation-delay: 0s;
}

.thinking-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-pulse {
  0%, 60%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  30% {
    transform: scale(1.2);
    opacity: 1;
  }
}

/* 流式输出打字机效果 */
.streaming-text {
  display: inline;
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: #333;
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 49% {
    opacity: 1;
  }
  50%, 100% {
    opacity: 0;
  }
}

/* Markdown 表格样式 */
.markdown-table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 14px;
  background-color: white;
}

.markdown-table th,
.markdown-table td {
  border: 1px solid #ddd;
  padding: 8px 12px;
  text-align: left;
}

.markdown-table th {
  background-color: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.markdown-table tr:nth-child(even) {
  background-color: #fafafa;
}

.markdown-table tr:hover {
  background-color: #f0f0f0;
}

/* Markdown 代码块样式 */
pre {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  margin: 12px 0;
}

pre code {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  color: #333;
}

/* 行内代码样式 */
code {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  color: #e83e8c;
}

/* 引用样式 */
blockquote {
  border-left: 4px solid #1890ff;
  padding-left: 12px;
  margin: 12px 0;
  color: #666;
  font-style: italic;
}

/* 链接样式 */
a {
  color: #1890ff;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* 列表样式 */
ul {
  padding-left: 24px;
  margin: 8px 0;
}

li {
  margin: 4px 0;
}

/* 标题样式 */
h1, h2, h3 {
  margin: 16px 0 8px 0;
  font-weight: 600;
}

h1 {
  font-size: 24px;
  color: #333;
}

h2 {
  font-size: 20px;
  color: #333;
}

h3 {
  font-size: 16px;
  color: #333;
}

/* 分隔线样式 */
hr {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 16px 0;
}
