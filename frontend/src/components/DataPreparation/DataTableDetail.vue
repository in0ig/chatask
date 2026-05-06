<template>
  <div class="data-table-detail">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state" data-testid="loading-state">
      <el-skeleton :rows="6" animated />
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state" data-testid="error-state">
      <el-alert
        :title="error"
        type="error"
        :closable="false"
        show-icon
      />
    </div>
    
    <!-- 正常状态 -->
    <div v-else class="detail-content">
      <!-- 表基本信息 -->
      <div class="table-info-section">
        <div class="section-header">
          <h3 class="section-title">基本信息</h3>
          <div class="section-actions">
            <el-button
              type="primary"
              size="small"
              @click="syncTableStructure"
              :loading="syncing"
              data-testid="sync-button"
            >
              <el-icon><Refresh /></el-icon>
              同步表结构
            </el-button>
          </div>
        </div>
        
        <div class="info-grid">
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">表名：</span>
            <span class="info-value" data-testid="table-name-value">{{ tableName }}</span>
          </div>
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">数据源：</span>
            <span class="info-value" data-testid="source-name-value">{{ dataSourceName }}</span>
          </div>
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">状态：</span>
            <el-tag 
              :type="statusType"
              data-testid="status-tag"
            >
              {{ statusText }}
            </el-tag>
          </div>
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">记录数：</span>
            <span class="info-value" data-testid="row-count-value">{{ formatNumber(rowCount) }}</span>
          </div>
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">字段数：</span>
            <span class="info-value" data-testid="field-count-value">{{ fieldCount }}</span>
          </div>
          <div class="info-item" data-testid="table-info-item">
            <span class="info-label">创建时间：</span>
            <span class="info-value" data-testid="created-at-value">{{ formatDate(createdAt) }}</span>
          </div>
          <div class="info-item full-width" data-testid="table-info-item">
            <span class="info-label">描述：</span>
            <span class="info-value" data-testid="description-value">{{ description || '无' }}</span>
          </div>
        </div>
      </div>
      
      <!-- 字段列表 -->
      <div class="fields-section">
        <div class="section-header">
          <h3 class="section-title">字段列表</h3>
          <div class="section-actions">
            <el-button
              type="primary"
              size="small"
              @click="addField"
              :disabled="!tableInfo"
              data-testid="add-field-button"
            >
              <el-icon><Plus /></el-icon>
              添加字段
            </el-button>
          </div>
        </div>
        
        <el-table
          :data="fields"
          stripe
          border
          style="width: 100%"
          data-testid="fields-table"
        >
          <el-table-column prop="name" label="字段名" width="150" data-testid="field-header-name" />
          <el-table-column prop="displayName" label="显示名称" width="150" data-testid="field-header-display-name" />
          <el-table-column prop="type" label="数据类型" width="120" data-testid="field-header-type" />
          <el-table-column prop="isPrimaryKey" label="主键" width="80" align="center" data-testid="field-header-primary-key">
            <template #default="{ row }">
              <el-tag v-if="row.isPrimaryKey" type="success" size="small">是</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="isNullable" label="可为空" width="80" align="center" data-testid="field-header-nullable">
            <template #default="{ row }">
              <el-tag v-if="row.isNullable" type="info" size="small">是</el-tag>
              <el-tag v-else type="warning" size="small">否</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" width="200" data-testid="field-header-description">
            <template #default="{ row }">
              {{ row.description || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="dictionaryName" label="关联字典" width="150" data-testid="field-header-dictionary">
            <template #default="{ row }">
              {{ row.dictionaryName || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" data-testid="field-header-actions">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                link
                @click="editField(row)"
                data-testid="edit-field-button"
              >
                编辑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 表关系列表 -->
      <div class="relations-section">
        <div class="section-header">
          <h3 class="section-title">表关系</h3>
        </div>
        
        <el-table
          :data="relations"
          stripe
          border
          style="width: 100%"
          data-testid="relations-table"
        >
          <el-table-column prop="relation_name" label="关系名称" width="200" data-testid="relation-header-name" />
          <el-table-column label="主表" width="200" data-testid="relation-header-primary">
            <template #default="{ row }">
              {{ row.primary_table_name }}.{{ row.primary_field_name }}
            </template>
          </el-table-column>
          <el-table-column label="外表" width="200" data-testid="relation-header-foreign">
            <template #default="{ row }">
              {{ row.foreign_table_name }}.{{ row.foreign_field_name }}
            </template>
          </el-table-column>
          <el-table-column prop="relation_type" label="关系类型" width="120" data-testid="relation-header-type">
            <template #default="{ row }">
              <el-tag type="info" size="small">{{ row.relation_type || '一对多' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" data-testid="relation-header-description">
            <template #default="{ row }">
              {{ row.description || '-' }}
            </template>
          </el-table-column>
        </el-table>
        
        <el-empty v-if="!relations || relations.length === 0" description="暂无表关系" />
      </div>
    </div>
    
    <!-- 字段编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑字段"
      width="600px"
      :close-on-click-modal="false"
      data-testid="edit-field-dialog"
    >
      <el-form
        ref="editFormRef"
        :model="editingField"
        label-width="120px"
        data-testid="edit-field-form"
      >
        <el-form-item label="字段名" data-testid="field-name-item">
          <el-input v-model="editingField.name" disabled data-testid="field-name-input" />
        </el-form-item>
        
        <el-form-item label="显示名称" data-testid="field-display-name-item">
          <el-input v-model="editingField.displayName" disabled data-testid="field-display-name-input" />
        </el-form-item>
        
        <el-form-item label="数据类型" data-testid="field-type-item">
          <el-input v-model="editingField.type" disabled data-testid="field-type-input" />
        </el-form-item>
        
        <el-form-item label="字段描述" data-testid="field-description-item">
          <el-input
            v-model="editingField.description"
            type="textarea"
            :rows="3"
            placeholder="请输入字段描述"
            data-testid="field-description-input"
          />
        </el-form-item>
        
        <el-form-item label="关联字典" data-testid="field-dictionary-item">
          <el-select
            v-model="editingField.dictionaryId"
            filterable
            remote
            clearable
            reserve-keyword
            placeholder="请搜索并选择字典"
            :remote-method="searchDictionaries"
            :loading="dictionarySearchLoading"
            @focus="loadAllDictionaries"
            style="width: 100%"
            data-testid="field-dictionary-select"
          >
            <el-option
              v-for="dict in dictionaryOptions"
              :key="dict.id"
              :label="dict.name"
              :value="dict.id"
              data-testid="dictionary-option"
            >
              <span>{{ dict.name }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 8px">{{ dict.code }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="cancelEdit" data-testid="cancel-edit-button">取消</el-button>
          <el-button
            type="primary"
            @click="saveFieldEdit"
            :loading="saving"
            data-testid="save-edit-button"
          >
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dataTableApi } from '@/api/dataTableApi'
import { apiClient } from '@/api/index'

// 定义类型
interface DataTableInfo {
  id: number
  tableName: string
  sourceId: number
  isActive: boolean
  rowCount: number
  description: string | null
  createdAt: string
  updatedAt: string
  fields: TableField[]
  relations: TableRelation[]
}

interface TableField {
  id: number
  name: string
  displayName: string
  type: string
  isPrimaryKey: boolean
  isNullable: boolean
  dictionaryCode: string | null
  dictionaryId: string | null
  dictionaryName: string | null
  description: string // 🔥 修复：改为 string 类型，在赋值时确保不为 null
}

interface Dictionary {
  id: string
  code: string
  name: string
}

interface TableRelation {
  id: string
  relation_name: string
  primary_table_id: string
  primary_table_name: string
  primary_field_id: string
  primary_field_name: string
  foreign_table_id: string
  foreign_table_name: string
  foreign_field_id: string
  foreign_field_name: string
  relation_type: string | null
  description: string | null
}

// Store
const dataPrepStore = useDataPreparationStore()

// Props
const props = defineProps({
  tableId: {
    type: String,
    required: true
  }
})

// 状态
const loading = ref(true)
const error = ref<string | null>(null)
const syncing = ref(false)
const tableInfo = ref<DataTableInfo | null>(null)
const editingFieldId = ref<number | null>(null)

// 字段编辑相关状态
const editDialogVisible = ref(false)
const editingField = ref<TableField>({
  id: 0,
  name: '',
  displayName: '',
  type: '',
  isPrimaryKey: false,
  isNullable: false,
  dictionaryCode: null,
  dictionaryId: null,
  dictionaryName: null,
  description: '' // 🔥 修复：使用空字符串而不是 null
})
const dictionaryOptions = ref<Dictionary[]>([])
const dictionarySearchLoading = ref(false)
const saving = ref(false)

// 字段类型选项
const fieldTypes = ref<string[]>([
  'VARCHAR', 'TEXT', 'INT', 'BIGINT', 'DECIMAL', 'DATE', 'DATETIME', 
  'TIMESTAMP', 'BOOLEAN', 'JSON', 'CHAR', 'FLOAT', 'DOUBLE', 'BLOB'
])

// 计算属性
const tableName = computed(() => {
  return tableInfo.value ? tableInfo.value.tableName : ''
})

const dataSourceName = computed(() => {
  if (!dataPrepStore.dataSources || !dataPrepStore.dataSources.data) {
    return '未知数据源'
  }
  const source = dataPrepStore.dataSources.data.find(ds => ds.id === tableInfo.value?.sourceId)
  return source ? source.name : '未知数据源'
})

const statusType = computed(() => {
  return (tableInfo.value && tableInfo.value.isActive) ? 'success' : 'warning'
})

const statusText = computed(() => {
  return (tableInfo.value && tableInfo.value.isActive) ? '激活' : '未激活'
})

const rowCount = computed(() => {
  return (tableInfo.value && tableInfo.value.rowCount) || 0
})

const fieldCount = computed(() => {
  return (tableInfo.value && tableInfo.value.fields && tableInfo.value.fields.length) || 0
})

const createdAt = computed(() => {
  return tableInfo.value ? tableInfo.value.createdAt : undefined
})

const description = computed(() => {
  return tableInfo.value && tableInfo.value.description
})

const fields = computed(() => {
  return (tableInfo.value && tableInfo.value.fields) || []
})

const relations = computed(() => {
  return (tableInfo.value && tableInfo.value.relations) || []
})

// 加载数据表详情
const loadDataTableDetail = async () => {
  loading.value = true
  error.value = null
  try {
    if (!props.tableId) {
      throw new Error('缺少数据表ID')
    }
    
    const data = await dataTableApi.getById(Number(props.tableId))
    
    // Map API response structure to component expected structure
    const mappedFields = data.columns?.map(col => ({
      id: col.id,
      name: col.name,
      displayName: col.name,
      type: col.type,
      isPrimaryKey: col.is_primary_key,
      isNullable: col.is_nullable,
      dictionaryCode: col.dictionary_code || null,
      dictionaryId: col.dictionary_id || null,
      dictionaryName: col.dictionary_name || null,
      description: col.description || '' // 🔥 修复：确保是字符串，不是 null
    })) || []
    
    tableInfo.value = {
      id: data.id,
      tableName: data.table_name,
      sourceId: data.source_id,
      isActive: data.is_active || false,
      rowCount: data.row_count || 0,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
      description: data.description || '',
      fields: mappedFields,
      relations: data.relations || []
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载数据表详情失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 格式化日期
const formatDate = (dateString: string | undefined): string => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 格式化数字
const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN')
}

// 同步表结构
const syncTableStructure = async () => {
  if (!tableInfo.value) return
  
  syncing.value = true
  try {
    const result = await dataTableApi.syncStructure({
      source_id: tableInfo.value.sourceId,
      table_name: tableInfo.value.tableName
    })
    
    // 重新加载表信息
    await loadDataTableDetail()
    
    ElMessage.success('表结构同步成功')
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '同步表结构失败'
    ElMessage.error(errorMessage)
  } finally {
    syncing.value = false
  }
}

// 添加新字段
const addField = async () => {
  if (!tableInfo.value) return
  
  try {
    const newField = await dataTableApi.addField(tableInfo.value.id, {
      name: '新字段',
      type: 'VARCHAR',
      isNullable: true,
      displayName: '新字段'
    })
    
    if (tableInfo.value.fields) {
      tableInfo.value.fields.push(newField)
    }
    
    ElMessage.success('字段添加成功')
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '添加字段失败'
    ElMessage.error(errorMessage)
  }
}

// 编辑字段
const editField = (field: TableField) => {
  console.log('📝 [前端] 编辑字段:', field)
  console.log('📝 [前端] 字段描述值:', field.description, '类型:', typeof field.description)
  
  // 复制字段数据到编辑表单
  // 🔥 修复：确保 description 是字符串类型，而不是 null
  editingField.value = {
    id: field.id,
    name: field.name,
    displayName: field.displayName,
    type: field.type,
    isPrimaryKey: field.isPrimaryKey,
    isNullable: field.isNullable,
    dictionaryCode: field.dictionaryCode,
    dictionaryId: field.dictionaryId,
    dictionaryName: field.dictionaryName,
    description: field.description || '' // 🔥 将 null 转换为空字符串
  }
  
  // 如果有关联字典，加载到选项中
  if (field.dictionaryId && field.dictionaryName) {
    dictionaryOptions.value = [{
      id: field.dictionaryId,
      code: field.dictionaryCode || '',
      name: field.dictionaryName
    }]
  } else {
    dictionaryOptions.value = []
  }
  
  editDialogVisible.value = true
}

// 搜索字典
const searchDictionaries = async (query: string) => {
  console.log('🔍 [前端] 搜索字典:', query)
  dictionarySearchLoading.value = true
  
  try {
    const response = await apiClient.get('/dictionaries/', {
      params: {
        search: query || undefined,  // 如果没有搜索词，不传 search 参数，返回所有字典
        page: 1,
        page_size: 100  // 增加到 100 以显示更多字典
      }
    })
    
    console.log('✅ [前端] 字典搜索结果:', response.data)
    dictionaryOptions.value = response.data.map((dict: any) => ({
      id: dict.id,
      code: dict.code,
      name: dict.name
    }))
  } catch (err) {
    console.error('❌ [前端] 搜索字典失败:', err)
    ElMessage.error('搜索字典失败')
  } finally {
    dictionarySearchLoading.value = false
  }
}

// 加载所有字典（当下拉框获得焦点时）
const loadAllDictionaries = async () => {
  // 如果已经有选项，不重复加载
  if (dictionaryOptions.value.length > 0) {
    return
  }
  
  await searchDictionaries('')
}

// 保存字段编辑
const saveFieldEdit = async () => {
  console.log('💾 [前端] 保存字段编辑:', editingField.value)
  
  saving.value = true
  
  try {
    // 调用更新字段 API
    const updateData = {
      description: editingField.value.description,
      dictionary_id: editingField.value.dictionaryId
    }
    
    console.log('📤 [前端] 发送更新请求:', {
      fieldId: editingField.value.id,
      data: updateData
    })
    
    const response = await apiClient.put(
      `/table-fields/${editingField.value.id}`,
      updateData
    )
    
    console.log('✅ [前端] 字段更新成功:', response.data)
    
    // 更新本地数据
    if (tableInfo.value && tableInfo.value.fields) {
      const fieldIndex = tableInfo.value.fields.findIndex(f => f.id === editingField.value.id)
      if (fieldIndex !== -1) {
        tableInfo.value.fields[fieldIndex].description = editingField.value.description
        tableInfo.value.fields[fieldIndex].dictionaryId = editingField.value.dictionaryId
        
        // 更新字典名称
        if (editingField.value.dictionaryId) {
          const selectedDict = dictionaryOptions.value.find(d => d.id === editingField.value.dictionaryId)
          if (selectedDict) {
            tableInfo.value.fields[fieldIndex].dictionaryName = selectedDict.name
            tableInfo.value.fields[fieldIndex].dictionaryCode = selectedDict.code
          }
        } else {
          tableInfo.value.fields[fieldIndex].dictionaryName = null
          tableInfo.value.fields[fieldIndex].dictionaryCode = null
        }
      }
    }
    
    ElMessage.success('字段更新成功')
    editDialogVisible.value = false
  } catch (err) {
    console.error('❌ [前端] 保存字段失败:', err)
    const errorMessage = err instanceof Error ? err.message : '保存字段失败'
    ElMessage.error(errorMessage)
  } finally {
    saving.value = false
  }
}

// 取消编辑
const cancelEdit = () => {
  console.log('❌ [前端] 取消编辑')
  editDialogVisible.value = false
}

// 初始化
onMounted(() => {
  loadDataTableDetail()
})
</script>

<style scoped>
.data-table-detail {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
}

.loading-state,
.error-state {
  padding: 20px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.table-info-section,
.fields-section {
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #fafafa;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-actions {
  display: flex;
  gap: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-weight: 600;
  color: #606266;
  white-space: nowrap;
}

.info-value {
  color: #303133;
  flex: 1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-table-detail {
    padding: 12px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 16px;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .section-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>