<template>
  <div class="demo-container">
    <h2>Token 使用统计组件演示</h2>
    
    <div class="demo-section">
      <h3>本地模型 - 正常使用情况 (25%)</h3>
      <TokenUsageStats 
        :currentUsage="8000" 
        :totalLimit="32000" 
        modelType="local" 
      />
    </div>
    
    <div class="demo-section">
      <h3>本地模型 - 高使用情况 (85%)</h3>
      <TokenUsageStats 
        :currentUsage="27200" 
        :totalLimit="32000" 
        modelType="local" 
      />
    </div>
    
    <div class="demo-section">
      <h3>阿里云模型 - 接近耗尽 (96%)</h3>
      <TokenUsageStats 
        :currentUsage="960000" 
        :totalLimit="1000000" 
        modelType="aliyun" 
      />
    </div>
    
    <div class="demo-section">
      <h3>默认值测试</h3>
      <TokenUsageStats />
    </div>
  </div>
</template>

<script setup lang="ts">
import TokenUsageStats from '@/components/Config/TokenUsageStats.vue';
</script>

<style scoped>
.demo-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.demo-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #fafafa;
}

h2 {
  color: #303133;
  text-align: center;
  margin-bottom: 30px;
}

h3 {
  color: #606266;
  margin-bottom: 15px;
}
</style>