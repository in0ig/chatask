<template>
  <div class="sheet-selector">
    <div class="selector-header">
      <h4>选择工作表</h4>
      <p class="description">请选择要导入的工作表</p>
    </div>
    
    <div class="sheet-list">
      <div
        v-for="sheet in sheets"
        :key="sheet.name"
        class="sheet-item"
        :class="{ 'selected': selectedSheets.includes(sheet.name) }"
        @click="toggleSheet(sheet.name)"
      >
        <div class="sheet-checkbox">
          <el-checkbox
            :model-value="selectedSheets.includes(sheet.name)"
            @change="toggleSheet(sheet.name)"
            @click.stop
          />
        </div>
        
        <div class="sheet-info">
          <div class="sheet-name">{{ sheet.name }}</div>
          <div class="sheet-meta">
            <span class="row-count">{{ sheet.rowCount }} 行</span>
            <span class="col-count">{{ sheet.columnCount }} 列</span>
          </div>
        </div>
        
        <div class="sheet-preview">
          <el-button
            type="text"
            size="small"
            @click.stop="previewSheet(sheet.name)"
            :disabled="loading"
          >
            预览
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 导入选项 -->
    <div class="import-options">
      <h5>导入选项</h5>
      <div class="options-grid">
        <el-checkbox v-model="options.firstRowAsHeader">
          第一行作为字段名
        </el-checkbox>
        <el-checkbox v-model="options.autoInferTypes">
          自动推断字段类型
        </el-checkbox>
        <el-checkbox v-model="options.skipEmptyRows">
          跳过空行
        </el-checkbox>
        <el-checkbox v-model="options.trimWhitespace">
          去除前后空格
        </el-checkbox>
      </div>
    </div>
    
    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="`预览: ${previewSheetName}`"
      width="80%"
      :before-close="closePreview"
    >
      <div v-if="previewLoading" class="preview-loading">
        <el-skeleton :rows="5" animated />
      </div>
      
      <div v-else-if="previewData" class="preview-content">
        <div class="preview-info">
          <span>共 {{ previewData.totalRows }} 行，显示前 {{ previewData.data.length }} 行</span>
        </div>
        
        <el-table
          :data="previewData.data"
          border
          size="small"
          max-height="400"
          class="preview-table"
        >
          <el-table-column
            v-for="(column, index) in previewData.columns"
            :key="index"
            :prop="column.key"
            :label="column.label"
            :width="120"
            show-overflow-tooltip
          />
        </el-table>
      </div>
      
      <div v-else class="preview-error">
        <el-empty description="预览数据加载失败" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

// 工作表信息接口
export interface SheetInfo {
  name: string
  rowCount: number
  columnCount: number
  hasHeader?: boolean
}

// 导入选项接口
export interface ImportOptions {
  firstRowAsHeader: boolean
  autoInferTypes: boolean
  skipEmptyRows: boolean
  trimWhitespace: boolean
}

// 预览数据接口
export interface PreviewData {
  columns: Array<{ key: string; label: string }>
  data: Record<string, any>[]
  totalRows: number
}

// Props
interface Props {
  sheets: SheetInfo[]
  modelValue: string[]
  options?: ImportOptions
  loading?: boolean
  filePath?: string
}

const props = withDefaults(defineProps<Props>(), {
  sheets: () => [],
  modelValue: () => [],
  options: () => ({
    firstRowAsHeader: true,
    autoInferTypes: true,
    skipEmptyRows: false,
    trimWhitespace: true
  }),
  loading: false,
  filePath: ''
})

// Emits
interface Emits {
  (e: 'update:modelValue', sheets: string[]): void
  (e: 'update:options', options: ImportOptions): void
  (e: 'sheet-selected', sheets: string[]): void
  (e: 'preview-sheet', sheetName: string): void
}

const emit = defineEmits<Emits>()

// 响应式数据
const selectedSheets = ref<string[]>([...props.modelValue])
const options = ref<ImportOptions>({ ...props.options })

// 预览相关
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewSheetName = ref('')
const previewData = ref<PreviewData | null>(null)

// 监听选中的工作表变化
watch(selectedSheets, (newSheets) => {
  emit('update:modelValue', newSheets)
  emit('sheet-selected', newSheets)
}, { deep: true })

// 监听选项变化
watch(options, (newOptions) => {
  emit('update:options', newOptions)
}, { deep: true })

// 监听外部传入的选中状态
watch(() => props.modelValue, (newValue) => {
  selectedSheets.value = [...newValue]
})

// 监听外部传入的选项
watch(() => props.options, (newOptions) => {
  options.value = { ...newOptions }
}, { deep: true })

// 计算属性
const hasSelectedSheets = computed(() => selectedSheets.value.length > 0)

// 切换工作表选中状态
const toggleSheet = (sheetName: string) => {
  const index = selectedSheets.value.indexOf(sheetName)
  if (index > -1) {
    selectedSheets.value.splice(index, 1)
  } else {
    selectedSheets.value.push(sheetName)
  }
}

// 预览工作表
const previewSheet = async (sheetName: string) => {
  if (!props.filePath) {
    ElMessage.warning('文件路径不存在，无法预览')
    return
  }
  
  previewSheetName.value = sheetName
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  
  try {
    // 模拟 API 调用获取预览数据
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟预览数据
    const mockData: PreviewData = {
      columns: [
        { key: 'col1', label: 'ID' },
        { key: 'col2', label: '姓名' },
        { key: 'col3', label: '年龄' },
        { key: 'col4', label: '部门' },
        { key: 'col5', label: '薪资' }
      ],
      data: [
        { col1: '1001', col2: '张三', col3: '28', col4: '技术部', col5: '12000' },
        { col1: '1002', col2: '李四', col3: '32', col4: '销售部', col5: '8000' },
        { col1: '1003', col2: '王五', col3: '25', col4: '市场部', col5: '9000' },
        { col1: '1004', col2: '赵六', col3: '30', col4: '技术部', col5: '15000' },
        { col1: '1005', col2: '钱七', col3: '27', col4: '人事部', col5: '7000' }
      ],
      totalRows: 1000
    }
    
    previewData.value = mockData
    emit('preview-sheet', sheetName)
    
  } catch (error) {
    console.error('预览工作表失败:', error)
    ElMessage.error('预览工作表失败')
  } finally {
    previewLoading.value = false
  }
}

// 关闭预览
const closePreview = () => {
  previewVisible.value = false
  previewData.value = null
  previewSheetName.value = ''
}

// 全选/取消全选
const toggleAllSheets = () => {
  if (selectedSheets.value.length === props.sheets.length) {
    selectedSheets.value = []
  } else {
    selectedSheets.value = props.sheets.map(sheet => sheet.name)
  }
}

// 暴露方法给父组件
defineExpose({
  selectedSheets: computed(() => selectedSheets.value),
  options: computed(() => options.value),
  hasSelectedSheets,
  toggleAllSheets
})
</script>

<style scoped>
.sheet-selector {
  width: 100%;
}

.selector-header {
  margin-bottom: 20px;
}

.selector-header h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.description {
  margin: 0;
  font-size: 14px;
  color: #606266;
}

.sheet-list {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 24px;
}

.sheet-item {
  display: flex;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: all 0.2s;
}

.sheet-item:last-child {
  border-bottom: none;
}

.sheet-item:hover {
  background-color: #f8f9fa;
}

.sheet-item.selected {
  background-color: #e6f7ff;
  border-color: #91d5ff;
}

.sheet-checkbox {
  margin-right: 12px;
}

.sheet-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sheet-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.sheet-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.sheet-preview {
  margin-left: 12px;
}

.import-options {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.import-options h5 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.preview-loading {
  padding: 20px;
}

.preview-content {
  max-height: 500px;
  overflow: auto;
}

.preview-info {
  margin-bottom: 12px;
  padding: 8px 12px;
  background-color: #f0f9ff;
  border-radius: 4px;
  font-size: 12px;
  color: #0066cc;
}

.preview-table {
  width: 100%;
}

.preview-table :deep(.el-table__header) {
  background-color: #fafafa;
}

.preview-table :deep(.el-table__body) {
  font-size: 12px;
}

.preview-error {
  padding: 40px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sheet-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .sheet-checkbox {
    margin-right: 0;
  }
  
  .sheet-preview {
    margin-left: 0;
    align-self: flex-end;
  }
  
  .options-grid {
    grid-template-columns: 1fr;
  }
}
</style>