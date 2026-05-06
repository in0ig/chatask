<template>
  <div class="data-table-tree">
    <!-- 搜索框 -->
    <div class="search-section">
      <el-input
        v-model="searchText"
        placeholder="搜索数据表..."
        clearable
        data-testid="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 树形组件 -->
    <div class="tree-section">
      <el-tree
        ref="treeRef"
        :data="filteredTreeData"
        :props="treeProps"
        :expand-on-click-node="false"
        :highlight-current="true"
        node-key="id"
        :default-expanded-keys="defaultExpandedKeys"
        @node-click="handleNodeClick"
        data-testid="tree-component"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <div class="node-content">
              <el-icon v-if="data.type === 'datasource'" class="node-icon datasource-icon">
                <Database />
              </el-icon>
              <el-icon v-else-if="data.type === 'table'" class="node-icon table-icon">
                <Grid />
              </el-icon>
              
              <span class="node-label">{{ node.label }}</span>
              
              <span v-if="data.type === 'datasource'" class="node-count">
                ({{ getChildrenCount(data) }})
              </span>
            </div>
          </div>
        </template>
      </el-tree>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-section" data-testid="loading-indicator">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && filteredTreeData.length === 0" class="empty-section" data-testid="empty-state">
      <el-empty description="暂无数据表" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Coin, Grid } from '@element-plus/icons-vue'
import type { DataTableNode } from '@/store/modules/dataPreparation'

// Props
interface Props {
  data: DataTableNode[]
  loading?: boolean
  selectedTableId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  selectedTableId: null
})

// Emits
const emit = defineEmits<{
  select: [tableId: string]
}>()

// 响应式数据
const searchText = ref('')
const treeRef = ref()

// 树形组件配置
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
  }).filter(Boolean) as DataTableNode[]
})

// 辅助方法
const getChildrenCount = (data: DataTableNode): number => {
  return (data.children && data.children.length) || 0
}

// 事件处理
const handleNodeClick = (data: DataTableNode) => {
  if (data.type === 'table' && data.tableId) {
    emit('select', data.tableId)
  }
}
</script>

<style scoped>
.data-table-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-section {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.tree-section {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.loading-section {
  padding: 16px;
}

.empty-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tree-node {
  width: 100%;
  padding: 4px 0;
}

.node-content {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0 8px;
}

.node-icon {
  margin-right: 8px;
  flex-shrink: 0;
}

.datasource-icon {
  color: #409eff;
}

.table-icon {
  color: #67c23a;
}

.node-label {
  flex: 1;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-count {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}
</style>