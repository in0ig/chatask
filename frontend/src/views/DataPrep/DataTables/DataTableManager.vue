<template>
  <div class="data-table-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据表管理</span>
          <el-button type="primary" @click="handleAddTable" data-testid="add-button">
            <el-icon><Plus /></el-icon>
            新增数据表
          </el-button>
        </div>
      </template>

      <!-- 数据表列表 -->
      <el-table 
        :data="tables" 
        v-loading="loading"
        empty-text="暂无数据表"
      >
        <el-table-column prop="name" label="表名" min-width="150" />
        <el-table-column prop="dataSourceName" label="数据源" width="120" />
        <el-table-column prop="fieldCount" label="字段数" width="80" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row?.fieldCount || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tableType" label="类型" width="80" />
        <el-table-column prop="comment" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="handleViewDetail(row)"
            >
              查看详情
            </el-button>
            <el-button 
              size="small" 
              type="primary" 
              @click="handleEditTable(row)"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDeleteTable(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增数据表对话框 -->
    <el-dialog
      title="新增数据表"
      v-model="showAddDialog"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="add-table-form">
        <!-- 数据源选择 -->
        <div class="form-section">
          <h4>选择数据源</h4>
          <el-select 
            v-model="selectedDataSourceId" 
            @change="handleDataSourceChange"
            placeholder="请选择数据源"
            style="width: 100%"
          >
            <el-option 
              v-for="ds in dataSources" 
              :key="ds.id" 
              :value="ds.id"
              :label="ds.name"
            />
          </el-select>
        </div>

        <!-- 表发现和选择 -->
        <div v-if="selectedDataSourceId" class="form-section">
          <div class="section-header">
            <h4>选择数据表</h4>
            <el-button 
              type="primary"
              @click="handleDiscoverTables"
              :loading="discovering"
            >
              <el-icon><Search /></el-icon>
              {{ discovering ? '发现中...' : '发现表' }}
            </el-button>
          </div>
          
          <div v-if="discoveredTables.length > 0" class="discovered-tables">
            <div class="table-header">
              <el-checkbox 
                v-model="selectAllDiscovered"
                @change="handleSelectAllDiscovered"
              >
                全选
              </el-checkbox>
            </div>
            <div class="discovered-table-list">
              <el-checkbox-group v-model="selectedDiscoveredTables">
                <div 
                  v-for="table in discoveredTables" 
                  :key="table.name"
                  class="discovered-table-item"
                >
                  <el-checkbox :label="table.name">
                    <div class="table-info">
                      <div class="table-name">{{ table.name }}</div>
                      <div class="table-meta">
                        {{ table.fieldCount }} 字段
                        <span v-if="table.comment" class="table-comment">- {{ table.comment }}</span>
                      </div>
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>
          </div>
          
          <div v-else-if="!discovering" class="empty-tables">
            <el-empty description="点击'发现表'来查找数据源中的可用表" />
          </div>
        </div>

        <div v-else class="form-hint">
          <el-alert
            title="请先选择一个数据源"
            type="info"
            :closable="false"
          />
        </div>
      </div>
      
      <template #footer>
        <el-button @click="closeAddDialog">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleAddSelectedTables"
          :disabled="selectedDiscoveredTables.length === 0"
        >
          添加选中的表 ({{ selectedDiscoveredTables.length }})
        </el-button>
      </template>
    </el-dialog>

    <!-- 数据表详情对话框 -->
    <el-dialog
      title="数据表详情"
      v-model="showDetailDialog"
      width="800px"
    >
      <div v-if="selectedTable" class="table-detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="表名">{{ selectedTable.name }}</el-descriptions-item>
            <el-descriptions-item label="数据源">{{ selectedTable.dataSourceName }}</el-descriptions-item>
            <el-descriptions-item label="字段数">{{ selectedTable.fieldCount }}</el-descriptions-item>
            <el-descriptions-item label="表类型">{{ selectedTable.tableType || '表' }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ selectedTable.comment || '无' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        
        <div class="detail-section" style="margin-top: 20px;">
          <h4>字段信息</h4>
          <el-table 
            :data="selectedTable.fields" 
            border
            empty-text="暂无字段信息"
          >
            <el-table-column prop="name" label="字段名" width="150" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="comment" label="描述" min-width="150">
              <template #default="{ row }">
                {{ row?.comment || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="关联字典" min-width="200">
              <template #default="{ row }">
                <span v-if="row?.dictionaryName" class="dictionary-tag">
                  <el-tag type="success" size="small">{{ row.dictionaryName }}</el-tag>
                </span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="selectedTable.relations && selectedTable.relations.length > 0" class="detail-section" style="margin-top: 20px;">
          <h4>关联关系</h4>
          <el-table :data="selectedTable.relations" border>
            <el-table-column prop="relationName" label="关系名称" width="150" />
            <el-table-column label="主表" width="200">
              <template #default="{ row }">
                {{ row.primaryTableName }}.{{ row.primaryFieldName }}
              </template>
            </el-table-column>
            <el-table-column label="外表" width="200">
              <template #default="{ row }">
                {{ row.foreignTableName }}.{{ row.foreignFieldName }}
              </template>
            </el-table-column>
            <el-table-column prop="relationType" label="关系类型" width="120" />
            <el-table-column prop="description" label="描述" min-width="150">
              <template #default="{ row }">
                {{ row?.description || '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>

    <!-- 数据表编辑对话框 -->
    <el-dialog
      title="编辑数据表"
      v-model="showEditDialog"
      width="900px"
      :close-on-click-modal="false"
    >
      <div v-if="editingTable" class="table-edit-form">
        <!-- 基本信息编辑 -->
        <div class="edit-section">
          <h4>基本信息</h4>
          <el-form :model="editingTable || {}" label-width="100px">
            <el-form-item label="表名">
              <el-input :value="editingTable?.name || ''" disabled />
            </el-form-item>
            <el-form-item label="数据源">
              <el-input :value="editingTable?.dataSourceName || ''" disabled />
            </el-form-item>
            <el-form-item label="表描述">
              <el-input 
                v-model="editingTable.comment"
                type="textarea" 
                :rows="2"
                placeholder="请输入表描述"
              />
            </el-form-item>
          </el-form>
        </div>
        
        <!-- 字段信息编辑 -->
        <div class="edit-section" style="margin-top: 20px;">
          <h4>字段信息编辑</h4>
          <el-table 
            :data="editingTable?.fields || []" 
            border
            empty-text="暂无字段信息"
            max-height="400px"
          >
            <el-table-column prop="name" label="字段名" width="150" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="字段描述" min-width="200">
              <template #default="{ row, $index }">
                <el-input 
                  v-model="row.comment" 
                  placeholder="请输入字段描述"
                  size="small"
                />
              </template>
            </el-table-column>
            <el-table-column label="关联字典" min-width="200">
              <template #default="{ row, $index }">
                <DictionarySelector
                  v-model="row.dictionaryId"
                  size="small"
                  placeholder="搜索并选择关联字典"
                  @change="handleDictionaryChange(row, $event)"
                />
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" @click="saveTableEdit" :loading="saving">
          保存修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { chatbiDataSourceApi } from '@/api/chatbiDataSourceApi'
import { dataTableApi } from '@/services/dataTableApi'
import { fieldMappingApi } from '@/api/fieldMappingApi'
import api from '@/services/api'
import DictionarySelector from '@/components/DataPreparation/DictionarySelector.vue'

// 数据源接口
interface DataSource {
  id: string
  name: string
  type: string
  status: string
}

// 数据表字段接口
interface TableField {
  id?: string
  name: string
  type: string
  comment?: string
  isPrimaryKey?: boolean
  isNullable?: boolean
  dictionaryId?: string | null // 关联的字典ID
  dictionaryName?: string | null // 关联的字典名称（用于显示）
}

// 表关联关系接口
interface TableRelation {
  id: string
  relationName: string
  primaryTableName: string
  primaryFieldName: string
  foreignTableName: string
  foreignFieldName: string
  relationType: string
  description?: string
}

// 数据表接口
interface DataTable {
  id: string
  name: string
  dataSourceId: string
  dataSourceName: string
  fieldCount: number
  tableType?: string
  comment?: string
  fields: TableField[]
  relations?: TableRelation[]
}

// 发现的表接口
interface DiscoveredTable {
  name: string
  fieldCount: number
  comment?: string
  fields: TableField[]
}

// 响应式数据
const loading = ref(false)
const discovering = ref(false)
const saving = ref(false)
const selectedTableId = ref<string | null>(null)
const selectedDataSourceId = ref<string>('')
const showAddDialog = ref(false)
const showDetailDialog = ref(false)
const showEditDialog = ref(false)
const selectAllDiscovered = ref(false)
const selectedDiscoveredTables = ref<string[]>([])

const dataSources = ref<DataSource[]>([])
const tables = ref<DataTable[]>([])
const discoveredTables = ref<DiscoveredTable[]>([])
const editingTable = ref<DataTable | null>(null) // 正在编辑的表

// 计算属性
const selectedTable = computed(() => {
  if (!selectedTableId.value) return null
  return tables.value.find(table => table.id === selectedTableId.value)
})

const selectedDataSource = computed(() => {
  if (!selectedDataSourceId.value) return null
  return dataSources.value.find(ds => ds.id === selectedDataSourceId.value)
})

// 事件处理
const handleTableSelect = (tableId: string) => {
  selectedTableId.value = tableId
}

const handleViewDetail = async (table: DataTable) => {
  console.log('📖 开始加载表详情:', table.id)
  
  // 先加载完整的表详情
  try {
    const detail = await dataTableApi.getTableDetail(table.id)
    console.log('✅ 表详情加载成功:', detail)
    console.log('📊 字段数量:', detail.fields?.length || 0)
    
    // 更新 tables 数组中的表信息
    const tableIndex = tables.value.findIndex(t => t.id === table.id)
    if (tableIndex !== -1) {
      // 映射字段数据
      const mappedFields = (detail.fields || []).map(field => {
        console.log('  - 映射字段:', field.field_name, {
          description: field.description,
          dictionary: field.dictionary?.name
        })
        return {
          id: field.id,
          name: field.field_name,
          type: field.data_type,
          comment: field.description || '',
          dictionaryId: field.dictionary_id,
          dictionaryName: field.dictionary?.name || null
        }
      })
      
      // 映射表关联关系
      const mappedRelations = (detail.relations || []).map(rel => ({
        id: rel.id,
        relationName: rel.relation_name,
        primaryTableName: rel.primary_table_name,
        primaryFieldName: rel.primary_field_name,
        foreignTableName: rel.foreign_table_name,
        foreignFieldName: rel.foreign_field_name,
        relationType: rel.join_type,
        description: rel.description
      }))
      
      // 使用 Vue 的响应式更新
      tables.value[tableIndex] = {
        ...tables.value[tableIndex],
        fields: mappedFields,
        relations: mappedRelations
      }
      
      console.log('✅ 字段映射完成，共', mappedFields.length, '个字段')
      console.log('✅ 关联关系映射完成，共', mappedRelations.length, '个关系')
    }
    
    // 数据更新完成后再打开对话框
    selectedTableId.value = table.id
    showDetailDialog.value = true
  } catch (error) {
    console.error('❌ 加载表详情失败:', error)
    ElMessage.warning('加载表详情失败，显示基本信息')
    // 即使失败也打开对话框，显示基本信息
    selectedTableId.value = table.id
    showDetailDialog.value = true
  }
}

const handleEditTable = async (table?: DataTable) => {
  if (table) {
    selectedTableId.value = table.id
  }
  if (selectedTable.value) {
    // 加载完整的表详情用于编辑
    let detail = null
    try {
      console.log('📝 加载表详情用于编辑:', selectedTable.value.id)
      detail = await dataTableApi.getTableDetail(selectedTable.value.id)
      console.log('✅ 表详情加载成功:', detail)
      console.log('📊 表描述:', detail.description)
      console.log('📊 字段数量:', detail.fields?.length || 0)
      
      // 更新选中表的完整信息
      const tableIndex = tables.value.findIndex(t => t.id === selectedTable.value!.id)
      if (tableIndex !== -1) {
        tables.value[tableIndex].fields = (detail.fields || []).map(field => {
          console.log('  - 映射字段:', field.field_name, {
            id: field.id,
            description: field.description,
            dictionary_id: field.dictionary_id
          })
          return {
            id: field.id,
            name: field.field_name,
            type: field.data_type,
            comment: field.description || '',
            dictionaryId: field.dictionary_id || null
          }
        })
        console.log('✅ 字段映射完成，共', tables.value[tableIndex].fields.length, '个字段')
      }
    } catch (error) {
      console.error('❌ 加载表详情失败:', error)
      ElMessage.warning('加载表详情失败，将显示基本编辑功能')
    }
    
    // 创建编辑表的副本，确保不为null
    // 重要：使用 API 返回的 detail.description，而不是 selectedTable.value.comment
    editingTable.value = {
      ...selectedTable.value,
      comment: detail?.description || selectedTable.value.comment || '', // 优先使用 API 返回的最新描述
      fields: (selectedTable.value.fields || []).map(field => ({
        ...field,
        dictionaryId: field.dictionaryId || null
      }))
    }
    
    console.log('📝 编辑表数据:', editingTable.value)
    console.log('📝 表描述值:', editingTable.value.comment)
    console.log('📝 编辑表字段数:', editingTable.value.fields?.length || 0)
    
    // 显示编辑对话框
    showEditDialog.value = true
  }
}

const handleDeleteTable = async (table: DataTable) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据表 "${table.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用真实 API 删除表
    await dataTableApi.deleteDataTable(table.id)
    
    // 刷新表列表
    await refreshTables()
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

const handleDataSourceChange = () => {
  // 清空发现的表和选择
  discoveredTables.value = []
  selectedDiscoveredTables.value = []
  selectAllDiscovered.value = false
}

const handleDiscoverTables = async () => {
  if (!selectedDataSourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  discovering.value = true
  try {
    // 调用真实 API 发现数据源中的表
    const response = await dataTableApi.discoverTables(selectedDataSourceId.value)
    
    // 检查响应格式，确保是数组
    if (Array.isArray(response)) {
      // 转换 API 响应为组件需要的格式
      discoveredTables.value = response.map(table => ({
        name: table.table_name,
        fieldCount: table.field_count || 0,
        comment: table.comment || '',
        fields: table.fields || []
      }))
      
      selectedDiscoveredTables.value = []
      selectAllDiscovered.value = false
      
      ElMessage.success(`从数据源 ${selectedDataSource.value?.name} 发现了 ${discoveredTables.value.length} 个表`)
      console.log(`从数据源 ${selectedDataSource.value?.name} 发现了 ${discoveredTables.value.length} 个表`)
    } else {
      console.warn('发现表API响应格式异常:', response)
      discoveredTables.value = []
      ElMessage.warning('发现表响应格式异常，请检查后端API')
    }
  } catch (error) {
    console.error('发现表失败:', error)
    ElMessage.error('发现表失败，请检查数据源连接')
    discoveredTables.value = []
  } finally {
    discovering.value = false
  }
}

const handleSelectAllDiscovered = () => {
  if (selectAllDiscovered.value) {
    selectedDiscoveredTables.value = discoveredTables.value.map(t => t.name)
  } else {
    selectedDiscoveredTables.value = []
  }
}

const handleAddSelectedTables = async () => {
  if (selectedDiscoveredTables.value.length === 0) return

  try {
    // 调用真实 API 批量同步表结构
    const response = await dataTableApi.batchSyncTableStructures({
      source_id: selectedDataSourceId.value,
      table_names: selectedDiscoveredTables.value
    })

    ElMessage.success(`成功添加 ${response.successfully_synced} 个数据表`)
    
    // 刷新表列表
    await refreshTables()
    closeAddDialog()
  } catch (error) {
    console.error('添加表失败:', error)
    ElMessage.error('添加表失败，请重试')
  }
}

const handleAddTable = () => {
  showAddDialog.value = true
}

const handleConfigureRelations = (tableId: string) => {
  console.log('配置表关联:', tableId)
  // 这里可以打开关联配置弹窗或跳转到关联配置页面
}

const closeAddDialog = () => {
  showAddDialog.value = false
  // 重置表单状态
  selectedDataSourceId.value = ''
  discoveredTables.value = []
  selectedDiscoveredTables.value = []
  selectAllDiscovered.value = false
}

const closeEditDialog = () => {
  showEditDialog.value = false
  editingTable.value = null
}

const saveTableEdit = async () => {
  if (!editingTable.value) return
  
  saving.value = true
  try {
    console.log('💾 开始保存表编辑...')
    
    // 1. 保存表描述（如果有修改）
    if (editingTable.value.comment !== undefined && editingTable.value.comment !== null) {
      console.log('📝 更新表描述:', editingTable.value.comment)
      try {
        await api.put(`/data-tables/${editingTable.value.id}`, {
          description: editingTable.value.comment
        })
        console.log('✅ 表描述更新成功')
      } catch (error) {
        console.error('❌ 表描述更新失败:', error)
        throw error
      }
    }
    
    // 2. 保存字段配置（描述和字典关联）
    const fields = editingTable.value.fields || []
    console.log(`📝 需要更新 ${fields.length} 个字段`)
    
    const fieldUpdatePromises = fields
      .filter(field => field.id) // 只更新有ID的字段
      .map(async (field) => {
        try {
          console.log(`  - 更新字段 ${field.name}:`, {
            description: field.comment,
            dictionary_id: field.dictionaryId
          })
          
          await dataTableApi.updateTableField(field.id!, {
            description: field.comment || '',
            dictionary_id: field.dictionaryId || null
          })
          
          console.log(`  ✅ 字段 ${field.name} 更新成功`)
        } catch (error) {
          console.error(`  ❌ 字段 ${field.name} 更新失败:`, error)
          throw error
        }
      })
    
    await Promise.all(fieldUpdatePromises)
    
    console.log('✅ 所有字段更新成功')
    
    // 显示成功消息
    ElMessage.success('数据表编辑保存成功')
    
    // 关闭对话框（在 nextTick 后执行，确保消息显示完成）
    await nextTick()
    closeEditDialog()
    
    // 注意：不需要刷新表列表，因为我们只修改了字段信息
    // 表列表的基本信息（表名、字段数等）没有变化
  } catch (error) {
    console.error('❌ 保存表编辑失败:', error)
    ElMessage.error('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const handleDictionaryChange = (field: TableField, dictionaryId: string | null) => {
  // 字典选择变化处理
  field.dictionaryId = dictionaryId
  console.log(`字段 ${field.name} 关联字典变更为:`, dictionaryId)
}

const refreshTables = async () => {
  loading.value = true
  try {
    // 调用真实 API 获取数据表列表
    const response = await dataTableApi.getDataTables({
      page: 1,
      page_size: 100 // 获取所有表，暂时不分页
    })
    
    // 检查响应格式，确保有 items 属性
    if (response && response.items && Array.isArray(response.items)) {
      // 转换 API 响应为组件需要的格式
      tables.value = response.items.map(table => ({
        id: table.id,
        name: table.table_name,
        dataSourceId: table.data_source_id,
        dataSourceName: table.data_source_name || '未知数据源',
        fieldCount: table.field_count || 0,
        tableType: table.table_type || '表',
        comment: table.description || '',
        fields: table.fields || [],
        relations: table.relations || []
      }))
      
      console.log(`成功加载 ${tables.value.length} 个数据表`)
    } else {
      console.warn('API 响应格式异常:', response)
      tables.value = []
      ElMessage.warning('数据表列表格式异常，请检查后端API')
    }
  } catch (error) {
    console.error('刷新数据表列表失败:', error)
    ElMessage.error('加载数据表列表失败')
    // 如果 API 调用失败，使用空数组
    tables.value = []
  } finally {
    loading.value = false
  }
}

const loadDataSources = async () => {
  try {
    // 使用真实的数据源 API
    const response = await chatbiDataSourceApi.getDataSources()
    
    // 检查响应格式，确保有 data 属性且是数组
    if (response && response.data && Array.isArray(response.data)) {
      // 转换 API 响应格式到组件需要的格式
      dataSources.value = response.data.map(ds => ({
        id: ds.id,
        name: ds.name,
        type: ds.type,
        status: ds.status === 'active' ? 'connected' : 'disconnected'
      }))
      
      console.log(`成功加载 ${dataSources.value.length} 个数据源`)
    } else {
      console.warn('数据源API响应格式异常:', response)
      dataSources.value = []
      ElMessage.warning('数据源列表格式异常，请检查后端API')
    }
  } catch (error) {
    console.error('加载数据源失败:', error)
    ElMessage.error('加载数据源失败，请检查后端连接')
    // 如果 API 调用失败，使用空数组
    dataSources.value = []
  }
}

// 生命周期
onMounted(async () => {
  await loadDataSources()
  await refreshTables()
})
</script>

<style scoped>
.data-table-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 对话框内容样式 */
.add-table-form {
  padding: 0;
}

.form-section {
  margin-bottom: 24px;
}

.form-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h4 {
  margin: 0;
}

.form-hint {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
}

/* 发现表列表样式 */
.discovered-tables {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 16px;
}

.table-header {
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 16px;
}

.discovered-table-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.discovered-table-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  transition: all 0.2s;
}

.discovered-table-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
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
  font-size: 12px;
  color: #909399;
}

.table-comment {
  color: #606266;
}

/* 详情对话框样式 */
.table-detail {
  padding: 0;
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

/* 编辑对话框样式 */
.table-edit-form {
  padding: 0;
}

.edit-section {
  margin-bottom: 24px;
}

.edit-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

/* 详情对话框样式 */
.table-detail {
  padding: 0;
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

.dictionary-tag {
  display: inline-flex;
  align-items: center;
}

.text-muted {
  color: #909399;
}
</style>