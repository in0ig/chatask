<template>
  <div class="dictionary-tree-container">
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else-if="data.length === 0" class="empty-container">
      <el-empty description="暂无字典数据">
        <el-button type="primary" @click="$emit('create')">新建字典</el-button>
      </el-empty>
    </div>
    
    <div v-else class="tree-content">
      <div v-for="dictionary in data" :key="dictionary.id" class="tree-node">
        <div 
          class="custom-tree-node"
          :class="{ 'selected': selectedId === dictionary.id }"
          @click="handleNodeClick(dictionary)"
        >
          <span class="node-label">{{ dictionary.name }}</span>
          <span class="node-actions">
            <el-button
              type="primary"
              size="small"
              text
              @click.stop="handleEdit(dictionary)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              text
              @click.stop="handleDelete(dictionary)"
            >
              删除
            </el-button>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Dictionary } from '@/types/dataPreparation'

// Props
interface Props {
  data: Dictionary[]
  selectedId?: string | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selectedId: null,
  loading: false
})

// Emits
const emit = defineEmits<{
  select: [dictionaryId: string]
  create: []
  edit: [dictionary: Dictionary]
  delete: [dictionary: Dictionary]
  'create-item': []
}>()

// 方法
const handleNodeClick = (dictionary: Dictionary) => {
  emit('select', dictionary.id)
}

const handleEdit = (dictionary: Dictionary) => {
  emit('edit', dictionary)
}

const handleDelete = (dictionary: Dictionary) => {
  emit('delete', dictionary)
}
</script>

<style scoped lang="scss">
.dictionary-tree-container {
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

  .tree-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .tree-node {
    margin-bottom: 4px;

    .custom-tree-node {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      border: 1px solid transparent;

      &:hover {
        background-color: #f5f7fa;
      }

      &.selected {
        background-color: #e6f7ff;
        border-color: #1890ff;
      }

      .node-label {
        flex: 1;
        font-size: 14px;
        color: #303133;
        font-weight: 500;
      }

      .node-actions {
        display: flex;
        gap: 4px;
        opacity: 0;
        transition: opacity 0.2s;
      }

      &:hover .node-actions {
        opacity: 1;
      }
    }
  }
}
</style>