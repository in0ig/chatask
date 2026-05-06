<template>
  <div class="dictionary-manager">
    <!-- 头部工具栏 -->
    <div class="manager-header">
      <div class="header-left">
        <h2 class="title">字典管理</h2>
        <span class="subtitle">管理数据字典和字典项</span>
      </div>
      <div class="header-right">
        <el-button 
          type="primary" 
          :icon="Plus" 
          @click="showCreateDictionaryDialog"
        >
          新建字典
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

    <!-- 主内容区域 -->
    <div class="manager-content">
      <!-- 左侧字典树 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="panel-title">字典树</span>
          <div class="panel-actions">
            <el-input
              v-model="treeSearchText"
              placeholder="搜索字典"
              size="small"
              :prefix-icon="Search"
              clearable
              @input="onTreeSearch"
            />
          </div>
        </div>
        <div class="panel-content">
          <DictionaryTree
            :data="filteredDictionaries"
            :selected-id="selectedDictionaryId"
            :loading="loading"
            @select="onDictionarySelect"
            @create="showCreateDictionaryDialog"
            @edit="onEditDictionary"
            @delete="onDeleteDictionary"
            @create-item="showCreateItemDialog"
          />
        </div>
      </div>

      <!-- 右侧字典项列表 -->
      <div class="right-panel">
        <div class="panel-header">
          <span class="panel-title">
            {{ selectedDictionary ? `${selectedDictionary.name} - 字典项` : '请选择字典' }}
          </span>
          <div class="panel-actions" v-if="selectedDictionary">
            <el-input
              v-model="itemSearchText"
              placeholder="搜索字典项"
              size="small"
              :prefix-icon="Search"
              clearable
              @input="onItemSearch"
            />
            <el-button 
              type="primary" 
              size="small"
              :icon="Plus" 
              @click="showCreateItemDialog"
            >
              新建
            </el-button>
            <el-button 
              type="default" 
              size="small"
              @click="showBatchAddDialog"
            >
              批量添加
            </el-button>
            <el-button
              type="success"
              size="small"
              :icon="Edit"
              :disabled="selectedItems.length === 0"
              @click="showBatchEditDialog"
            >
              批量编辑
            </el-button>
          </div>
        </div>
        <div class="panel-content">
          <div v-if="!selectedDictionary" class="empty-state">
            <el-empty description="请从左侧选择一个字典查看其字典项" />
          </div>
          <DictionaryItemList
            v-else
            :dictionary-id="selectedDictionaryId"
            :items="filteredDictionaryItems"
            :loading="itemsLoading"
            @edit="onEditItem"
            @delete="onDeleteItem"
            @refresh="loadDictionaryItems"
            @selection-change="onItemSelectionChange"
            @update-sort="onItemSortUpdate"
          />
        </div>
      </div>
    </div>

    <!-- 字典表单对话框 -->
    <el-dialog
      v-model="dictionaryDialogVisible"
      :title="dictionaryDialogMode === 'create' ? '新建字典' : '编辑字典'"
      width="600px"
      :close-on-click-modal="false"
    >
      <DictionaryForm
        :mode="dictionaryDialogMode"
        :dictionary="currentDictionary"
        :dictionaries="dictionaries"
        :loading="dictionaryFormLoading"
        @submit="onDictionarySubmit"
        @cancel="closeDictionaryDialog"
      />
    </el-dialog>

    <!-- 字典项表单对话框 -->
    <el-dialog
      v-model="itemDialogVisible"
      :title="itemDialogMode === 'create' ? '新建字典项' : '编辑字典项'"
      width="800px"
      :close-on-click-modal="false"
    >
      <DictionaryItemForm
        v-if="itemDialogVisible"
        :mode="itemDialogMode"
        :dictionary-id="selectedDictionaryId"
        :item="currentItem"
        :loading="itemFormLoading"
        @submit="onItemSubmit"
        @cancel="closeItemDialog"
      />
    </el-dialog>
    
    <!-- 批量添加字典项对话框 -->
    <el-dialog
      v-model="batchAddDialogVisible"
      title="批量添加字典项"
      width="800px"
      :close-on-click-modal="false"
    >
      <DictionaryItemBatchAdd
        v-if="batchAddDialogVisible"
        :loading="batchAddFormLoading"
        @submit="onBatchAddSubmit"
        @cancel="closeBatchAddDialog"
      />
    </el-dialog>

    <!-- 批量编辑字典项对话框 -->
    <el-dialog
      v-model="batchEditDialogVisible"
      title="批量编辑字典项"
      width="600px"
      :close-on-click-modal="false"
    >
      <DictionaryItemBatchEdit
        v-if="batchEditDialogVisible"
        :items="selectedItems"
        :loading="batchEditFormLoading"
        @submit="onBatchEditSubmit"
        @cancel="closeBatchEditDialog"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Edit } from '@element-plus/icons-vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import DictionaryTree from '@/components/DataPreparation/DictionaryTree.vue'
import DictionaryForm from '@/components/DataPreparation/DictionaryForm.vue'
import DictionaryItemList from '@/components/DataPreparation/DictionaryItemList.vue'
import DictionaryItemForm from '@/components/DataPreparation/DictionaryItemForm.vue'
import DictionaryItemBatchAdd from '@/components/DataPreparation/DictionaryItemBatchAdd.vue'
import DictionaryItemBatchEdit from '@/components/DataPreparation/DictionaryItemBatchEdit.vue'
import type { Dictionary, DictionaryItem } from '@/types/dataPreparation'

// Store
const dataPreparationStore = useDataPreparationStore()

// 响应式数据
const loading = ref(false)
const itemsLoading = ref(false)
const selectedDictionaryId = ref<string | null>(null)
const treeSearchText = ref('')
const itemSearchText = ref('')
const selectedItems = ref<DictionaryItem[]>([])

// 字典对话框
const dictionaryDialogVisible = ref(false)
const dictionaryDialogMode = ref<'create' | 'edit'>('create')
const currentDictionary = ref<Dictionary | null>(null)
const dictionaryFormLoading = ref(false)

// 字典项对话框
const itemDialogVisible = ref(false)
const itemDialogMode = ref<'create' | 'edit'>('create')
const currentItem = ref<DictionaryItem | null>(null)
const itemFormLoading = ref(false)

// 批量添加/编辑对话框
const batchAddDialogVisible = ref(false)
const batchAddFormLoading = ref(false)
const batchEditDialogVisible = ref(false)
const batchEditFormLoading = ref(false)


// 计算属性
const dictionaries = computed(() => {
  console.log('🔍 DictionaryManager - dictionaries computed:', dataPreparationStore.dictionaries)
  return dataPreparationStore.dictionaries
})
const dictionaryItems = computed(() => {
  console.log('🔍 DictionaryManager - dictionaryItems computed:', dataPreparationStore.dictionaryItems)
  return dataPreparationStore.dictionaryItems
})

const selectedDictionary = computed(() => {
  if (!dictionaries.value || !selectedDictionaryId.value) return null
  return dictionaries.value.find(dict => dict.id === selectedDictionaryId.value)
})

const filteredDictionaries = computed(() => {
  if (!dictionaries.value) {
    console.log('🔍 DictionaryManager - filteredDictionaries: dictionaries.value is null/undefined')
    return []
  }
  if (!treeSearchText.value) {
    console.log('🔍 DictionaryManager - filteredDictionaries: no search, returning all', dictionaries.value.length, 'items')
    return dictionaries.value
  }
  const filtered = dictionaries.value.filter(dict => 
    dict.name.toLowerCase().includes(treeSearchText.value.toLowerCase()) ||
    dict.description?.toLowerCase().includes(treeSearchText.value.toLowerCase())
  )
  console.log('🔍 DictionaryManager - filteredDictionaries: filtered', filtered.length, 'items')
  return filtered
})

const filteredDictionaryItems = computed(() => {
  console.log('🔍 DictionaryManager - filteredDictionaryItems computed called')
  console.log('🔍 DictionaryManager - dictionaryItems.value:', dictionaryItems.value)
  console.log('🔍 DictionaryManager - selectedDictionaryId.value:', selectedDictionaryId.value)
  
  if (!dictionaryItems.value || !selectedDictionaryId.value) {
    console.log('🚫 DictionaryManager - filteredDictionaryItems: missing data or selectedId')
    return []
  }
  
  const items = dictionaryItems.value.filter(item => item.dictionary_id === selectedDictionaryId.value)
  console.log('🔍 DictionaryManager - filteredDictionaryItems: filtered items for dictionary', selectedDictionaryId.value, ':', items)
  
  if (!itemSearchText.value) {
    console.log('🔍 DictionaryManager - filteredDictionaryItems: no search text, returning', items.length, 'items')
    return items
  }
  
  const searchFiltered = items.filter(item => 
    item.item_key.toLowerCase().includes(itemSearchText.value.toLowerCase()) ||
    item.item_value.toLowerCase().includes(itemSearchText.value.toLowerCase()) ||
    item.description?.toLowerCase().includes(itemSearchText.value.toLowerCase())
  )
  console.log('🔍 DictionaryManager - filteredDictionaryItems: search filtered', searchFiltered.length, 'items')
  return searchFiltered
})

// 方法
const refreshData = async () => {
  loading.value = true
  try {
    console.log('🔄 DictionaryManager - refreshData: starting...')
    await dataPreparationStore.fetchDictionaries()
    console.log('🔄 DictionaryManager - refreshData: dictionaries fetched, count:', dataPreparationStore.dictionaries.length)
    
    if (selectedDictionaryId.value) {
      await loadDictionaryItems()
    }
    ElMessage.success('数据刷新成功')
  } catch (error: any) {
    console.error('🔄 DictionaryManager - refreshData: error:', error)
    ElMessage.error('刷新数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const loadDictionaryItems = async () => {
  if (!selectedDictionaryId.value) {
    console.log('🚫 DictionaryManager - loadDictionaryItems: no selectedDictionaryId')
    return
  }
  
  console.log('🔄 DictionaryManager - loadDictionaryItems: starting for dictionaryId:', selectedDictionaryId.value)
  itemsLoading.value = true
  try {
    await dataPreparationStore.fetchDictionaryItems(selectedDictionaryId.value)
    console.log('✅ DictionaryManager - loadDictionaryItems: success, items count:', dataPreparationStore.dictionaryItems.length)
  } catch (error: any) {
    console.error('❌ DictionaryManager - loadDictionaryItems: error:', error)
    ElMessage.error('加载字典项失败: ' + (error.message || '未知错误'))
  } finally {
    itemsLoading.value = false
  }
}

// 字典树搜索
const onTreeSearch = () => {
  // 搜索逻辑已在计算属性中实现
}

// 字典项搜索
const onItemSearch = () => {
  // 搜索逻辑已在计算属性中实现
}

// 字典选择
const onDictionarySelect = (dictionaryId: string) => {
  console.log('🎯 DictionaryManager - onDictionarySelect called with:', dictionaryId)
  selectedDictionaryId.value = dictionaryId
  console.log('🎯 DictionaryManager - selectedDictionaryId set to:', selectedDictionaryId.value)
}

// 字典管理
const showCreateDictionaryDialog = () => {
  dictionaryDialogMode.value = 'create'
  currentDictionary.value = null
  dictionaryDialogVisible.value = true
}

const onEditDictionary = (dictionary: Dictionary) => {
  dictionaryDialogMode.value = 'edit'
  currentDictionary.value = { ...dictionary }
  dictionaryDialogVisible.value = true
}

const onDeleteDictionary = async (dictionary: Dictionary) => {
  // 检查是否存在子字典
  const hasChildren = dictionaries.value.some(d => d.parent_id === dictionary.id)
  if (hasChildren) {
    ElMessage.error('该字典下存在子字典，请先删除子字典！')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除字典 "${dictionary.name}" 吗？此操作将同时删除该字典下的所有字典项。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await dataPreparationStore.deleteDictionary(dictionary.id)
    ElMessage.success('字典删除成功')
    if (selectedDictionaryId.value === dictionary.id) {
      selectedDictionaryId.value = null
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除字典失败:', error)
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const onDictionarySubmit = async (formData: Partial<Dictionary>) => {
  dictionaryFormLoading.value = true
  try {
    let result
    if (dictionaryDialogMode.value === 'create') {
      result = await dataPreparationStore.createDictionary(formData)
    } else {
      result = await dataPreparationStore.updateDictionary(currentDictionary.value!.id, formData)
    }
    
    ElMessage.success(dictionaryDialogMode.value === 'create' ? '字典创建成功' : '字典更新成功')
    closeDictionaryDialog()
    
    // 如果是新建字典，自动选中
    if (dictionaryDialogMode.value === 'create' && result) {
      selectedDictionaryId.value = result.id
    }
  } catch (error: any) {
    console.error('字典操作失败:', error)
    ElMessage.error('操作失败: ' + (error.message || '未知错误'))
  } finally {
    dictionaryFormLoading.value = false
  }
}

const closeDictionaryDialog = () => {
  dictionaryDialogVisible.value = false
  currentDictionary.value = null
}

// 字典项管理
const showCreateItemDialog = () => {
  if (!selectedDictionaryId.value) {
    ElMessage.warning('请先选择一个字典')
    return
  }
  
  itemDialogMode.value = 'create'
  currentItem.value = null
  itemDialogVisible.value = true
}

const onEditItem = (item: DictionaryItem) => {
  itemDialogMode.value = 'edit'
  currentItem.value = { ...item }
  itemDialogVisible.value = true
}

const onDeleteItem = async (item: DictionaryItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除字典项 "${item.item_value}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    if (!selectedDictionaryId.value) {
      ElMessage.error('未选择字典')
      return
    }
    
    console.log('🗑️ DictionaryManager - onDeleteItem: deleting item', item.id, 'from dictionary', selectedDictionaryId.value)
    await dataPreparationStore.deleteDictionaryItem(item.id, selectedDictionaryId.value)
    console.log('✅ DictionaryManager - onDeleteItem: delete successful, refreshing data')
    
    // 🔧 FIX: 删除成功后立即刷新字典项列表
    await loadDictionaryItems()
    
    ElMessage.success('字典项删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('❌ DictionaryManager - onDeleteItem: delete failed:', error)
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const onItemSubmit = async (formData: Partial<DictionaryItem>) => {
  itemFormLoading.value = true
  try {
    if (itemDialogMode.value === 'create') {
      await dataPreparationStore.createDictionaryItem({
        ...formData,
        dictionary_id: selectedDictionaryId.value
      })
    } else {
      await dataPreparationStore.updateDictionaryItem(currentItem.value!.id, formData)
    }
    
    ElMessage.success(itemDialogMode.value === 'create' ? '字典项创建成功' : '字典项更新成功')
    closeItemDialog()
  } catch (error: any) {
    console.error('字典项操作失败:', error)
    ElMessage.error('操作失败: ' + (error.message || '未知错误'))
  } finally {
    itemFormLoading.value = false
  }
}

const closeItemDialog = () => {
  itemDialogVisible.value = false
  currentItem.value = null
}

// 字典项列表事件处理
const onItemSelectionChange = (items: DictionaryItem[]) => {
  selectedItems.value = items
}

const onItemSortUpdate = async (sortedItems: DictionaryItem[]) => {
    itemsLoading.value = true
    try {
        const payload = sortedItems.map((item, index) => ({ id: item.id, sortOrder: index }))
        await dataPreparationStore.updateDictionaryItemsSort(selectedDictionaryId.value, payload)
        ElMessage.success('排序更新成功')
        await loadDictionaryItems() // 刷新以确认顺序
    } catch (error: any) {
        ElMessage.error('排序更新失败，已恢复原顺序')
        await loadDictionaryItems() // 失败时恢复服务器顺序
        console.error('排序更新失败:', error)
    } finally {
        itemsLoading.value = false
    }
}

// 批量操作
const showBatchAddDialog = () => {
  if (!selectedDictionaryId.value) {
    ElMessage.warning('请先选择一个字典')
    return
  }
  batchAddDialogVisible.value = true
}

const closeBatchAddDialog = () => {
  batchAddDialogVisible.value = false
}

const onBatchAddSubmit = async (items: Array<{ key: string, value: string, description?: string }>) => {
  batchAddFormLoading.value = true
  try {
    await dataPreparationStore.batchCreateDictionaryItems(selectedDictionaryId.value, items)
    ElMessage.success(`成功批量添加 ${items.length} 个字典项`)
    closeBatchAddDialog()
    await loadDictionaryItems()
  } catch (error: any) {
    console.error('批量添加失败:', error)
    ElMessage.error('批量添加失败: ' + (error.message || '未知错误'))
  } finally {
    batchAddFormLoading.value = false
  }
}

const showBatchEditDialog = () => {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('请至少选择一个字典项进行编辑')
    return
  }
  batchEditDialogVisible.value = true
}

const closeBatchEditDialog = () => {
  batchEditDialogVisible.value = false
}

const onBatchEditSubmit = async (formData: { status: 'ENABLED' | 'DISABLED' }) => {
  batchEditFormLoading.value = true
  try {
    const ids = selectedItems.value.map(item => item.id)
    await dataPreparationStore.batchUpdateDictionaryItems(ids, formData)
    ElMessage.success(`成功批量更新 ${ids.length} 个字典项`)
    closeBatchEditDialog()
    await loadDictionaryItems()
  } catch (error: any) {
    console.error('批量编辑失败:', error)
    ElMessage.error('批量编辑失败: ' + (error.message || '未知错误'))
  } finally {
    batchEditFormLoading.value = false
  }
}


// 监听字典选择变化
watch(selectedDictionaryId, (newId, oldId) => {
  console.log('👀 DictionaryManager - watch selectedDictionaryId:', { oldId, newId })
  if (newId) {
    itemSearchText.value = ''
    selectedItems.value = []
    console.log('🔄 DictionaryManager - watch: calling loadDictionaryItems for:', newId)
    loadDictionaryItems()
  } else {
    console.log('🚫 DictionaryManager - watch: newId is null/undefined')
  }
})

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
.dictionary-manager {
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
      gap: 8px;
    }
  }

  .manager-content {
    flex: 1;
    display: flex;
    min-height: 0;

    .left-panel {
      width: 300px;
      border-right: 1px solid #e4e7ed;
      display: flex;
      flex-direction: column;

      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid #e4e7ed;
        background: #fafafa;

        .panel-title {
          font-weight: 500;
          color: #303133;
        }

        .panel-actions {
          flex: 1;
          margin-left: 16px;
        }
      }

      .panel-content {
        flex: 1;
        overflow: auto;
      }
    }

    .right-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;

      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        border-bottom: 1px solid #e4e7ed;
        background: #fafafa;

        .panel-title {
          font-weight: 500;
          color: #303133;
        }

        .panel-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
      }

      .panel-content {
        flex: 1;
        overflow: auto;

        .empty-state {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 300px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .dictionary-manager {
    .manager-content {
      flex-direction: column;

      .left-panel {
        width: 100%;
        height: 300px;
        border-right: none;
        border-bottom: 1px solid #e4e7ed;
      }

      .right-panel {
        height: calc(100vh - 400px);
      }
    }
  }
}
</style>