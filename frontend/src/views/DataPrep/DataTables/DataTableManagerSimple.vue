<template>
  <div class="data-table-manager-simple">
    <h1>数据表管理 - 简化版本</h1>
    <p>这是一个简化的数据表管理组件，用于测试路由是否正常工作。</p>
    
    <div class="test-info">
      <h3>组件状态：</h3>
      <ul>
        <li>组件已成功加载 ✅</li>
        <li>当前路由：{{ $route.path }}</li>
        <li>路由参数：{{ JSON.stringify($route.params) }}</li>
        <li>查询参数：{{ JSON.stringify($route.query) }}</li>
      </ul>
    </div>

    <div class="actions">
      <button @click="goBack">返回上一页</button>
      <button @click="goToDataSources">前往数据源</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  router.back()
}

const goToDataSources = () => {
  router.push('/data-prep/sources')
}

// 组件加载时输出调试信息
console.log('DataTableManagerSimple 组件已加载')
console.log('当前路由信息:', {
  path: router.currentRoute.value.path,
  name: router.currentRoute.value.name,
  params: router.currentRoute.value.params,
  query: router.currentRoute.value.query
})
</script>

<style scoped>
.data-table-manager-simple {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 5px;
  margin: 20px 0;
}

.test-info ul {
  margin: 10px 0;
  padding-left: 20px;
}

.test-info li {
  margin: 5px 0;
}

.actions {
  margin-top: 20px;
}

.actions button {
  margin-right: 10px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.actions button:hover {
  background: #0056b3;
}

h1 {
  color: #333;
  border-bottom: 2px solid #007bff;
  padding-bottom: 10px;
}

p {
  color: #666;
  line-height: 1.6;
}
</style>