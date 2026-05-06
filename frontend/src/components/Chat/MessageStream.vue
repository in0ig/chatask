<template>
  <div class="message-stream">
    <!-- 欢迎语和推荐问题（仅在无消息时显示） -->
    <div v-if="messages.length === 0" class="welcome-container">
      <div class="welcome-message">
        欢迎使用 Ask Jarvis！我是您的智能数据分析助手，可以通过自然语言查询数据。
      </div>
      
      <div class="recommended-questions">
        <span class="label">推荐问题：</span>
        <div class="chips">
          <button 
            v-for="(question, index) in recommendedQuestions" 
            :key="index"
            class="chip"
            @click="selectRecommendedQuestion(question)"
          >
            {{ question }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 消息列表 -->
    <div class="messages-container">
      <div 
        v-for="message in messages" 
        :key="message.id"
        :class="['message', message.role === 'user' ? 'message-user' : 'message-assistant']"
      >
        <!-- 用户消息 -->
        <div v-if="message.role === 'user'" class="user-message">
          <div class="message-content">
            {{ message.content }}
          </div>
        </div>
        
        <!-- AI 消息 -->
        <AIMessage
          v-else
          :thinking-steps="convertStagesToThinkingSteps(message.stages || [])"
          :thinking-time="message.thinkingTime"
          :thinking-collapsed="message.thinkingCollapsed"
          :text-content="getResultDescription(message.stages || [])"
          :chart-data="message.chartData || getChartData(message.stages || [])"
          :chart-type="message.chartType"
          :timestamp="message.timestamp"
        />
      </div>
    </div>
    
    <!-- 清空会话按钮 -->
    <div class="clear-session-container" v-if="messages.length > 0">
      <button class="clear-session-btn" @click="clearMessages">清空会话</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useChatStore } from '@/store/modules/chat'
import AIMessage from './AIMessage.vue'

const chatStore = useChatStore()

// Emits
const emit = defineEmits<{
  (e: 'select-question', question: string): void
}>()

// 从 store 获取数据
const messages = computed(() => chatStore.currentMessages)
const recommendedQuestions = ref([
  '最近一个月的销售额是多少？',
  '各地区的订单量对比',
  '哪些产品的利润率最高？'
])

// 方法绑定
const selectRecommendedQuestion = (question: string) => {
  // 触发父组件处理推荐问题
  emit('select-question', question)
}

const clearMessages = () => {
  chatStore.clearCurrentSession()
}

// 将 stages 转换为 thinkingSteps 格式
const convertStagesToThinkingSteps = (stages: any[]) => {
  if (!stages || stages.length === 0) return []
  
  // 过滤掉"数据结果描述"stage，只保留思考过程相关的 stages
  const thinkingStageNames = [
    '意图识别',
    '智能选表', 
    '意图澄清',
    '模型思考',
    'SQL生成',
    'SQL执行'
  ]
  
  return stages
    .filter(stage => thinkingStageNames.includes(stage.name))
    .map(stage => ({
      title: stage.name,
      type: stage.name === 'SQL生成' ? 'sql' : 'text',
      content: stage.content,
      status: stage.status === 'completed' ? 'completed' : 
              stage.status === 'error' ? 'error' :
              stage.status === 'in_progress' ? 'running' : 'pending'
    }))
}

// 从 stages 中提取数据结果描述
const getResultDescription = (stages: any[]) => {
  if (!stages || stages.length === 0) return ''
  
  // 🔧 修复：后端实际使用的 stage 名称是 '数据分析'，不是 '数据结果描述'
  const descStage = stages.find(stage => stage.id === 'data_analysis' || stage.name === '数据分析')
  return descStage?.content || ''
}

// 从 stages 中提取图表数据
const getChartData = (stages: any[]) => {
  if (!stages || stages.length === 0) return null
  
  // 查找包含图表配置的 stage
  const chartStage = stages.find(stage => 
    stage.metadata?.chart_config || stage.metadata?.chartData
  )
  
  if (!chartStage) {
    console.log('⚠️ [getChartData] 未找到 chartStage')
    return null
  }
  
  console.log('🔍 [getChartData] 找到 chartStage:', {
    hasChartData: !!chartStage.metadata?.chartData,
    hasChartConfig: !!chartStage.metadata?.chart_config,
    chartData: chartStage.metadata?.chartData,
    chartConfig: chartStage.metadata?.chart_config
  })
  
  // 优先使用 chartData（原始数据格式）
  if (chartStage.metadata?.chartData) {
    console.log('✅ [getChartData] 返回 chartData:', chartStage.metadata.chartData)
    return chartStage.metadata.chartData
  }
  
  // 降级：尝试从 chart_config 中提取（但这不是正确的格式）
  if (chartStage.metadata?.chart_config?.chartConfig) {
    console.warn('⚠️ [getChartData] 使用 chart_config.chartConfig（可能格式不正确）')
    return chartStage.metadata.chart_config.chartConfig
  }
  
  console.warn('⚠️ [getChartData] 没有可用的图表数据')
  return null
}
</script>

<style scoped>
.message-stream {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-y: auto;
  background-color: #f5f5f5;
}

.welcome-container {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.welcome-message {
  font-size: 16px;
  margin-bottom: 20px;
  line-height: 1.6;
}

.recommended-questions {
  margin-top: 20px;
}

.recommended-questions .label {
  display: block;
  margin-bottom: 10px;
  color: #888;
  font-size: 14px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.chip {
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #1890ff;
  border-radius: 20px;
  padding: 6px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.chip:hover {
  background-color: #91d5ff;
  color: white;
}

.messages-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.message {
  display: flex;
  max-width: 100%;
}

.user-message {
  margin-left: auto;
  max-width: 80%;
}

.message-content {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
  background-color: #e6f7ff;
  color: #1890ff;
}

.clear-session-container {
  text-align: center;
  padding: 10px 0;
}

.clear-session-btn {
  background-color: transparent;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  padding: 6px 16px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-session-btn:hover {
  background-color: #f5f5f5;
}
</style>