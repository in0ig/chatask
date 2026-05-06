<template>
  <div class="data-table-list">
    <!-- 标题和新增按钮 -->
    <div class="header">
      <h3>数据表列表</h3>
      <el-button type="primary" @click="handleAddTable">新增数据表</el-button>
    </div>

    <!-- 搜索和筛选区域 -->
    <div class="filter-section">
      <el-input
        v-model="searchText"
        placeholder="搜索数据表名称..."
        clearable
        style="width: 200px; margin-right: 10px;"
      />
      
      <el-select
        v-model="sourceFilter"
        placeholder="选择数据源"
        style="width: 150px; margin-right: 10px;"
      >
        <el-option
          v-for="source in dataSourceOptions"
          :key="source.value"
          :label="source.label"
          :value="source.value"
        />
      </el-select>
      
      <el-select
        v-model="statusFilter"
        placeholder="选择状态"
        style="width: 120px; margin-right: 10px;"
      >
        <el-option
          label="全部"
          value=""
        />
        <el-option
          label="已同步"
          value="synced"
        />
        <el-option
          label="未同步"
          value="unsynced"
        />
        <el-option
          label="错误"
          value="error"
        />
      </el-select>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-loading :text="'加载中...'" :spinner="'el-icon-loading'" :background="'rgba(0, 0, 0, 0.7)'" />
    </div>

    <!-- 空数据状态 -->
    <div v-else-if="filteredData.length === 0" class="empty-state">
      <el-empty description="暂无数据表" />
    </div>

    <!-- 数据表列表 -->
    <table v-else class="data-table-table" style="width: 100%; margin-top: 20px; border-collapse: collapse;">
      <thead>
        <tr>
          <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e4e7ed; width: 200px;">表名</th>
          <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e4e7ed; width: 120px;">数据源</th>
          <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e4e7ed; width: 100px;">状态</th>
          <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e4e7ed; width: 180px;">更新时间</th>
          <th style="padding: 12px; text-align: left; border-bottom: 1px solid #e4e7ed; width: 200px;">操作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="table in filteredData" :key="table.id">
          <tr :style="{ backgroundColor: table.status === 'error' ? '#fff0f0' : 'inherit' }">
            <td style="padding: 12px; border-bottom: 1px solid #e4e7ed;">
              {{ table.name }}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e4e7ed;">
              {{ table.dataSource }}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e4e7ed;">
              <el-tag :type="getStatusType(table.status)">{{ getStatusText(table.status) }}</el-tag>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e4e7ed;">
              {{ table.updatedAt }}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e4e7ed;">
              <el-button
                size="small"
                type="primary"
                @click="handleView(table)"
                :disabled="table.status === 'error'"
              >查看</el-button>
              
              <el-button
                size="small"
                type="success"
                @click="handleEdit(table)"
                :disabled="table.status === 'error'"
              >编辑</el-button>
              
              <el-button
                size="small"
                type="warning"
                @click="handleSync(table)"
                :disabled="table.status === 'error'"
              >同步</el-button>
              
              <el-button
                size="small"
                type="danger"
                @click="handleDelete(table)"
              >删除</el-button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dataTableApi } from '@/api/dataTableApi'
import { ElMessage, ElMessageBox } from 'element-plus'

// 状态管理
const dataPreparationStore = useDataPreparationStore()

// 数据绑定
const loading = ref(false)
const searchText = ref('')
const sourceFilter = ref('')
const statusFilter = ref('')

// 数据源选项
const dataSourceOptions = computed(() => {
  return dataPreparationStore.dataSources.map(source => ({
    value: source.id,
    label: source.name
  }))
})

// 数据表列表
const dataTables = ref([])

// 获取数据表列表
const loadDataTables = async () => {
  loading.value = true
  try {
    const response = await dataTableApi.list()
    dataTables.value = response.data || []
  } catch (error) {
    ElMessage.error('获取数据表列表失败')
  } finally {
    loading.value = false
  }
}

// 过滤数据
const filteredData = computed(() => {
  return dataTables.value.filter(table => {
    const matchesSearch = !searchText.value || 
      table.name.toLowerCase().includes(searchText.value.toLowerCase())
    const matchesSource = !sourceFilter.value || table.dataSourceId === sourceFilter.value
    const matchesStatus = !statusFilter.value || table.status === statusFilter.value
    
    return matchesSearch && matchesSource && matchesStatus
  })
})

// 状态文本和类型映射
const getStatusText = (status) => {
  const statusMap = {
    synced: '已同步',
    unsynced: '未同步',
    error: '错误'
  }
  return statusMap[status] || status
}

const getStatusType = (status) => {
  const typeMap = {
    synced: 'success',
    unsynced: 'info',
    error: 'danger'
  }
  return typeMap[status] || 'info'
}

// 操作方法
const handleAddTable = () => {
  ElMessage.info('跳转到新增数据表页面')
}

const handleView = (table) => {
  ElMessage.info(`查看数据表: ${table.name}`)
}

const handleEdit = (table) => {
  ElMessage.info(`编辑数据表: ${table.name}`)
}

const handleSync = async (table) => {
  try {
    await dataTableApi.sync(table.id)
    ElMessage.success('同步成功')
    loadDataTables() // 刷新数据
  } catch (error) {
    ElMessage.error('同步失败')
  }
}

const handleDelete = async (table) => {
  const result = await ElMessageBox.confirm(
    `确定要删除数据表 "${table.name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
  
  if (result === 'confirm') {
    try {
      await dataTableApi.delete(table.id)
      ElMessage.success('删除成功')
      loadDataTables() // 刷新数据
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }
}

// 初始化
onMounted(() => {
  loadDataTables()
})
</script>

<style scoped>
.data-table-list {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-section {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 40px;
}

.data-table-table {
  min-height: 300px;
}
</style>