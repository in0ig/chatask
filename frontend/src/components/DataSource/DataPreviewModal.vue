<template>
  <el-dialog
    v-model="visible"
    :title="previewTitle"
    width="90%"
    :fullscreen="true"
    :before-close="handleClose"
    :destroy-on-close="true"
    class="data-preview-modal"
    :modal-append-to-body="true"
  >
    <!-- 多表选择下拉框 -->
    <div v-if="isMultiTable && selectedTables.length > 0" class="table-selector">
      <span class="selector-label">选择要预览的表：</span>
      <el-select 
        v-model="currentTableId" 
        placeholder="请选择表"
        @change="handleTableChange"
        style="width: 300px;"
      >
        <el-option
          v-for="table in selectedTables"
          :key="table.id"
          :label="table.name"
          :value="table.id"
        />
      </el-select>
    </div>
    
    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="preview-tabs" @tab-click="handleTabClick">
      <el-tab-pane label="字段预览" name="schema" />
      <el-tab-pane label="数据预览" name="data" />
      <el-tab-pane label="表关联" name="relations" v-if="isMultiTable" />
    </el-tabs>
    
    <!-- 字段预览 -->
    <div v-if="activeTab === 'schema'" class="schema-preview">
      <div 
        v-for="field in previewData.schema" 
        :key="field.name"
        class="field-item"
      >
        <el-collapse v-model="activeField" accordion>
          <el-collapse-item :title="field.name + ' (' + field.type + ')'" :name="field.name">
            <div class="field-details">
              <div class="detail-item">
                <span class="label">字段名：</span>
                <span>{{ field.name }}</span>
              </div>
              <div class="detail-item">
                <span class="label">类型：</span>
                <span>{{ field.type }}</span>
              </div>
              <div class="detail-item">
                <span class="label">描述：</span>
                <span>{{ field.description || '无描述' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">单位：</span>
                <span>{{ field.unit || '无' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">类别：</span>
                <span>{{ field.category || '无' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">是否主键：</span>
                <span>{{ field.isPrimaryKey ? '是' : '否' }}</span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
    
    <!-- 数据预览 -->
    <div v-if="activeTab === 'data'" class="data-preview">
      <el-table
        :data="previewData.data"
        style="width: 100%;"
        :max-height="tableMaxHeight"
        border
        highlight-current-row
        class="data-table"
      >
        <el-table-column
          v-for="column in previewData.schema"
          :key="column.name"
          :prop="column.name"
          :label="column.name"
          :min-width="column.minWidth || 120"
          :width="column.width || null"
          :show-overflow-tooltip="true"
          class-name="table-column"
        >
          <template #default="scope">
            <div class="cell-content">
              <span class="cell-text" :style="{ 'max-width': '300px', 'word-wrap': 'break-word', 'white-space': 'normal' }">
                {{ scope.row[column.name] || '-' }}
              </span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页信息 -->
      <div class="pagination-info" v-if="previewData.data && previewData.data.length > 0">
        共 {{ previewData.data.length }} 条记录
      </div>
    </div>
    
    <!-- 表关联预览 -->
    <div v-if="activeTab === 'relations'" class="relations-preview">
      <div v-if="loadingRelations" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="tableRelations.length === 0" class="no-relations">
        <el-empty description="暂无表关联关系" />
      </div>
      <div v-else class="relations-list">
        <el-table
          :data="tableRelations"
          style="width: 100%;"
          border
          highlight-current-row
        >
          <el-table-column prop="relation_name" label="关联名称" width="180" />
          <el-table-column label="主表" width="200">
            <template #default="scope">
              {{ scope.row.primary_table_name }}.{{ scope.row.primary_field_name }}
            </template>
          </el-table-column>
          <el-table-column prop="join_type" label="连接类型" width="100" align="center">
            <template #default="scope">
              <el-tag :type="getJoinTypeTag(scope.row.join_type)">
                {{ scope.row.join_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="从表" width="200">
            <template #default="scope">
              {{ scope.row.foreign_table_name }}.{{ scope.row.foreign_field_name }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="80" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.status ? 'success' : 'info'">
                {{ scope.row.status ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
    
    <!-- 多表选择提示 -->
    <div v-if="isMultiTable && activeTab !== 'relations'" class="multi-table-tip">
      <el-alert
        :title="`已选择 ${selectedTables.length} 个数据表，当前显示：${currentTableName}`"
        type="info"
        show-icon
        :closable="false"
      />
    </div>
    
    <!-- 无数据提示 -->
    <div v-if="!previewData.data || previewData.data.length === 0" class="no-data">
      <p>暂无数据可预览</p>
    </div>
    
    <!-- 底部按钮 -->
    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  previewData: {
    type: Object,
    default: () => ({
      schema: [],
      data: []
    })
  },
  isMultiTable: {
    type: Boolean,
    default: false
  },
  selectedTables: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'table-change'])

// State
const visible = ref(props.modelValue)
const activeTab = ref('schema')
const activeField = ref('')
const currentTableId = ref('')
const loadingRelations = ref(false)
const tableRelations = ref([])

// 计算属性：当前表名
const currentTableName = computed(() => {
  if (!currentTableId.value || props.selectedTables.length === 0) {
    return ''
  }
  const table = props.selectedTables.find(t => t.id === currentTableId.value)
  return table ? table.name : ''
})

// 计算属性：预览标题
const previewTitle = computed(() => {
  if (props.isMultiTable) {
    return `多表预览 (${props.selectedTables.length} 个表)`
  }
  
  if (props.previewData.schema && props.previewData.schema.length > 0) {
    return props.previewData.schema[0].name || '数据预览'
  }
  
  return '数据预览'
})

// 计算属性：表格最大高度
const tableMaxHeight = computed(() => {
  return window.innerHeight - 200 // 200px 是标题、标签页和底部按钮的高度
})

// 监听 props 变化
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
  if (newValue && props.isMultiTable && props.selectedTables.length > 0) {
    // 默认选择第一个表
    currentTableId.value = props.selectedTables[0].id
    // 加载表关联数据
    loadTableRelations()
  }
})

// 监听选中的表变化
watch(() => props.selectedTables, (newTables) => {
  if (newTables.length > 0 && !currentTableId.value) {
    currentTableId.value = newTables[0].id
  }
}, { immediate: true })

// 处理对话框关闭
const handleClose = () => {
  visible.value = false
  emit('update:modelValue', false)
  // 重置状态
  activeTab.value = 'schema'
  currentTableId.value = ''
  tableRelations.value = []
}

// 处理标签页切换
const handleTabClick = (tab) => {
  activeTab.value = tab.props.name
  if (tab.props.name === 'relations' && tableRelations.value.length === 0) {
    loadTableRelations()
  }
}

// 处理表切换
const handleTableChange = (tableId) => {
  currentTableId.value = tableId
  emit('table-change', tableId)
}

// 加载表关联数据
const loadTableRelations = async () => {
  if (!props.isMultiTable || props.selectedTables.length === 0) {
    return
  }
  
  loadingRelations.value = true
  try {
    // 获取所有选中表的ID
    const tableIds = props.selectedTables.map(t => t.id)
    
    // 调用后端API获取表关联
    const response = await axios.get('/api/table-relations', {
      params: {
        // 可以根据需要添加筛选条件
        limit: 100
      }
    })
    
    // 筛选出与选中表相关的关联
    if (response.data && Array.isArray(response.data)) {
      tableRelations.value = response.data.filter(relation => 
        tableIds.includes(relation.primary_table_id) || 
        tableIds.includes(relation.foreign_table_id)
      )
    } else {
      tableRelations.value = []
    }
  } catch (error) {
    console.error('加载表关联失败:', error)
    ElMessage.error('加载表关联失败')
    tableRelations.value = []
  } finally {
    loadingRelations.value = false
  }
}

// 获取连接类型标签样式
const getJoinTypeTag = (joinType) => {
  const typeMap = {
    'INNER': 'primary',
    'LEFT': 'success',
    'RIGHT': 'warning',
    'FULL': 'danger'
  }
  return typeMap[joinType] || 'info'
}

// 监听 visible 变化以同步到父组件
watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
})

// 组件挂载时初始化
onMounted(() => {
  if (props.isMultiTable && props.selectedTables.length > 0) {
    currentTableId.value = props.selectedTables[0].id
  }
})
</script>

<style scoped>
.data-preview-modal {
  --el-dialog-padding-primary: 16px;
}

.table-selector {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.selector-label {
  font-weight: 600;
  margin-right: 12px;
  color: var(--el-text-color-primary);
}

.preview-tabs {
  margin-bottom: 16px;
}

.schema-preview {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 16px 0;
}

.field-item {
  margin-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color);
}

.field-item:last-child {
  border-bottom: none;
}

.field-details {
  padding: 12px;
  background-color: #f8f8f8;
  border-radius: 8px;
  margin-top: 8px;
}

.detail-item {
  display: flex;
  margin-bottom: 8px;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.label {
  font-weight: 600;
  color: var(--el-text-color-secondary);
  min-width: 80px;
}

.data-preview {
  height: calc(100vh - 200px);
  overflow: auto;
}

.data-table {
  margin-bottom: 16px;
}

.table-column {
  word-wrap: break-word;
}

.cell-content {
  padding: 8px;
}

.cell-text {
  display: inline-block;
  max-width: 300px;
  word-wrap: break-word;
  white-space: normal;
}

.pagination-info {
  text-align: right;
  color: var(--el-text-color-secondary);
  padding: 8px 16px;
}

.relations-preview {
  height: calc(100vh - 250px);
  overflow: auto;
}

.loading-state {
  padding: 20px;
}

.no-relations {
  padding: 40px;
  text-align: center;
}

.relations-list {
  padding: 16px 0;
}

.multi-table-tip {
  margin: 16px 0;
}

.no-data {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 40px;
  font-size: 16px;
}
</style>