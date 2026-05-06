<template>
  <div class="intelligent-tools-section">
    <!-- 智能工具配置 -->
    <div class="tool-group">
      <h3 class="group-title">智能工具</h3>
      
      <div class="tool-item">
        <label class="tool-label">数据解读</label>
        <el-switch
          v-model="config.enableDataInterpretation"
          class="tool-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updateToolConfig('enableDataInterpretation', $event)"
        />
        <span class="tool-description">开启后，查询结果将包含数据摘要和洞察</span>
      </div>
      
      <div class="tool-item">
        <label class="tool-label">智能建议</label>
        <el-switch
          v-model="config.enableSmartSuggestions"
          class="tool-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updateToolConfig('enableSmartSuggestions', $event)"
        />
        <span class="tool-description">根据查询内容自动推荐相关分析维度</span>
      </div>
      
      <div class="tool-item">
        <label class="tool-label">异常检测</label>
        <el-switch
          v-model="config.enableAnomalyDetection"
          class="tool-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updateToolConfig('enableAnomalyDetection', $event)"
        />
        <span class="tool-description">自动识别数据中的异常值和趋势变化</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConfigStore } from '@/store/modules/config'

// 定义智能工具配置类型
interface IntelligentToolConfig {
  enableDataInterpretation: boolean
  enableSmartSuggestions: boolean
  enableAnomalyDetection: boolean
}

// 获取配置 store
const configStore = useConfigStore()

// 响应式配置状态（从 store 同步）
const config = computed(() => {
  return {
    enableDataInterpretation: configStore.intelligentTools.enableDataInterpretation,
    enableSmartSuggestions: configStore.intelligentTools.enableSmartSuggestions,
    enableAnomalyDetection: configStore.intelligentTools.enableAnomalyDetection
  }
})

// 更新工具配置并同步到 store
const updateToolConfig = (key: keyof IntelligentToolConfig, value: boolean) => {
  configStore.updateIntelligentToolConfig(key, value)
}

// 初始化配置（从 store 加载）
const initConfig = () => {
  // Store 会在初始化时自动加载持久化配置
}

// 在组件挂载时初始化
initConfig()
</script>

<style scoped>
.intelligent-tools-section {
  padding: 20px;
}

.tool-group {
  margin-bottom: 30px;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e0;
}

.tool-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}

.tool-label {
  flex: 1;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.tool-switch {
  margin: 0 10px;
}

.tool-description {
  flex: 2;
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}
</style>