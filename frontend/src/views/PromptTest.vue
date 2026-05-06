<!-- Prompt 阶段测试页面 -->
<template>
  <div class="prompt-test-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>🧪 Prompt 阶段测试</h2>
          <p class="subtitle">逐步验证每个阶段的 Prompt 和语义上下文传递</p>
        </div>
      </template>
      
      <!-- 测试表单 -->
      <el-form :model="form" label-width="120px" class="test-form">
        <el-form-item label="测试阶段">
          <el-select v-model="form.stage" placeholder="选择测试阶段" style="width: 100%">
            <el-option label="🎯 意图识别" value="intent" />
            <el-option label="📊 智能选表" value="table_selection" />
            <el-option label="💾 SQL生成" value="sql_generation" />
            <el-option label="📈 数据分析" value="data_analysis" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="用户问题">
          <el-input
            v-model="form.user_question"
            type="textarea"
            :rows="3"
            placeholder="输入测试问题，如：查询订单总数"
          />
        </el-form-item>
        
        <el-form-item label="数据源ID" v-if="form.stage !== 'intent'">
          <el-input v-model="form.data_source_id" placeholder="可选，留空使用默认" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="testStage" :loading="loading" size="large">
            <el-icon><VideoPlay /></el-icon>
            <span style="margin-left: 8px">测试此阶段</span>
          </el-button>
          <el-button @click="clearResult" :disabled="!result" size="large">
            <el-icon><Delete /></el-icon>
            <span style="margin-left: 8px">清空结果</span>
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 测试结果 -->
    <el-card v-if="result" class="result-card">
      <template #header>
        <div class="card-header">
          <h3>📋 测试结果</h3>
          <el-tag :type="result.success ? 'success' : 'danger'" size="large">
            {{ result.success ? '✅ 测试成功' : '❌ 测试失败' }}
          </el-tag>
        </div>
      </template>
      
      <!-- 成功/失败状态 -->
      <el-alert
        v-if="!result.success"
        type="error"
        :title="'测试失败'"
        :description="result.error"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
      />
      
      <!-- 语义上下文信息 -->
      <div v-if="result.semantic_context" class="section">
        <h4>📊 语义上下文信息</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="使用的模块">
            <el-tag
              v-for="module in result.semantic_context.modules_used"
              :key="module"
              style="margin-right: 8px"
              type="success"
            >
              {{ module }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Token 使用量">
            <el-tag type="info">{{ result.semantic_context.total_tokens }} tokens</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="相关性评分" v-if="result.semantic_context.relevance_scores">
            <div class="relevance-scores">
              <el-tag
                v-for="(score, module) in result.semantic_context.relevance_scores"
                :key="module"
                :type="getScoreType(score)"
                style="margin-right: 8px; margin-bottom: 8px"
              >
                {{ module }}: {{ (score * 100).toFixed(0) }}%
              </el-tag>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="上下文预览">
            <pre class="context-preview">{{ result.semantic_context.context_preview }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <!-- 渲染的 Prompt -->
      <div class="section">
        <div class="section-header">
          <h4>📝 实际发送给 AI 的 Prompt</h4>
          <el-button @click="copyPrompt" size="small" type="primary" plain>
            <el-icon><DocumentCopy /></el-icon>
            <span style="margin-left: 4px">复制 Prompt</span>
          </el-button>
        </div>
        <el-input
          v-model="result.rendered_prompt"
          type="textarea"
          :rows="15"
          readonly
          class="prompt-textarea"
        />
      </div>
      
      <!-- AI 响应 -->
      <div v-if="result.ai_response" class="section">
        <h4>🤖 AI 响应</h4>
        <pre class="ai-response">{{ JSON.stringify(result.ai_response, null, 2) }}</pre>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Delete, DocumentCopy } from '@element-plus/icons-vue'
import axios from 'axios'

// 表单数据
const form = reactive({
  stage: 'intent',
  user_question: '查询订单总数',
  data_source_id: ''
})

// 加载状态
const loading = ref(false)

// 测试结果
const result = ref<any>(null)

/**
 * 测试阶段
 */
const testStage = async () => {
  loading.value = true
  result.value = null
  
  try {
    const response = await axios.post('/api/prompt-test/test-stage', {
      user_question: form.user_question,
      data_source_id: form.data_source_id || null,
      stage: form.stage
    })
    
    result.value = response.data
    
    if (response.data.success) {
      ElMessage.success('测试成功')
    } else {
      ElMessage.error('测试失败')
    }
  } catch (error: any) {
    ElMessage.error(`请求失败: ${error.message}`)
    result.value = {
      stage: form.stage,
      rendered_prompt: '',
      success: false,
      error: error.message
    }
  } finally {
    loading.value = false
  }
}

/**
 * 清空结果
 */
const clearResult = () => {
  result.value = null
}

/**
 * 复制 Prompt
 */
const copyPrompt = () => {
  if (result.value?.rendered_prompt) {
    navigator.clipboard.writeText(result.value.rendered_prompt)
    ElMessage.success('Prompt 已复制到剪贴板')
  }
}

/**
 * 获取评分类型（用于标签颜色）
 */
const getScoreType = (score: number): string => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'info'
}
</script>

<style scoped>
.prompt-test-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.subtitle {
  margin: 8px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.test-form {
  margin-top: 20px;
}

.result-card {
  margin-top: 20px;
}

.section {
  margin-top: 24px;
}

.section:first-child {
  margin-top: 0;
}

.section h4 {
  margin: 0 0 12px 0;
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h4 {
  margin: 0;
}

.context-preview {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
}

.prompt-textarea {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.prompt-textarea :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.ai-response {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.relevance-scores {
  display: flex;
  flex-wrap: wrap;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .prompt-test-page {
    padding: 10px;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
