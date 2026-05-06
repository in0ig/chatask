<template>
  <div class="data-source-list">
    <!-- 标题和新增按钮 -->
    <div class="header">
      <h2>数据源列表</h2>
      <el-button 
        type="primary" 
        @click="handleAddDataSource"
      >
        新增数据源
      </el-button>
    </div>

    <!-- 搜索框 -->
    <div class="filter-section">
      <el-input
        v-model="searchKeyword"
        placeholder="按名称搜索..."
        clearable
      />
    </div>

    <!-- 加载状态 -->
    <div class="loading-state" v-if="dataSourceLoading">
      <p>加载中...</p>
    </div>

    <!-- 空数据状态 -->
    <div class="empty-state" v-if="!dataSourceLoading && filteredDataSources.length === 0">
      <p>暂无数据源</p>
    </div>

    <!-- 数据源表格 -->
    <div class="table-container" v-if="!dataSourceLoading && filteredDataSources.length > 0">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>类型</th>
            <th>连接状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in filteredDataSources" :key="source.id">
            <td>{{ source.id }}</td>
            <td>{{ source.name }}</td>
            <td>
              <span class="type-tag" :class="`type-${source.type}`">
                {{ getTypeLabel(source.type) }}
              </span>
            </td>
            <td>
              <span class="status-tag" :class="source.is_active ? 'status-active' : 'status-inactive'">
                {{ getStatusLabel(source.is_active) }}
              </span>
            </td>
            <td>{{ formatDate(source.created_at) }}</td>
            <td>
              <button class="btn btn-primary" @click="handleEditDataSource(source)">编辑</button>
              <button class="btn btn-success" @click="handleCopyDataSource(source)">复制</button>
              <button class="btn btn-danger" @click="handleDeleteDataSource(source)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataSource } from '@/api/dataSourceApi'

// Store 实例
const dataPrepStore = useDataPreparationStore()

// 搜索关键词
const searchKeyword = ref('')

// 加载状态
const dataSourceLoading = computed(() => dataPrepStore.dataSourceLoading)

// 数据源列表
const dataSources = computed(() => dataPrepStore.dataSources)

// 过滤后的数据源列表
const filteredDataSources = computed(() => {
  if (!searchKeyword.value) {
    return dataSources.value
  }
  return dataSources.value.filter(source => 
    source.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

// 获取类型标签文本
const getTypeLabel = (type: string) => {
  const typeMap: Record<string, string> = {
    'mysql': 'MySQL',
    'excel': 'Excel',
    'api': 'API'
  }
  return typeMap[type] || type
}

// 获取状态标签文本
const getStatusLabel = (isActive: boolean) => {
  return isActive ? '已激活' : '未激活'
}

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 新增数据源
const handleAddDataSource = () => {
  ElMessage.info('新增数据源功能待实现')
}

// 编辑数据源
const handleEditDataSource = (dataSource: DataSource) => {
  ElMessage.info(`编辑数据源：${dataSource.name}`)
}

// 复制数据源
const handleCopyDataSource = (dataSource: DataSource) => {
  ElMessage.info(`复制数据源：${dataSource.name}`)
}

// 删除数据源
const handleDeleteDataSource = (dataSource: DataSource) => {
  ElMessageBox.confirm(
    `确定要删除数据源 "${dataSource.name}" 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success(`已删除数据源：${dataSource.name}`)
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 加载数据源列表
const loadDataSources = async () => {
  try {
    await dataPrepStore.fetchDataSources()
  } catch (error) {
    ElMessage.error('加载数据源列表失败')
  }
}

// 组件挂载时加载数据
loadDataSources()
</script>

<style scoped>
.data-source-list {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.filter-section {
  margin-bottom: 20px;
}

.loading-state,
.empty-state {
  padding: 40px;
  text-align: center;
  color: #909399;
}

.table-container {
  flex: 1;
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #e4e7ed;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e4e7ed;
}

.data-table th {
  background-color: #f5f7fa;
  font-weight: 600;
}

.type-tag,
.status-tag {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.type-mysql {
  background-color: #e6f7ff;
  color: #1890ff;
}

.type-excel {
  background-color: #fff7e6;
  color: #fa8c16;
}

.type-api {
  background-color: #f6ffed;
  color: #52c41a;
}

.status-active {
  background-color: #f6ffed;
  color: #52c41a;
}

.status-inactive {
  background-color: #fff2f0;
  color: #ff4d4f;
}

.btn {
  padding: 4px 8px;
  margin-right: 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.btn-primary {
  background-color: #409eff;
  color: white;
}

.btn-success {
  background-color: #67c23a;
  color: white;
}

.btn-danger {
  background-color: #f56c6c;
  color: white;
}

.btn:hover {
  opacity: 0.8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .filter-section {
    margin-bottom: 15px;
  }
}
</style>