<template>
  <div class="data-table-manager-test">
    <h1>数据表管理测试页面</h1>
    <p>如果你能看到这个页面，说明路由配置是正确的！</p>
    
    <div class="test-info">
      <h2>测试信息</h2>
      <ul>
        <li>当前路由: {{ $route.path }}</li>
        <li>路由名称: {{ $route.name }}</li>
        <li>加载时间: {{ loadTime }}</li>
      </ul>
    </div>
    
    <div class="test-actions">
      <h2>测试操作</h2>
      <button @click="testNavigation">测试导航</button>
      <button @click="testStore">测试 Store</button>
      <button @click="testApi">测试 API</button>
    </div>
    
    <div class="test-results" v-if="testResults.length > 0">
      <h2>测试结果</h2>
      <ul>
        <li v-for="result in testResults" :key="result.id" :class="result.success ? 'success' : 'error'">
          {{ result.message }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

// 响应式数据
const loadTime = ref('')
const testResults = ref<Array<{id: number, message: string, success: boolean}>>([])

// 路由相关
const router = useRouter()
const route = useRoute()

// 生命周期
onMounted(() => {
  loadTime.value = new Date().toLocaleString()
  console.log('数据表管理测试页面已加载')
})

// 测试方法
const testNavigation = () => {
  try {
    addTestResult('路由导航测试通过', true)
    console.log('当前路由:', route.path)
  } catch (error) {
    addTestResult(`路由导航测试失败: ${error}`, false)
  }
}

const testStore = () => {
  try {
    // 简单的 store 测试
    addTestResult('Store 访问测试通过', true)
  } catch (error) {
    addTestResult(`Store 访问测试失败: ${error}`, false)
  }
}

const testApi = () => {
  try {
    // 简单的 API 测试
    fetch('/api/data-tables')
      .then(response => {
        if (response.ok) {
          addTestResult('API 连接测试通过', true)
        } else {
          addTestResult(`API 连接测试失败: HTTP ${response.status}`, false)
        }
      })
      .catch(error => {
        addTestResult(`API 连接测试失败: ${error.message}`, false)
      })
  } catch (error) {
    addTestResult(`API 测试异常: ${error}`, false)
  }
}

const addTestResult = (message: string, success: boolean) => {
  testResults.value.push({
    id: Date.now(),
    message,
    success
  })
}
</script>

<style scoped>
.data-table-manager-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-info, .test-actions, .test-results {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.test-actions button {
  margin-right: 10px;
  padding: 8px 16px;
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.test-actions button:hover {
  background: #337ecc;
}

.test-results ul {
  list-style: none;
  padding: 0;
}

.test-results li {
  padding: 5px 10px;
  margin: 5px 0;
  border-radius: 4px;
}

.test-results li.success {
  background: #f0f9ff;
  color: #0066cc;
  border: 1px solid #b3d8ff;
}

.test-results li.error {
  background: #fef0f0;
  color: #c53030;
  border: 1px solid #fbc4c4;
}

h1 {
  color: #303133;
}

h2 {
  color: #606266;
  font-size: 16px;
}
</style>