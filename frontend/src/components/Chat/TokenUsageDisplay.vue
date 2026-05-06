<template>
  <div class="token-usage-display">
    <div class="header">
      <h3>Token 使用统计</h3>
    </div>
    
    <!-- 本地模型 Token 使用 -->
    <div class="model-section">
      <h4>本地模型</h4>
      <div class="usage-info">
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: localProgress + '%' }"></div>
        </div>
        <div class="usage-text">
          <span class="used">{{ localUsed }} / {{ localLimit }} tokens</span>
          <span class="percentage">{{ localProgress.toFixed(1) }}%</span>
        </div>
      </div>
      <div class="warning" v-if="localWarning">
        <el-icon><Warning /></el-icon>
        <span>接近本地模型限制，建议切换到云端模型</span>
      </div>
    </div>
    
    <!-- 阿里云模型 Token 使用 -->
    <div class="model-section">
      <h4>阿里云模型</h4>
      <div class="usage-info">
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: aliyunProgress + '%' }"></div>
        </div>
        <div class="usage-text">
          <span class="used">{{ aliyunUsed }} / {{ aliyunLimit }} tokens</span>
          <span class="percentage">{{ aliyunProgress.toFixed(1) }}%</span>
        </div>
      </div>
      <div class="warning" v-if="aliyunWarning">
        <el-icon><Warning /></el-icon>
        <span>接近阿里云模型限制，建议结束会话</span>
      </div>
    </div>
    
    <!-- 总体统计 -->
    <div class="total-section">
      <h4>总体统计</h4>
      <div class="total-info">
        <div class="stat-item">
          <span class="label">总轮次：</span>
          <span class="value">{{ totalTurns }}</span>
        </div>
        <div class="stat-item">
          <span class="label">总输入Token：</span>
          <span class="value">{{ totalInput }}</span>
        </div>
        <div class="stat-item">
          <span class="label">总输出Token：</span>
          <span class="value">{{ totalOutput }}</span>
        </div>
        <div class="stat-item">
          <span class="label">总计Token：</span>
          <span class="value">{{ totalTokens }}</span>
        </div>
      </div>
    </div>
    
    <!-- 模型使用详情 -->
    <div class="model-details">
      <h4>模型使用详情</h4>
      <div class="model-list">
        <div 
          v-for="(model, modelName) in modelUsage" 
          :key="modelName"
          class="model-item"
        >
          <span class="model-name">{{ getModelName(modelName) }}</span>
          <span class="model-stats">
            输入：{{ model.input }} | 输出：{{ model.output }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/store/modules/chat'
import { Warning } from '@element-plus/icons-vue'

const chatStore = useChatStore()

// 获取Token使用统计
const tokenStats = computed(() => chatStore.getTokenUsageStats())

// 计算本地模型使用情况
const localUsed = computed(() => chatStore.sessionContext.local_model.tokenCount)
const localLimit = 15000
const localProgress = computed(() => Math.min((localUsed.value / localLimit) * 100, 100))
const localWarning = computed(() => localUsed.value > localLimit * 0.8)

// 计算阿里云模型使用情况
const aliyunUsed = computed(() => chatStore.sessionContext.aliyun_model.tokenCount)
const aliyunLimit = 800000
const aliyunProgress = computed(() => Math.min((aliyunUsed.value / aliyunLimit) * 100, 100))
const aliyunWarning = computed(() => aliyunUsed.value > aliyunLimit * 0.8)

// 总体统计
const totalTurns = computed(() => tokenStats.value.totalTurns)
const totalInput = computed(() => tokenStats.value.totalInputTokens)
const totalOutput = computed(() => tokenStats.value.totalOutputTokens)
const totalTokens = computed(() => tokenStats.value.totalTokens)

// 模型使用详情
const modelUsage = computed(() => tokenStats.value.modelUsage)

// 获取模型名称显示
const getModelName = (modelName: string): string => {
  if (modelName.includes('local')) return '本地模型'
  if (modelName.includes('aliyun')) return '阿里云模型'
  if (modelName.includes('qwen')) return 'Qwen模型'
  return modelName
}
</script>

<style scoped>
.token-usage-display {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
}

.header {
  margin-bottom: 16px;
}

.header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.model-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.model-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.usage-info {
  margin-bottom: 12px;
}

.progress-container {
  width: 100%;
  height: 8px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background-color: #1890ff;
  transition: width 0.3s ease;
}

.usage-text {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #333;
}

.used {
  font-weight: 600;
}

.percentage {
  color: #666;
}

.warning {
  display: flex;
  align-items: center;
  color: #faad14;
  font-size: 13px;
}

.warning el-icon {
  margin-right: 4px;
}

.total-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.total-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.total-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.label {
  font-size: 12px;
  color: #666;
}

.value {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.model-details {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.model-details h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}

.model-name {
  font-weight: 600;
  color: #333;
}

.model-stats {
  color: #666;
}
</style>
