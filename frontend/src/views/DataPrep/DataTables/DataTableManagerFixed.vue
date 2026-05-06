<template>
  <div class="data-table-manager">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">数据表管理</h2>
        <p class="page-description">管理数据源中的表结构和字段配置</p>
      </div>
      <div class="header-right">
        <el-select
          v-model="selectedSourceId"
          placeholder="选择数据源"
          @change="handleSourceChange"
          style="width: 200px; margin-right: 12px;"
          data-testid="source-selector"
        >
          <el-option
            v-for="source in dataSources"
            :key="source.id"
            :label="source.name"
            :value="source.id"
          />
        </el-select>
        <el-button type="primary" @click="handleDiscoverTables" :disabled="!selectedSourceId">
          <el-icon><Search /></el-icon>
          发现表
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 左侧表列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <h3>数据表列表</h3>
          <div class="panel-actions">
            <el-button 
              size="small" 
              @click="refreshTables"
              :loading="loading"
              data-testid="refresh-button"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="loading" class="loading-state">
            <el-skeleton :rows="5" />
          </div>
          <div v-else-if="discoveredTables.length === 0" class="empty-state">
            <el-empty description="请选择数据源并点击发现表按钮" />
          </div>
          <div v-else class="table-list">
            <div 
              v-for="table in discoveredTables" 
              :key="table.table_name"
              class="table-item"
              :class="{ active: selectedTableName === table.table_name }"
              @click="handleTableSelect(table.table_name)"
            >
              <div class="table-info">
                <div class="table-name">{{ table.table_name }}</div>
                <div class="table-meta">
                  {{ table.row_count }} 行
                  <span v-if="table.comment" class="table-comment">{{ table.comment }}</span>
                </div>
                <div class="table-actions">
                  <el-button 
                    size="small" 
                    type="primary" 
                    @click.stop="handleSyncTable(table.table_name)"
                    :loading="syncingTables.has(table.table_name)"
                  >
                    同步结构
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <div class="right-panel">
        <div class="panel-header">
          <h3>{{ selectedTableName || '表详情' }}</h3>
          <div v-if="selectedTableName && tableStructure" class="panel-actions">
            <el-button 
              size="small" 
              @click="handleRefreshStructure"
              :loading="loadingStructure"
            >
              <el-icon><Refresh /></el-icon>
              刷新结构
            </el-button>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="loadingStructure" class="loading-state">
            <el-skeleton :rows="8" />
          </div>
          <div v-else-if="tableStructure" class="table-detail">
            <!-- 基本信息 -->
            <div class="detail-section">
              <h4>基本信息</h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">表名:</span>
                  <span class="value">{{ tableStructure.table_name }}</span>
                </div>
                <div class="info-item">
                  <span class="label">字段数:</span>
                  <span class="value">{{ tableStructure.field_count }}</span>
                </div>
                <div class="info-item">
                  <span class="label">行数:</span>
                  <span class="value">{{ tableStructure.row_count }}</span>
                </div>
                <div v-if="tableStructure.comment" class="info-item">
                  <span class="label">备注:</span>
                  <span class="value">{{ tableStructure.comment }}</span>
                </div>
              </div>
            </div>

            <!-- 字段信息 -->
            <div class="detail-section">
              <h4>字段信息</h4>
              <div class="fields-table">
                <el-table :data="tableStructure.fields" style="width: 100%">
                  <el-table-column prop="name" label="字段名" width="150" />
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="nullable" label="可空" width="80">
                    <template #default="scope">
                      <el-tag :type="scope.row.nullable ? 'info' : 'warning'" size="small">
                        {{ scope.row.nullable ? '是' : '否' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="key" label="键类型" width="100">
                    <template #default="scope">
                      <el-tag v-if="scope.row.key === 'PRI'" type="danger" size="small">主键</el-tag>
                      <el-tag v-else-if="scope.row.key === 'UNI'" type="warning" size="small">唯一</el-tag>
                      <el-tag v-else-if="scope.row.key === 'MUL'" type="info" size="small">索引</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="default" label="默认值" width="120" />
                  <el-table-column prop="comment" label="备注" min-width="200" />
                </el-table>
              </div>
            </div>
          </div>
          <div v-else class="empty-state" data-testid="empty-state">
            <el-empty description="请选择一个数据表查看详情" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { dataTableApi } from '@/services/dataTableApi'
import { dataSourceApi, type DataSource } from '@/services/dataSourceApi'

// 数据源接口
interface DiscoveredTable {
  table_name: string
  comment?: string
  row_count: number
  schema: string
}

// 表结构接口
interface TableStructure {
  table_name: string
  comment?: string
  row_count: number
  field_count: number
  fields: Array<{
    name: string
    type: string
    nullable: boolean
    key: string
    default: string | null
    comment: string | null
  }>
}

// 响应式数据
const loading = ref(false)
const loadingStructure = ref(false)
const selectedSourceId = ref<string>('')
const selectedTableName = ref<string>('')
const dataSources = ref<DataSource[]>([])
const discoveredTables = ref<DiscoveredTable[]>([])
const tableStructure = ref<TableStructure | null>(null)
const syncingTables = ref(new Set<string>())

// 计算属性
const selectedSource = computed(() => {
  if (!selectedSourceId.value) return null
  return dataSources.value.find(source => source.id === selectedSourceId.value)
})

// 事件处理
const handleSourceChange = async (sourceId: string) => {
  selectedTableName.value = ''
  tableStructure.value = null
  discoveredTables.value = []
  
  if (sourceId) {
    // 测试连接
    try {
      const testResult = await dataTableApi.testConnection(sourceId)
      if (!testResult.success) {
        ElMessage.error(`数据源连接失败: ${testResult.message}`)
        return
      }
    } catch (error) {
      console.error('测试连接失败:', error)
      ElMessage.error('数据源连接测试失败')
      return
    }
  }
}

const handleDiscoverTables = async () => {
  if (!selectedSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  loading.value = true
  try {
    const tables = await dataTableApi.discoverTables(selectedSourceId.value)
    discoveredTables.value = tables
    ElMessage.success(`发现 ${tables.length} 个数据表`)
  } catch (error) {
    console.error('发现表失败:', error)
    ElMessage.error('发现数据表失败')
    discoveredTables.value = []
  } finally {
    loading.value = false
  }
}

const handleTableSelect = async (tableName: string) => {
  if (selectedTableName.value === tableName) return
  
  selectedTableName.value = tableName
  await loadTableStructure()
}

const loadTableStructure = async () => {
  if (!selectedSourceId.value || !selectedTableName.value) return

  loadingStructure.value = true
  try {
    const structure = await dataTableApi.getTableStructure(selectedSourceId.value, selectedTableName.value)
    tableStructure.value = structure
  } catch (error) {
    console.error('获取表结构失败:', error)
    ElMessage.error('获取表结构失败')
    tableStructure.value = null
  } finally {
    loadingStructure.value = false
  }
}

const handleSyncTable = async (tableName: string) => {
  if (!selectedSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  syncingTables.value.add(tableName)
  try {
    const result = await dataTableApi.syncStructure({
      source_id: parseInt(selectedSourceId.value),
      table_name: tableName
    })
    ElMessage.success(`表 ${tableName} 同步成功`)
    
    // 如果当前选中的表就是同步的表，刷新结构信息
    if (selectedTableName.value === tableName) {
      await loadTableStructure()
    }
  } catch (error) {
    console.error('同步表结构失败:', error)
    ElMessage.error(`同步表 ${tableName} 失败`)
  } finally {
    syncingTables.value.delete(tableName)
  }
}

const handleRefreshStructure = async () => {
  await loadTableStructure()
}

const refreshTables = async () => {
  if (!selectedSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }
  await handleDiscoverTables()
}

// 加载数据源列表
const loadDataSources = async () => {
  try {
    const sources = await dataSourceApi.getAll()
    dataSources.value = sources.filter(source => source.isActive)
  } catch (error) {
    console.error('加载数据源失败:', error)
    ElMessage.error('加载数据源列表失败')
  }
}

// 生命周期
onMounted(async () => {
  await loadDataSources()
})
</script>

<style scoped>
.data-table-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f5f5f5;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.header-left {
  flex: 1;
}

.page-title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.page-description {
  margin: 0;
  font-size: 14px;
  color: #606266;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px;
  min-height: 0;
}

.left-panel {
  width: 320px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.right-panel {
  flex: 1;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-content {
  flex: 1;
  overflow: auto;
}

.loading-state,
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.table-list {
  padding: 8px;
}

.table-item {
  padding: 12px;
  margin: 4px 0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.table-item:hover {
  background-color: #f5f7fa;
  border-color: #e4e7ed;
}

.table-item.active {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.table-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-name {
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.table-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.table-comment {
  color: #606266;
  font-style: italic;
}

.table-actions {
  display: flex;
  justify-content: flex-end;
}

.table-detail {
  padding: 20px;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  font-weight: 500;
  color: #606266;
  min-width: 60px;
}

.info-item .value {
  color: #303133;
}

.fields-table {
  margin-top: 12px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .left-panel {
    width: 280px;
  }
}

@media (max-width: 992px) {
  .main-content {
    flex-direction: column;
  }
  
  .left-panel {
    width: 100%;
    height: 300px;
  }
  
  .right-panel {
    height: 400px;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-right {
    width: 100%;
    justify-content: flex-end;
  }
  
  .main-content {
    padding: 12px;
    gap: 12px;
  }
  
  .left-panel {
    height: 250px;
  }
  
  .right-panel {
    height: 350px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>