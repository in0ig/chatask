<template>
  <div class="data-source-list">
    <!-- 搜索和筛选区域 -->
    <div class="filter-section">
      <el-input
        v-model="searchText"
        placeholder="按名称搜索..."
        clearable
        style="width: 200px; margin-right: 16px;"
      />
      
      <el-select
        v-model="typeFilter"
        placeholder="按类型筛选"
        clearable
        style="width: 120px; margin-right: 16px;"
      >
        <el-option
          label="MySQL"
          value="mysql"
        />
        <el-option
          label="Excel"
          value="excel"
        />
        <el-option
          label="API"
          value="api"
        />
      </el-select>
      
      <el-select
        v-model="statusFilter"
        placeholder="按状态筛选"
        clearable
        style="width: 120px; margin-right: 16px;"
      >
        <el-option
          label="激活"
          value="active"
        />
        <el-option
          label="禁用"
          value="inactive"
        />
      </el-select>
      
      <el-button type="primary" @click="handleAddDataSource">新增</el-button>
    </div>
    
    <!-- 数据源表格 -->
    <el-table
      :data="filteredDataSources"
      :loading="loading"
      style="width: 100%; margin-top: 16px;"
      empty-text="暂无数据源"
      border
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="scope">
          <el-tag :type="getTagType(scope.row.type)">{{ getDisplayType(scope.row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
            {{ scope.row.is_active ? '激活' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="scope">
          {{ formatDate(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            @click="handleEditDataSource(scope.row)"
            :disabled="loading"
          >
            编辑
          </el-button>
          <el-button
            size="small"
            type="warning"
            @click="handleCopyDataSource(scope.row)"
            :disabled="loading"
          >
            复制
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="handleDeleteDataSource(scope.row)"
            :disabled="loading"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :page-sizes="[10, 20, 50, 100]"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPrep'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DataSource } from '@/types/dataPrep'

// Store
const dataPrepStore = useDataPreparationStore()

// State
const loading = ref(false)
const searchText = ref('')
const typeFilter = ref<string | null>(null)
const statusFilter = ref<string | null>(null)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// Computed
const filteredDataSources = computed(() => {
  return dataPrepStore.dataSources
    .filter(ds => {
      const matchesSearch = !searchText.value || ds.name.toLowerCase().includes(searchText.value.toLowerCase())
      const matchesType = !typeFilter.value || ds.type === typeFilter.value
      const matchesStatus = !statusFilter.value || (statusFilter.value === 'active' ? ds.is_active : !ds.is_active)
      return matchesSearch && matchesType && matchesStatus
    })
    .slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value)
})

// Methods
const handleAddDataSource = () => {
  // 导航到新增数据源页面
  router.push('/data-prep/data-sources/new')
}

const handleEditDataSource = (dataSource: DataSource) => {
  router.push(`/data-prep/data-sources/${dataSource.id}/edit`)
}

const handleCopyDataSource = (dataSource: DataSource) => {
  // 复制逻辑
  ElMessage.info('复制功能待实现')
}

const handleDeleteDataSource = (dataSource: DataSource) => {
  ElMessageBox.confirm(
    `确定要删除数据源 "${dataSource.name}" 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 删除逻辑
    ElMessage.success('删除成功')
  }).catch(() => {
    // 取消删除
  })
}

const handleSizeChange = (newSize: number) => {
  pageSize.value = newSize
  currentPage.value = 1
}

const handleCurrentChange = (newPage: number) => {
  currentPage.value = newPage
}

const getTagType = (type: string): 'primary' | 'info' | 'warning' | 'danger' => {
  switch (type) {
    case 'mysql': return 'primary'
    case 'excel': return 'info'
    case 'api': return 'warning'
    default: return 'info'
  }
}

const getDisplayType = (type: string): string => {
  switch (type) {
    case 'mysql': return 'MySQL'
    case 'excel': return 'Excel'
    case 'api': return 'API'
    default: return type
  }
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// Router
const router = useRouter()

// Load data on mount
onMounted(() => {
  loadDataSourceList()
})

const loadDataSourceList = async () => {
  loading.value = true
  try {
    await dataPrepStore.fetchDataSources()
    total.value = dataPrepStore.dataSources.length
  } catch (error) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.data-source-list {
  padding: 16px;
}

.filter-section {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>