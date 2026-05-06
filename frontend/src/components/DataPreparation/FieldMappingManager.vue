<template>
  <div class="field-mapping-manager">
    <!-- 头部工具栏 -->
    <div class="manager-header">
      <div class="header-left">
        <h2 class="title">字段映射管理</h2>
        <span class="subtitle">为数据表字段配置业务含义和字典映射</span>
      </div>
      <div class="header-right">
        <el-select
          v-model="selectedTableId"
          placeholder="选择数据表"
          clearable
          filterable
          @change="onTableChange"
          style="width: 200px; margin-right: 12px;"
        >
          <el-option
            v-for="table in tables"
            :key="table.id"
            :label="table.name"
            :value="table.id"
          />
        </el-select>
        <el-button 
          type="primary" 
          :icon="Plus" 
          @click="showBatchMappingDialog"
          :disabled="!selectedTableId"
        >
          批量映射
        </el-button>
        <el-button 
          :icon="Download" 
          @click="exportMappings"
          :disabled="!selectedTableId"
        >
          导出
        </el-button>
        <el-button 
          :icon="Upload" 
          @click="showImportDialog"
          :disabled="!selectedTableId"
        >
          导入
        </el-button>
        <el-button 
          :icon="Refresh" 
          @click="refreshData"
          :loading="loading"
        >
          刷新
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-bar" v-if="selectedTableId">
      <el-input
        v-model="searchText"
        placeholder="搜索字段名称或业务名称"
        :prefix-icon="Search"
        clearable
        @input="onSearch"
        style="width: 300px; margin-right: 12px;"
      />
      <el-select
        v-model="filterStatus"
        placeholder="映射状态"
        clearable
        @change="onFilterChange"
        style="width: 150px; margin-right: 12px;"
      >
        <el-option label="已映射" value="mapped" />
        <el-option label="未映射" value="unmapped" />
      </el-select>
      <el-select
        v-model="filterDictionary"
        placeholder="关联字典"
        clearable
        filterable
        @change="onFilterChange"
        style="width: 200px;"
      >
        <el-option
          v-for="dict in dictionaries"
          :key="dict.id"
          :label="dict.name"
          :value="dict.id"
        />
      </el-select>
    </div>

    <!-- 主内容区域 -->
    <div class="manager-content">
      <div v-if="!selectedTableId" class="empty-state">
        <el-empty description="请选择一个数据表开始配置字段映射" />
      </div>
      
      <div v-else class="mapping-table-container">
        <el-table
          :data="filteredMappings"
          :loading="loading"
          stripe
          border
          height="600"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="field_name" label="字段名称" width="150" fixed="left">
            <template #default="{ row }">
              <div class="field-info">
                <span class="field-name">{{ row.field_name }}</span>
                <el-tag size="small" type="info">{{ row.field_type }}</el-tag>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="business_name" label="业务名称" width="180">
            <template #default="{ row }">
              <el-input
                v-if="row.editing"
                v-model="row.business_name"
                size="small"
                placeholder="请输入业务名称"
              />
              <span v-else>{{ row.business_name || '-' }}</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="business_meaning" label="业务含义" min-width="200">
            <template #default="{ row }">
              <el-input
                v-if="row.editing"
                v-model="row.business_meaning"
                type="textarea"
                :rows="2"
                size="small"
                placeholder="请输入业务含义"
              />
              <span v-else>{{ row.business_meaning || '-' }}</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="dictionary_name" label="关联字典" width="150">
            <template #default="{ row }">
              <el-select
                v-if="row.editing"
                v-model="row.dictionary_id"
                size="small"
                clearable
                filterable
                placeholder="选择字典"
              >
                <el-option
                  v-for="dict in dictionaries"
                  :key="dict.id"
                  :label="dict.name"
                  :value="dict.id"
                />
              </el-select>
              <el-tag v-else-if="row.dictionary_name" size="small" type="success">
                {{ row.dictionary_name }}
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="value_range" label="取值范围" width="150">
            <template #default="{ row }">
              <el-input
                v-if="row.editing"
                v-model="row.value_range"
                size="small"
                placeholder="如：1-100"
              />
              <span v-else>{{ row.value_range || '-' }}</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="is_required" label="必填" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                v-if="row.editing"
                v-model="row.is_required"
                size="small"
              />
              <el-tag v-else :type="row.is_required ? 'danger' : 'info'" size="small">
                {{ row.is_required ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="default_value" label="默认值" width="120">
            <template #default="{ row }">
              <el-input
                v-if="row.editing"
                v-model="row.default_value"
                size="small"
                placeholder="默认值"
              />
              <span v-else>{{ row.default_value || '-' }}</span>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <div v-if="row.editing" class="action-buttons">
                <el-button
                  type="primary"
                  size="small"
                  @click="saveMapping(row)"
                  :loading="row.saving"
                >
                  保存
                </el-button>
                <el-button
                  size="small"
                  @click="cancelEdit(row)"
                >
                  取消
                </el-button>
              </div>
              <div v-else class="action-buttons">
                <el-button
                  type="primary"
                  size="small"
                  @click="editMapping(row)"
                >
                  编辑
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="deleteMapping(row)"
                >
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 批量操作栏 -->
        <div v-if="selectedMappings.length > 0" class="batch-actions">
          <span class="selection-info">已选择 {{ selectedMappings.length }} 项</span>
          <el-button type="primary" size="small" @click="showBatchEditDialog">
            批量编辑
          </el-button>
          <el-button type="danger" size="small" @click="batchDeleteMappings">
            批量删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 批量映射对话框 -->
    <el-dialog
      v-model="batchMappingDialogVisible"
      title="批量字段映射"
      width="800px"
      :close-on-click-modal="false"
    >
      <FieldMappingBatchForm
        v-if="batchMappingDialogVisible"
        :table-id="selectedTableId"
        :fields="unmappedFields"
        :dictionaries="dictionaries"
        :loading="batchMappingLoading"
        @submit="onBatchMappingSubmit"
        @cancel="closeBatchMappingDialog"
      />
    </el-dialog>

    <!-- 批量编辑对话框 -->
    <el-dialog
      v-model="batchEditDialogVisible"
      title="批量编辑字段映射"
      width="600px"
      :close-on-click-modal="false"
    >
      <FieldMappingBatchEdit
        v-if="batchEditDialogVisible"
        :mappings="selectedMappings"
        :dictionaries="dictionaries"
        :loading="batchEditLoading"
        @submit="onBatchEditSubmit"
        @cancel="closeBatchEditDialog"
      />
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入字段映射"
      width="600px"
      :close-on-click-modal="false"
    >
      <FieldMappingImport
        v-if="importDialogVisible"
        :table-id="selectedTableId"
        :loading="importLoading"
        @submit="onImportSubmit"
        @cancel="closeImportDialog"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Refresh, Search } from '@element-plus/icons-vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import FieldMappingBatchForm from './FieldMappingBatchForm.vue'
import FieldMappingBatchEdit from './FieldMappingBatchEdit.vue'
import FieldMappingImport from './FieldMappingImport.vue'
import type { DataTable, Dictionary } from '@/store/modules/dataPreparation'

// 字段映射接口定义
interface FieldMapping {
  id?: string
  table_id: string
  field_id: string
  field_name: string
  field_type: string
  dictionary_id?: string
  dictionary_name?: string
  business_name: string
  business_meaning?: string
  value_range?: string
  is_required: boolean
  default_value?: string
  editing?: boolean
  saving?: boolean
  originalData?: any
}

// Store
const dataPreparationStore = useDataPreparationStore()

// 响应式数据
const loading = ref(false)
const selectedTableId = ref<string>('')
const searchText = ref('')
const filterStatus = ref<string>('')
const filterDictionary = ref<string>('')
const selectedMappings = ref<FieldMapping[]>([])
const fieldMappings = ref<FieldMapping[]>([])

// 对话框状态
const batchMappingDialogVisible = ref(false)
const batchMappingLoading = ref(false)
const batchEditDialogVisible = ref(false)
const batchEditLoading = ref(false)
const importDialogVisible = ref(false)
const importLoading = ref(false)

// 计算属性
const tables = computed(() => dataPreparationStore.dataTablesData)
const dictionaries = computed(() => dataPreparationStore.dictionariesData)

const filteredMappings = computed(() => {
  let result = fieldMappings.value

  // 搜索过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(mapping => 
      mapping.field_name.toLowerCase().includes(search) ||
      mapping.business_name?.toLowerCase().includes(search)
    )
  }

  // 状态过滤
  if (filterStatus.value === 'mapped') {
    result = result.filter(mapping => mapping.business_name)
  } else if (filterStatus.value === 'unmapped') {
    result = result.filter(mapping => !mapping.business_name)
  }

  // 字典过滤
  if (filterDictionary.value) {
    result = result.filter(mapping => mapping.dictionary_id === filterDictionary.value)
  }

  return result
})

const unmappedFields = computed(() => {
  return fieldMappings.value.filter(mapping => !mapping.business_name)
})

// 方法
const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      dataPreparationStore.fetchDataTables(),
      dataPreparationStore.fetchDictionaries()
    ])
    if (selectedTableId.value) {
      await loadFieldMappings()
    }
    ElMessage.success('数据刷新成功')
  } catch (error: any) {
    console.error('刷新数据失败:', error)
    ElMessage.error('刷新数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const loadFieldMappings = async () => {
  if (!selectedTableId.value) return
  
  loading.value = true
  try {
    // 调用真实的字段映射API
    const response = await fetch(`/api/field-mappings?table_id=${selectedTableId.value}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    fieldMappings.value = data.items || []
  } catch (error: any) {
    console.error('加载字段映射失败:', error)
    ElMessage.error('加载字段映射失败: ' + (error.message || '未知错误'))
    // 发生错误时返回空数组，不再使用mock数据
    fieldMappings.value = []
  } finally {
    loading.value = false
  }
}

const onTableChange = () => {
  selectedMappings.value = []
  searchText.value = ''
  filterStatus.value = ''
  filterDictionary.value = ''
  if (selectedTableId.value) {
    loadFieldMappings()
  } else {
    fieldMappings.value = []
  }
}

const onSearch = () => {
  // 搜索逻辑已在计算属性中实现
}

const onFilterChange = () => {
  // 过滤逻辑已在计算属性中实现
}

const onSelectionChange = (selection: FieldMapping[]) => {
  selectedMappings.value = selection
}

// 编辑相关方法
const editMapping = (mapping: FieldMapping) => {
  mapping.originalData = { ...mapping }
  mapping.editing = true
}

const cancelEdit = (mapping: FieldMapping) => {
  if (mapping.originalData) {
    Object.assign(mapping, mapping.originalData)
    delete mapping.originalData
  }
  mapping.editing = false
}

const saveMapping = async (mapping: FieldMapping) => {
  if (!mapping.business_name?.trim()) {
    ElMessage.error('业务名称不能为空')
    return
  }

  mapping.saving = true
  try {
    // 调用真实的字段映射保存API
    const updateData = {
      business_name: mapping.business_name,
      business_meaning: mapping.business_meaning,
      dictionary_id: mapping.dictionary_id,
      value_range: mapping.value_range,
      is_required: mapping.is_required,
      default_value: mapping.default_value
    }
    
    const response = await fetch(`/api/field-mappings/${mapping.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updateData)
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    mapping.editing = false
    mapping.saving = false
    delete mapping.originalData
    
    ElMessage.success('字段映射保存成功')
  } catch (error: any) {
    console.error('保存字段映射失败:', error)
    ElMessage.error('保存失败: ' + (error.message || '未知错误'))
  } finally {
    mapping.saving = false
  }
}

const deleteMapping = async (mapping: FieldMapping) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除字段 "${mapping.field_name}" 的映射配置吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用真实的字段映射删除API
    const response = await fetch(`/api/field-mappings/${mapping.id}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 清空映射信息
    mapping.business_name = ''
    mapping.business_meaning = ''
    mapping.dictionary_id = undefined
    mapping.dictionary_name = undefined
    mapping.value_range = ''
    mapping.is_required = false
    mapping.default_value = ''
    
    ElMessage.success('字段映射删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除字段映射失败:', error)
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

// 批量操作方法
const showBatchMappingDialog = () => {
  if (unmappedFields.value.length === 0) {
    ElMessage.warning('当前表的所有字段都已配置映射')
    return
  }
  batchMappingDialogVisible.value = true
}

const closeBatchMappingDialog = () => {
  batchMappingDialogVisible.value = false
}

const onBatchMappingSubmit = async (mappingData: any[]) => {
  batchMappingLoading.value = true
  try {
    // 调用真实的批量字段映射API
    const response = await fetch('/api/field-mappings/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        table_id: selectedTableId.value,
        mappings: mappingData
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 更新本地数据
    mappingData.forEach(data => {
      const mapping = fieldMappings.value.find(m => m.field_id === data.field_id)
      if (mapping) {
        Object.assign(mapping, data)
      }
    })
    
    ElMessage.success(`成功配置 ${mappingData.length} 个字段映射`)
    closeBatchMappingDialog()
  } catch (error: any) {
    console.error('批量映射失败:', error)
    ElMessage.error('批量映射失败: ' + (error.message || '未知错误'))
  } finally {
    batchMappingLoading.value = false
  }
}

const showBatchEditDialog = () => {
  batchEditDialogVisible.value = true
}

const closeBatchEditDialog = () => {
  batchEditDialogVisible.value = false
}

const onBatchEditSubmit = async (editData: any) => {
  batchEditLoading.value = true
  try {
    // 调用真实的批量编辑API
    const mappingIds = selectedMappings.value.map(m => m.id).filter(Boolean)
    const response = await fetch('/api/field-mappings/batch-update', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        mapping_ids: mappingIds,
        updates: editData
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 更新选中的映射
    selectedMappings.value.forEach(mapping => {
      if (editData.dictionary_id !== undefined) {
        mapping.dictionary_id = editData.dictionary_id
        mapping.dictionary_name = editData.dictionary_id ? 
          dictionaries.value.find(d => d.id === editData.dictionary_id)?.name : undefined
      }
      if (editData.is_required !== undefined) {
        mapping.is_required = editData.is_required
      }
    })
    
    ElMessage.success(`成功批量编辑 ${selectedMappings.value.length} 个字段映射`)
    closeBatchEditDialog()
    selectedMappings.value = []
  } catch (error: any) {
    console.error('批量编辑失败:', error)
    ElMessage.error('批量编辑失败: ' + (error.message || '未知错误'))
  } finally {
    batchEditLoading.value = false
  }
}

const batchDeleteMappings = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedMappings.value.length} 个字段映射吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用真实的批量删除API
    const mappingIds = selectedMappings.value.map(m => m.id).filter(Boolean)
    const response = await fetch('/api/field-mappings/batch-delete', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mapping_ids: mappingIds })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 清空选中映射的配置
    selectedMappings.value.forEach(mapping => {
      mapping.business_name = ''
      mapping.business_meaning = ''
      mapping.dictionary_id = undefined
      mapping.dictionary_name = undefined
      mapping.value_range = ''
      mapping.is_required = false
      mapping.default_value = ''
    })
    
    ElMessage.success(`成功删除 ${selectedMappings.value.length} 个字段映射`)
    selectedMappings.value = []
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败: ' + (error.message || '未知错误'))
    }
  }
}

// 导入导出方法
const exportMappings = async () => {
  try {
    // 调用真实的导出API
    const response = await fetch(`/api/field-mappings/export?table_id=${selectedTableId.value}`, {
      method: 'GET'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `field_mappings_${selectedTableId.value}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('字段映射导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
  }
}

const showImportDialog = () => {
  importDialogVisible.value = true
}

const closeImportDialog = () => {
  importDialogVisible.value = false
}

const onImportSubmit = async (importData: any) => {
  importLoading.value = true
  try {
    // 调用真实的导入API
    const formData = new FormData()
    formData.append('file', importData.file)
    formData.append('table_id', selectedTableId.value)
    
    const response = await fetch('/api/field-mappings/import', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    ElMessage.success(`导入成功：${result.success_count} 个成功，${result.failed_count} 个失败`)
    closeImportDialog()
    await loadFieldMappings()
  } catch (error: any) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  } finally {
    importLoading.value = false
  }
}

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
.field-mapping-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;

  .manager-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #e4e7ed;
    background: #fafafa;

    .header-left {
      .title {
        margin: 0 0 4px 0;
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }

      .subtitle {
        font-size: 12px;
        color: #909399;
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .search-bar {
    display: flex;
    align-items: center;
    padding: 12px 20px;
    border-bottom: 1px solid #e4e7ed;
    background: #fafafa;
  }

  .manager-content {
    flex: 1;
    padding: 20px;
    overflow: auto;

    .empty-state {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 400px;
    }

    .mapping-table-container {
      .field-info {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .field-name {
          font-weight: 500;
          color: #303133;
        }
      }

      .action-buttons {
        display: flex;
        gap: 4px;
      }

      .batch-actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        margin-top: 16px;
        background: #f5f7fa;
        border-radius: 4px;

        .selection-info {
          font-size: 14px;
          color: #606266;
        }

        .el-button {
          margin-left: 8px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .field-mapping-manager {
    .manager-header {
      flex-direction: column;
      gap: 12px;
      align-items: stretch;

      .header-right {
        justify-content: center;
        flex-wrap: wrap;
      }
    }

    .search-bar {
      flex-direction: column;
      gap: 8px;
      align-items: stretch;
    }
  }
}
</style>