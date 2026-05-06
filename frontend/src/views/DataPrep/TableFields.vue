<template>
  <div class="table-fields-container">
    <div class="page-header">
      <h1>字段配置</h1>
      <p>配置数据表字段的语义信息</p>
    </div>
    
    <div class="fields-content">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>表名: {{ tableId }}</span>
            <el-button type="primary" @click="saveFields">保存配置</el-button>
          </div>
        </template>
        
        <el-table :data="fields" style="width: 100%">
          <el-table-column prop="name" label="字段名" width="150" />
          <el-table-column prop="type" label="数据类型" width="120" />
          <el-table-column prop="alias" label="别名" width="150">
            <template #default="scope">
              <el-input v-model="scope.row.alias" placeholder="输入别名" />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述">
            <template #default="scope">
              <el-input v-model="scope.row.description" placeholder="输入描述" />
            </template>
          </el-table-column>
          <el-table-column prop="isVisible" label="可见" width="80">
            <template #default="scope">
              <el-switch v-model="scope.row.isVisible" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const tableId = ref(route.params.tableId || '')

// 模拟字段数据
const fields = ref([
  { name: 'id', type: 'INT', alias: '编号', description: '主键', isVisible: true },
  { name: 'name', type: 'VARCHAR', alias: '名称', description: '产品名称', isVisible: true },
  { name: 'price', type: 'DECIMAL', alias: '价格', description: '产品价格', isVisible: true },
  { name: 'created_at', type: 'DATETIME', alias: '创建时间', description: '记录创建时间', isVisible: false }
])

const saveFields = () => {
  console.log('保存字段配置:', fields.value)
  // TODO: 调用 API 保存配置
}

onMounted(() => {
  console.log('加载表字段配置, tableId:', tableId.value)
})
</script>

<style scoped>
.table-fields-container {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  color: #333;
  margin-bottom: 8px;
}

.page-header p {
  color: #666;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fields-content {
  background: #fff;
  border-radius: 8px;
}
</style>
