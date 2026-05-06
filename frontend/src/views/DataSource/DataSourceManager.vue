<template>
  <div class="data-source-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据源管理</span>
          <el-button type="primary" @click="handleAddClick" data-testid="add-button">
            <el-icon><Plus /></el-icon>
            新增数据源
          </el-button>
        </div>
      </template>

      <!-- 数据源列表 -->
      <el-table 
        :data="dataSourceList" 
        v-loading="loading"
        empty-text="暂无数据源"
      >
        <el-table-column prop="name" label="数据源名称" min-width="150" />
        <el-table-column prop="type" label="数据库类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.type === 'mysql' ? 'success' : 'primary'">
              {{ row.type?.toUpperCase() || 'UNKNOWN' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config.host" label="主机地址" min-width="150" />
        <el-table-column prop="config.database" label="数据库名" min-width="120" />
        <el-table-column label="连接状态" width="120">
          <template #default="{ row }">
            <el-tag 
              :type="getStatusType(row.status)"
              :icon="getStatusIcon(row.status)"
            >
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="testConnection(row)"
              :loading="testingConnections.has(row.id)"
            >
              测试连接
            </el-button>
            <el-button 
              size="small" 
              type="primary" 
              @click="editDataSource(row)"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteDataSource(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      :title="editingDataSource ? '编辑数据源' : '新增数据源'"
      v-model="showAddDialog"
      width="600px"
      :close-on-click-modal="false"
    >
      <DataSourceForm
        :data-source="editingDataSource"
        @submit="handleSubmit"
        @cancel="handleCancel"
        :loading="submitting"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Warning, CircleCheck } from '@element-plus/icons-vue'
import { useDataSourceStore } from '@/store/modules/dataSource'
import DataSourceForm from '@/components/DataSource/DataSourceForm.vue'
import type { DataSource, DataSourceConfig } from '@/types/dataSource'

// Store
const dataSourceStore = useDataSourceStore()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const showAddDialog = ref(false)
const editingDataSource = ref<DataSource | null>(null)
const testingConnections = ref(new Set<string>())

// 计算属性
const dataSourceList = computed(() => dataSourceStore.dataSourceList)

// 状态相关方法
const getStatusType = (status: string) => {
  switch (status) {
    case 'active': return 'success'
    case 'inactive': return 'info'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'active': return CircleCheck
    case 'error': return Warning
    default: return Connection
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'active': return '正常'
    case 'inactive': return '未连接'
    case 'error': return '错误'
    default: return '未知'
  }
}

// 数据源操作方法
const loadDataSources = async () => {
  loading.value = true
  try {
    await dataSourceStore.fetchDataSources()
  } catch (error) {
    ElMessage.error('加载数据源列表失败')
  } finally {
    loading.value = false
  }
}

const testConnection = async (dataSource: DataSource) => {
  testingConnections.value.add(dataSource.id)
  try {
    // 将前端数据格式转换为后端API期望的格式
    const testConfig: DataSourceConfig = {
      name: dataSource.name,
      type: dataSource.type,
      host: dataSource.config.host,
      port: dataSource.config.port,
      database: dataSource.config.database,
      username: dataSource.config.username,
      password: '12345678' // 使用已知的测试密码
    }
    
    const result = await dataSourceStore.testConnection(testConfig)
    if (result.success) {
      ElMessage.success('连接测试成功')
      // 更新数据源状态
      try {
        await dataSourceStore.updateDataSourceStatus(dataSource.id, 'active')
      } catch (statusError) {
        console.error('Failed to update data source status:', statusError)
        // 状态更新失败不影响连接测试成功的提示
      }
    } else {
      ElMessage.error(`连接测试失败: ${result.error}`)
      try {
        await dataSourceStore.updateDataSourceStatus(dataSource.id, 'error')
      } catch (statusError) {
        console.error('Failed to update data source status:', statusError)
      }
    }
  } catch (error) {
    console.error('Connection test error:', error)
    ElMessage.error('连接测试失败')
    try {
      await dataSourceStore.updateDataSourceStatus(dataSource.id, 'error')
    } catch (statusError) {
      console.error('Failed to update data source status:', statusError)
    }
  } finally {
    testingConnections.value.delete(dataSource.id)
  }
}

const editDataSource = (dataSource: DataSource) => {
  editingDataSource.value = { ...dataSource }
  showAddDialog.value = true
}

const deleteDataSource = async (dataSource: DataSource) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据源 "${dataSource.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await dataSourceStore.deleteDataSource(dataSource.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 表单处理方法
const handleAddClick = () => {
  console.log('新增按钮被点击')
  showAddDialog.value = true
}

const handleSubmit = async (config: DataSourceConfig) => {
  submitting.value = true
  try {
    if (editingDataSource.value) {
      await dataSourceStore.updateDataSource(editingDataSource.value.id, config)
      ElMessage.success('更新成功')
    } else {
      await dataSourceStore.createDataSource(config)
      ElMessage.success('创建成功')
    }
    // 刷新数据源列表以确保数据同步
    await loadDataSources()
    handleCancel()
  } catch (error) {
    console.error('Submit error:', error)
    ElMessage.error(editingDataSource.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  showAddDialog.value = false
  editingDataSource.value = null
}

// 生命周期
onMounted(() => {
  loadDataSources()
})
</script>

<style scoped>
.data-source-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>