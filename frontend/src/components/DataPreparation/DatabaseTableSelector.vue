<template>
  <div class="database-table-selector">
    <!-- 数据源选择 -->
    <div class="source-selection">
      <h4>选择数据源</h4>
      <el-select
        v-model="selectedSourceId"
        placeholder="请选择数据源"
        @change="handleSourceChange"
        style="width: 100%"
        data-testid="source-selector"
      >
        <el-option
          v-for="source in dataSources"
          :key="source.id"
          :label="source.name"
          :value="source.id"
        />
      </el-select>
    </div>

    <!-- 表发现和选择 -->
    <div v-if="selectedSourceId" class="table-selection">
      <div class="section-header">
        <h4>选择数据表</h4>
        <div class="section-actions">
          <el-button
            size="small"
            @click="discoverTables"
            :loading="discovering"
            data-testid="discover-button"
          >
            <el-icon><Refresh /></el-icon>
            {{ discovering ? '发现中...' : '发现表' }}
          </el-button>
        </div>
      </div>

      <!-- 搜索框 -->
      <el-input
        v-model="searchText"
        placeholder="搜索表名..."
        clearable
        class="search-input"
        data-testid="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <!-- 表列表 -->
      <div class="table-list" v-loading="discovering">
        <el-checkbox-group v-model="selectedTables" data-testid="table-checkbox-group">
          <div
            v-for="table in filteredTables"
            :key="table.table_name"
            class="table-item"
            data-testid="table-item"
          >
            <el-checkbox
              :label="table.table_name"
              :value="table.table_name"
              data-testid="table-checkbox"
            >
              <div class="table-info">
                <div class="table-name">{{ table.table_name }}</div>
                <div class="table-meta">
                  <span class="row-count">{{ formatNumber(table.row_count) }} 行</span>
                  <span v-if="table.comment" class="comment">{{ table.comment }}</span>
                </div>
              </div>
            </el-checkbox>
          </div>
        </el-checkbox-group>

        <!-- 空状态 -->
        <div v-if="!discovering && discoveredTables.length === 0" class="empty-state" data-testid="empty-state">
          <el-empty description="未发现任何表，请检查数据源连接" />
        </div>

        <!-- 无搜索结果 -->
        <div v-if="!discovering && discoveredTables.length > 0 && filteredTables.length === 0" class="empty-state" data-testid="no-results">
          <el-empty description="没有找到匹配的表" />
        </div>
      </div>

      <!-- 批量操作 -->
      <div v-if="discoveredTables.length > 0" class="batch-actions">
        <el-button
          size="small"
          @click="selectAll"
          data-testid="select-all-button"
        >
          全选
        </el-button>
        <el-button
          size="small"
          @click="selectNone"
          data-testid="select-none-button"
        >
          全不选
        </el-button>
        <span class="selection-info">
          已选择 {{ selectedTables.length }} / {{ filteredTables.length }} 个表
        </span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <el-button @click="handleCancel" data-testid="cancel-button">
        取消
      </el-button>
      <el-button
        type="primary"
        @click="handleConfirm"
        :disabled="selectedTables.length === 0"
        :loading="syncing"
        data-testid="confirm-button"
      >
        {{ syncing ? '导入中...' : `导入选中的表 (${selectedTables.length})` }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dataTableApi } from '@/services/dataTableApi'

// Props
interface Props {
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: false
})

// Emits
const emit = defineEmits<{
  cancel: []
  confirm: [tables: string[]]
  tablesImported: [count: number]
}>()

// Store
const dataPrepStore = useDataPreparationStore()

// 响应式数据
const selectedSourceId = ref<string>('')
const searchText = ref('')
const discovering = ref(false)
const syncing = ref(false)
const discoveredTables = ref<Array<{table_name: string, comment?: string, row_count: number, schema: string}>>([])
const selectedTables = ref<string[]>([])

// 计算属性
const dataSources = computed(() => dataPrepStore.dataSources.data)

const filteredTables = computed(() => {
  if (!searchText.value.trim()) {
    return discoveredTables.value
  }
  
  const search = searchText.value.toLowerCase()
  return discoveredTables.value.filter(table => 
    table.table_name.toLowerCase().includes(search) ||
    (table.comment && table.comment.toLowerCase().includes(search))
  )
})

// 方法
const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN')
}

const handleSourceChange = () => {
  // 清空之前的发现结果
  discoveredTables.value = []
  selectedTables.value = []
  searchText.value = ''
}

const discoverTables = async () => {
  if (!selectedSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  discovering.value = true
  try {
    const tables = await dataTableApi.discoverTables(selectedSourceId.value)
    discoveredTables.value = tables
    selectedTables.value = []
    
    ElMessage.success(`发现 ${tables.length} 个表`)
  } catch (error) {
    console.error('表发现失败:', error)
    ElMessage.error('表发现失败，请检查数据源连接')
    discoveredTables.value = []
  } finally {
    discovering.value = false
  }
}

const selectAll = () => {
  selectedTables.value = filteredTables.value.map(table => table.table_name)
}

const selectNone = () => {
  selectedTables.value = []
}

const handleCancel = () => {
  emit('cancel')
}

const handleConfirm = async () => {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请至少选择一个表')
    return
  }

  syncing.value = true
  try {
    // 批量同步表结构
    const result = await dataTableApi.batchSyncStructure({
      source_id: selectedSourceId.value,
      table_names: selectedTables.value
    })
    
    if (result.successfully_synced > 0) {
      ElMessage.success(`成功导入 ${result.successfully_synced} 个表`)
      
      // 刷新数据表列表
      await dataPrepStore.fetchDataTables()
      
      emit('tablesImported', result.successfully_synced)
      emit('confirm', selectedTables.value)
    }
    
    if (result.failed_count > 0) {
      ElMessage.warning(`${result.failed_count} 个表导入失败`)
    }
    
  } catch (error) {
    console.error('表导入失败:', error)
    ElMessage.error('表导入失败')
  } finally {
    syncing.value = false
  }
}

// 生命周期
onMounted(async () => {
  // 确保数据源列表已加载
  if (dataSources.value.length === 0) {
    await dataPrepStore.fetchDataSources()
  }
})
</script>

<style scoped>
.database-table-selector {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.source-selection h4,
.section-header h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.search-input {
  margin-bottom: 16px;
}

.table-list {
  flex: 1;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
}

.table-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.table-item:last-child {
  border-bottom: none;
}

.table-info {
  margin-left: 8px;
}

.table-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.table-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.row-count {
  color: #409eff;
}

.comment {
  color: #606266;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid #e4e7ed;
}

.selection-info {
  margin-left: auto;
  font-size: 12px;
  color: #606266;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .batch-actions {
    flex-wrap: wrap;
  }
  
  .selection-info {
    margin-left: 0;
    width: 100%;
    text-align: center;
  }
}
</style>