<template>
  <div class="dictionary-item-list">
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>
    
    <div v-else-if="items.length === 0" class="empty-container">
      <el-empty description="暂无字典项数据">
        <el-button type="primary" @click="$emit('refresh')">刷新数据</el-button>
      </el-empty>
    </div>
    
    <div v-else class="table-container">
      <el-table
        ref="tableRef"
        :data="localItems"
        stripe
        border
        height="100%"
        row-key="id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="55" />

        <el-table-column label="排序" width="60" align="center">
          <template #default>
            <el-icon class="drag-handle" style="cursor: grab;"><Rank /></el-icon>
          </template>
        </el-table-column>
        
        <el-table-column
          prop="item_key"
          label="项键"
          width="120"
          sortable
        />
        
        <el-table-column
          prop="item_value"
          label="项值"
          width="150"
          sortable
        />
        
        <el-table-column
          prop="description"
          label="描述"
          min-width="200"
          show-overflow-tooltip
        />
        
        <el-table-column
          prop="sort_order"
          label="顺序"
          width="80"
          sortable
        />
        
        <el-table-column
          prop="status"
          label="状态"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.status ? 'success' : 'danger'"
              size="small"
            >
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column
          label="操作"
          width="120"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              text
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              text
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import type { DictionaryItem } from '@/store/modules/dataPreparation'
import Sortable from 'sortablejs'
import { Rank } from '@element-plus/icons-vue'

// Props
interface Props {
  dictionaryId: string
  items: DictionaryItem[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// Emits
const emit = defineEmits<{
  edit: [item: DictionaryItem]
  delete: [item: DictionaryItem]
  refresh: []
  'selection-change': [selection: DictionaryItem[]]
  'update-sort': [items: DictionaryItem[]]
}>()

// 响应式数据
const tableRef = ref<any>(null)
const localItems = ref<DictionaryItem[]>([])

watch(() => props.items, (newItems) => {
  console.log('📋 DictionaryItemList - props.items changed:', newItems)
  console.log('📋 DictionaryItemList - items count:', newItems?.length || 0)
  localItems.value = [...newItems]
}, { immediate: true, deep: true })

watch(() => props.dictionaryId, (newId) => {
  console.log('📋 DictionaryItemList - props.dictionaryId changed:', newId)
}, { immediate: true })

watch(() => props.loading, (newLoading) => {
  console.log('📋 DictionaryItemList - props.loading changed:', newLoading)
}, { immediate: true })


// 方法
const onSelectionChange = (selection: DictionaryItem[]) => {
  emit('selection-change', selection)
}

const handleEdit = (item: DictionaryItem) => {
  emit('edit', item)
}

const handleDelete = (item: DictionaryItem) => {
  emit('delete', item)
}

// 拖拽排序
const initSortable = () => {
  const tbody = tableRef.value?.$el.querySelector('.el-table__body-wrapper tbody')
  if (!tbody) return

  Sortable.create(tbody, {
    animation: 150,
    handle: '.drag-handle',
    onEnd: (event) => {
      const { newIndex, oldIndex } = event
      if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex) return
      
      const row = localItems.value.splice(oldIndex, 1)[0]
      localItems.value.splice(newIndex, 0, row)

      // Only emit the updated list. The parent will handle assigning new sortOrder.
      emit('update-sort', localItems.value)
    },
  })
}

onMounted(() => {
  initSortable()
})

// Re-initialize when table data changes
watch(() => props.items, () => {
  nextTick(() => {
    initSortable()
  })
}, { deep: true })

</script>

<style scoped lang="scss">
.dictionary-item-list {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;

  .loading-container,
  .empty-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }

  .table-container {
    flex: 1;
    min-height: 0;
  }

  .drag-handle {
    cursor: grab;
  }
}
</style>