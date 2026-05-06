<template>
  <el-dialog
    v-model="visible"
    :title="'数据表'"
    width="800px"
    :before-close="handleClose"
    class="table-selector-modal"
  >
    <div class="modal-content">
      <!-- 搜索框 -->
      <div class="search-section">
        <el-input
          v-model="searchTerm"
          placeholder="搜索数据表..."
          clearable
          prefix-icon="Search"
          style="width: 300px;"
        />
        <div class="action-buttons">
          <el-button type="primary" size="small" @click="selectAll">全选</el-button>
          <el-button type="primary" size="small" @click="deselectAll">反选</el-button>
          <el-button type="primary" size="small" @click="applyFilter">筛选</el-button>
        </div>
      </div>

      <!-- 数据表列表 -->
      <div class="table-list">
        <div 
          v-for="table in filteredTables" 
          :key="table.id" 
          class="table-item"
        >
          <el-checkbox
            v-model="table.selected"
            :label="table.id"
            class="table-checkbox"
          />
          <span class="table-name">{{ table.name }}</span>
          <el-button 
            text
            size="small" 
            @click="previewTable(table)"
            class="preview-btn"
          >
            预览
          </el-button>
        </div>
      </div>

      <!-- 底部已选信息 -->
      <div class="selected-info">
        已选 {{ selectedCount }} 个表：
        <span v-if="selectedTables.length > 0" class="selected-tables">
          {{ selectedTables.map(t => t.name).join(', ') }}
        </span>
        <span v-else class="no-selection">无</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="confirmSelection">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, defineEmits, defineProps } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  availableTables: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = ref(false)
const searchTerm = ref('')

// 将 availableTables 转换为带 selected 状态的结构
const tableList = ref(props.availableTables.map(table => ({
  ...table,
  selected: props.modelValue.includes(table.id)
})))

// 计算已选表格
const selectedTables = computed(() => {
  return tableList.value.filter(table => table.selected)
})

// 计算已选数量
const selectedCount = computed(() => selectedTables.value.length)

// 过滤表格
const filteredTables = computed(() => {
  if (!searchTerm.value) {
    return tableList.value
  }
  return tableList.value.filter(table => 
    table.name.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
})

// 打开弹窗
const open = () => {
  visible.value = true
}

// 关闭弹窗
const handleClose = () => {
  visible.value = false
  emit('close')
}

// 全选
const selectAll = () => {
  tableList.value.forEach(table => {
    table.selected = true
  })
}

// 反选
const deselectAll = () => {
  tableList.value.forEach(table => {
    table.selected = !table.selected
  })
}

// 应用筛选（当前仅基于搜索框，此方法保留用于未来扩展）
const applyFilter = () => {
  // 当前仅依赖 searchTerm，此方法为未来扩展预留
}

// 预览表格（模拟）
const previewTable = (table) => {
  console.log('预览表格:', table.name)
  // 在实际应用中，这里会打开一个预览弹窗或跳转到预览页面
}

// 确认选择
const confirmSelection = () => {
  const selectedIds = selectedTables.value.map(table => table.id)
  emit('update:modelValue', selectedIds)
  visible.value = false
}

// 监听 modelValue 变化以同步内部状态
watch(() => props.modelValue, (newVal) => {
  tableList.value = props.availableTables.map(table => ({
    ...table,
    selected: newVal.includes(table.id)
  }))
})

// 暴露方法给父组件
defineExpose({
  open
})
</script>

<style scoped>
.table-selector-modal {
  --el-dialog-padding-primary: 0;
}

.modal-content {
  padding: 20px;
  max-height: 600px;
  overflow-y: auto;
}

.search-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.table-list {
  margin-bottom: 20px;
}

.table-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background-color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.table-checkbox {
  margin-right: 12px;
}

.table-name {
  flex-grow: 1;
  font-weight: 500;
  color: #333;
}

.preview-btn {
  color: #1890ff;
  padding: 4px 8px;
}

.preview-btn:hover {
  color: #0978e0;
  background-color: #f0f7ff;
}

.selected-info {
  padding: 12px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border: 1px dashed #ddd;
  margin-bottom: 20px;
}

.selected-tables {
  color: #1890ff;
  font-weight: 500;
}

.no-selection {
  color: #999;
  font-style: italic;
}
</style>