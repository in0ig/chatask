<template>
  <div class="sql-builder-demo">
    <div class="demo-header">
      <h2>SQL 建表功能演示</h2>
      <p>这是 SQL 建表组件的演示页面，用于测试和验证功能。</p>
    </div>
    
    <div class="demo-content">
      <SqlBuilder 
        :visible="true"
        @success="onTableCreated"
        @close="onClose"
      />
    </div>
    
    <!-- 结果显示 -->
    <div v-if="createdTable" class="demo-result">
      <h3>创建成功的表</h3>
      <pre>{{ JSON.stringify(createdTable, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SqlBuilder from '@/components/DataPreparation/SqlBuilder.vue'

// 响应式数据
const createdTable = ref(null)

// 事件处理
const onTableCreated = (table: any) => {
  console.log('表创建成功:', table)
  createdTable.value = table
}

const onClose = () => {
  console.log('关闭 SQL 建表组件')
}
</script>

<style scoped lang="scss">
.sql-builder-demo {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;

  .demo-header {
    margin-bottom: 20px;
    text-align: center;

    h2 {
      color: #303133;
      margin-bottom: 8px;
    }

    p {
      color: #606266;
      font-size: 14px;
    }
  }

  .demo-content {
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    overflow: hidden;
    height: 800px;
  }

  .demo-result {
    margin-top: 20px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;

    h3 {
      margin: 0 0 12px 0;
      color: #303133;
    }

    pre {
      background: #fff;
      padding: 12px;
      border-radius: 4px;
      border: 1px solid #e4e7ed;
      font-size: 12px;
      color: #606266;
      overflow-x: auto;
    }
  }
}
</style>