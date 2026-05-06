<template>
  <div class="data-source-list">
    <!-- 使用 ChatBI 数据源管理组件 -->
    <DataSourceManager />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import DataSourceManager from '@/views/DataSource/DataSourceManager.vue'

// 组件挂载时的初始化逻辑
onMounted(() => {
  console.log('数据准备 - 数据源页面已加载，使用 ChatBI 数据源管理组件')
})
</script>

<style scoped lang="scss">
.data-source-list {
  height: 100%;
  
  // 确保 ChatBI 数据源管理组件占满容器
  :deep(.data-source-manager) {
    height: 100%;
  }
}
</style>