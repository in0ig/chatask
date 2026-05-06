<template>
  <div class="data-table-tree">
    <div class="search-section">
      <el-input
        v-model="searchText"
        placeholder="搜索数据表..."
        data-testid="search-input"
      />
    </div>
    
    <div class="tree-section">
      <el-tree
        ref="treeRef"
        :data="data"
        :props="treeProps"
        node-key="id"
        @node-click="handleNodeClick"
        data-testid="tree-component"
      />
    </div>
    
    <div v-if="loading" data-testid="loading-indicator">
      <el-skeleton :rows="5" />
    </div>
    
    <div v-if="!loading && data.length === 0" data-testid="empty-state">
      <el-empty description="暂无数据表" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { DataTableNode } from '@/store/modules/dataPreparation'

interface Props {
  data: DataTableNode[]
  loading?: boolean
  selectedTableId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectedTableId: null
})

const emit = defineEmits<{
  select: [tableId: string]
  refresh: []
  syncTable: [tableId: string]
  editTable: [tableId: string]
  deleteTable: [tableId: string]
  duplicateTable: [tableId: string]
  exportTable: [tableId: string]
}>()

const searchText = ref('')
const treeRef = ref()
const syncingTableIds = ref(new Set<string>())

const treeProps = {
  children: 'children',
  label: 'label'
}

// 计算属性
const defaultExpandedKeys = computed(() => {
  return props.data
    .filter(node => node.type === 'datasource')
    .map(node => node.id)
})

const filteredTreeData = computed(() => {
  if (!searchText.value.trim()) {
    return props.data
  }
  
  const filterText = searchText.value.toLowerCase()
  
  return props.data.map(sourceNode => {
    if (sourceNode.type === 'datasource') {
      const filteredChildren = (sourceNode.children || []).filter(tableNode => 
        tableNode.label.toLowerCase().includes(filterText)
      )
      
      if (filteredChildren.length > 0 || sourceNode.label.toLowerCase().includes(filterText)) {
        return {
          ...sourceNode,
          children: filteredChildren
        }
      }
    }
    return null
  }).filter(node => node !== null) as DataTableNode[]
})

// 事件处理方法
const handleNodeClick = (data: DataTableNode) => {
  if (data.type === 'table' && data.tableId) {
    emit('select', data.tableId)
  }
}

const handleSearch = () => {
  // 搜索时自动展开所有匹配的节点
  if (searchText.value.trim()) {
    const expandedKeys = filteredTreeData.value
      .filter(node => node.type === 'datasource')
      .map(node => node.id)
    
    if (treeRef.value) {
      treeRef.value.setExpandedKeys(expandedKeys)
    }
  }
}

const handleSyncTable = async (data: DataTableNode) => {
  if (!data.tableId) return
  
  syncingTableIds.value.add(data.tableId)
  
  try {
    emit('syncTable', data.tableId)
    ElMessage.success('表结构同步成功')
  } catch (error) {
    ElMessage.error('表结构同步失败')
    console.error('表结构同步失败:', error)
  } finally {
    syncingTableIds.value.delete(data.tableId)
  }
}

const handleTableAction = async (command: string, data: DataTableNode) => {
  if (!data.tableId) return
  
  switch (command) {
    case 'edit':
      emit('editTable', data.tableId)
      break
      
    case 'duplicate':
      emit('duplicateTable', data.tableId)
      break
      
    case 'export':
      emit('exportTable', data.tableId)
      break
      
    case 'delete':
      try {
        await ElMessageBox.confirm(
          `确定要删除数据表 "${data.label}" 吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        emit('deleteTable', data.tableId)
      } catch {
        // 用户取消删除
      }
      break
  }
}

// 监听选中状态变化
watch(() => props.selectedTableId, (newId) => {
  if (newId && treeRef.value && treeRef.value.setCurrentKey) {
    // 找到对应的表节点并设置为当前节点
    const findTableNode = (nodes: DataTableNode[]): DataTableNode | null => {
      for (const node of nodes) {
        if (node.type === 'table' && node.tableId === newId) {
          return node
        }
        if (node.children && node.children.length > 0) {
          const found = findTableNode(node.children)
          if (found) return found
        }
      }
      return null
    }
    
    const tableNode = findTableNode(props.data)
    if (tableNode) {
      treeRef.value.setCurrentKey(tableNode.id)
    }
  }
})
</script>

<style scoped>
.data-table-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-section {
  padding: 16px;
}

.tree-section {
  flex: 1;
  overflow-y: auto;
}
</style>