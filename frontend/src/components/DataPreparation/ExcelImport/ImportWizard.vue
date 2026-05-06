<template>
  <div class="import-wizard">
    <el-dialog
      v-model="visible"
      title="Excel 导入向导"
      width="80%"
      class="wizard-dialog"
    >
      <!-- 步骤导航 -->
      <div class="wizard-steps">
        <el-steps :active="currentStep" align-center>
          <el-step title="上传文件" />
          <el-step title="选择工作表" />
          <el-step title="预览数据" />
          <el-step title="导入数据" />
        </el-steps>
      </div>
      
      <!-- 步骤内容 -->
      <div class="wizard-content">
        <div v-show="currentStep === 0" class="step-content">
          <div class="mock-file-upload">文件上传组件</div>
        </div>
        
        <div v-show="currentStep === 1" class="step-content">
          <div class="mock-sheet-selector">工作表选择组件</div>
        </div>
        
        <div v-show="currentStep === 2" class="step-content">
          <div class="mock-data-preview">数据预览组件</div>
        </div>
        
        <div v-show="currentStep === 3" class="step-content">
          <div class="import-progress">
            <div class="progress-header">
              <h4>正在导入数据...</h4>
              <p>{{ importStatus.message }}</p>
            </div>
            
            <el-progress
              :percentage="importStatus.progress"
              :status="importStatus.status"
              :stroke-width="8"
            />
            
            <div class="progress-stats">
              <div class="stat-item">
                <span>已处理: {{ importStatus.processedRows }} / {{ importStatus.totalRows }}</span>
              </div>
              <div class="stat-item">
                <span>成功: {{ importStatus.successRows }}</span>
              </div>
              <div class="stat-item">
                <span>失败: {{ importStatus.errorRows }}</span>
              </div>
            </div>
            
            <div v-show="importStatus.completed" class="import-result">
              <el-result
                :icon="importStatus.success ? 'success' : 'error'"
                :title="importStatus.success ? '导入成功' : '导入失败'"
                :sub-title="importStatus.resultMessage"
              >
                <template #extra>
                  <div class="result-actions">
                    <el-button v-if="importStatus.success" type="primary" @click="viewImportedData">
                      查看数据
                    </el-button>
                    <el-button v-if="!importStatus.success" type="primary" @click="retryImport">
                      重试导入
                    </el-button>
                    <el-button @click="startNewImport">
                      重新导入
                    </el-button>
                  </div>
                </template>
              </el-result>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="wizard-footer">
          <el-button
            v-if="currentStep > 0 && currentStep < 3"
            @click="prevStep"
            :disabled="loading"
          >
            上一步
          </el-button>
          
          <el-button @click="handleClose" :disabled="loading">
            {{ currentStep === 3 && importStatus.completed ? '关闭' : '取消' }}
          </el-button>
          
          <el-button
            v-if="currentStep < 3"
            type="primary"
            @click="nextStep"
            :disabled="!canProceed || loading"
            :loading="loading"
          >
            {{ getNextButtonText() }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 导入状态接口
interface ImportStatus {
  progress: number
  status: 'success' | 'exception' | undefined
  message: string
  processedRows: number
  totalRows: number
  successRows: number
  errorRows: number
  duration: number
  completed: boolean
  success: boolean
  resultMessage: string
  errors: Array<{
    row: number
    message: string
  }>
}

// Props
interface Props {
  modelValue: boolean
  dataSourceId?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  dataSourceId: ''
})

// Emits
interface Emits {
  (e: 'update:modelValue', visible: boolean): void
  (e: 'import-success', result: any): void
  (e: 'import-error', error: string): void
  (e: 'import-cancelled'): void
}

const emit = defineEmits<Emits>()

// 组件引用
const fileUploadRef = ref()
const sheetSelectorRef = ref()
const dataPreviewRef = ref()

// 响应式数据
const visible = ref(props.modelValue)
const currentStep = ref(0)
const loading = ref(false)

// 文件上传相关
const uploadedFile = ref<File | null>(null)
const filePath = ref('')
const availableSheets = ref<any[]>([])

// Sheet 选择相关
const selectedSheets = ref<string[]>([])
const importOptions = ref({
  firstRowAsHeader: true,
  autoInferTypes: true,
  skipEmptyRows: false,
  trimWhitespace: true
})

// 数据预览相关
const previewData = ref<Record<string, any>[]>([])
const previewFields = ref<any[]>([])
const totalRows = ref(0)
const tableConfig = ref({ tableName: '' })

// 导入状态
const importStatus = ref<ImportStatus>({
  progress: 0,
  status: undefined,
  message: '准备导入...',
  processedRows: 0,
  totalRows: 0,
  successRows: 0,
  errorRows: 0,
  duration: 0,
  completed: false,
  success: false,
  resultMessage: '',
  errors: []
})

// 监听外部 visible 变化
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
})

// 监听内部 visible 变化
watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
  if (!newValue) {
    resetWizard()
  }
})

// 计算属性
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 0:
      return uploadedFile.value !== null && filePath.value !== ''
    case 1:
      return selectedSheets.value.length > 0
    case 2:
      return tableConfig.value.tableName.trim() !== '' && previewFields.value.length > 0
    default:
      return false
  }
})

// 获取下一步按钮文本
const getNextButtonText = () => {
  switch (currentStep.value) {
    case 0:
      return '解析文件'
    case 1:
      return '预览数据'
    case 2:
      return '开始导入'
    default:
      return '下一步'
  }
}

// 格式化持续时间
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

// 文件选择处理
const onFileSelected = (file: File) => {
  uploadedFile.value = file
  const baseName = file.name.replace(/\.[^/.]+$/, '')
  tableConfig.value.tableName = baseName.replace(/[^a-zA-Z0-9_]/g, '_')
}

// 文件清除处理
const onFileCleared = () => {
  uploadedFile.value = null
  filePath.value = ''
  availableSheets.value = []
  tableConfig.value.tableName = ''
}

// 文件上传成功处理
const onUploadSuccess = (result: any) => {
  filePath.value = result.file_path
  availableSheets.value = result.sheet_names.map((name: string) => ({
    name,
    rowCount: result.row_count || 0,
    columnCount: result.column_count || 0
  }))
  
  if (availableSheets.value.length > 0) {
    selectedSheets.value = [availableSheets.value[0].name]
  }
  
  ElMessage.success('文件解析成功')
}

// 文件上传错误处理
const onUploadError = (error: string) => {
  ElMessage.error(`文件上传失败: ${error}`)
}

// Sheet 选择处理
const onSheetsSelected = (sheets: string[]) => {
  selectedSheets.value = sheets
}

// 字段类型变更处理
const onFieldTypeChanged = (field: any, oldType: string) => {
  console.log(`字段 ${field.name} 类型从 ${oldType} 变更为 ${field.dataType}`)
}

// 验证错误处理
const onValidationError = (field: string, message: string) => {
  ElMessage.error(`字段 ${field}: ${message}`)
}

// 下一步
const nextStep = async () => {
  if (!canProceed.value) return
  
  loading.value = true
  
  try {
    switch (currentStep.value) {
      case 0:
        await fileUploadRef.value?.upload()
        break
      case 1:
        await loadPreviewData()
        break
      case 2:
        await startImport()
        break
    }
    
    if (currentStep.value < 3) {
      currentStep.value++
    }
    
  } catch (error: any) {
    console.error('步骤执行失败:', error)
    ElMessage.error(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}

// 上一步
const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 加载预览数据
const loadPreviewData = async () => {
  if (selectedSheets.value.length === 0) {
    throw new Error('请选择至少一个工作表')
  }
  
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  const mockFields = [
    {
      name: 'id',
      displayName: 'ID',
      dataType: 'INTEGER',
      nullable: false,
      sampleData: ['1001', '1002', '1003'],
      originalType: 'INTEGER'
    },
    {
      name: 'name',
      displayName: '姓名',
      dataType: 'VARCHAR',
      nullable: false,
      sampleData: ['张三', '李四', '王五'],
      originalType: 'VARCHAR'
    }
  ]
  
  const mockData = [
    { id: '1001', name: '张三' },
    { id: '1002', name: '李四' },
    { id: '1003', name: '王五' }
  ]
  
  previewFields.value = mockFields
  previewData.value = mockData
  totalRows.value = 1000
}

// 开始导入
const startImport = async () => {
  if (!dataPreviewRef.value?.validateAllFields()) {
    throw new Error('字段配置验证失败')
  }
  
  importStatus.value = {
    progress: 0,
    status: undefined,
    message: '正在准备导入...',
    processedRows: 0,
    totalRows: totalRows.value,
    successRows: 0,
    errorRows: 0,
    duration: 0,
    completed: false,
    success: false,
    resultMessage: '',
    errors: []
  }
  
  const startTime = Date.now()
  
  return new Promise<void>((resolve) => {
    const interval = setInterval(() => {
      importStatus.value.progress += Math.random() * 10
      importStatus.value.processedRows = Math.floor(
        (importStatus.value.progress / 100) * importStatus.value.totalRows
      )
      importStatus.value.duration = Date.now() - startTime
      
      if (importStatus.value.progress < 30) {
        importStatus.value.message = '正在验证数据格式...'
      } else if (importStatus.value.progress < 60) {
        importStatus.value.message = '正在转换数据类型...'
      } else if (importStatus.value.progress < 90) {
        importStatus.value.message = '正在写入数据库...'
      } else {
        importStatus.value.message = '正在完成导入...'
      }
      
      if (importStatus.value.progress >= 100) {
        clearInterval(interval)
        importStatus.value.progress = 100
        importStatus.value.processedRows = importStatus.value.totalRows
        
        const success = Math.random() > 0.2
        
        setTimeout(() => {
          importStatus.value.completed = true
          importStatus.value.success = success
          importStatus.value.duration = Date.now() - startTime
          
          if (success) {
            importStatus.value.status = 'success'
            importStatus.value.successRows = importStatus.value.totalRows - Math.floor(Math.random() * 10)
            importStatus.value.errorRows = importStatus.value.totalRows - importStatus.value.successRows
            importStatus.value.resultMessage = `成功导入 ${importStatus.value.successRows} 条记录到表 ${tableConfig.value.tableName}`
            importStatus.value.message = '导入完成'
            
            emit('import-success', {
              tableName: tableConfig.value.tableName,
              totalRows: importStatus.value.totalRows,
              successRows: importStatus.value.successRows,
              errorRows: importStatus.value.errorRows
            })
          } else {
            importStatus.value.status = 'exception'
            importStatus.value.resultMessage = '导入过程中发生错误，请检查数据格式或联系管理员'
            importStatus.value.message = '导入失败'
            
            emit('import-error', importStatus.value.resultMessage)
          }
          
          resolve()
        }, 1000)
      }
    }, 200)
  })
}

// 查看导入的数据
const viewImportedData = () => {
  ElMessage.success('跳转到数据表管理页面')
  visible.value = false
}

// 重试导入
const retryImport = () => {
  currentStep.value = 2
  importStatus.value.completed = false
}

// 重新开始导入
const startNewImport = () => {
  resetWizard()
}

// 关闭对话框
const handleClose = async () => {
  if (currentStep.value === 3 && !importStatus.value.completed) {
    try {
      await ElMessageBox.confirm(
        '导入正在进行中，确定要取消吗？',
        '确认取消',
        {
          confirmButtonText: '确定',
          cancelButtonText: '继续导入',
          type: 'warning'
        }
      )
      
      emit('import-cancelled')
      visible.value = false
    } catch {
      return
    }
  } else {
    visible.value = false
  }
}

// 重置向导
const resetWizard = () => {
  currentStep.value = 0
  loading.value = false
  
  uploadedFile.value = null
  filePath.value = ''
  availableSheets.value = []
  selectedSheets.value = []
  previewData.value = []
  previewFields.value = []
  totalRows.value = 0
  tableConfig.value = { tableName: '' }
  
  importStatus.value = {
    progress: 0,
    status: undefined,
    message: '准备导入...',
    processedRows: 0,
    totalRows: 0,
    successRows: 0,
    errorRows: 0,
    duration: 0,
    completed: false,
    success: false,
    resultMessage: '',
    errors: []
  }
}

// 暴露方法给父组件
defineExpose({
  open: () => {
    visible.value = true
  },
  close: () => {
    visible.value = false
  },
  reset: resetWizard
})
</script>

<style scoped>
.import-wizard {
  width: 100%;
}

.wizard-steps {
  margin-bottom: 32px;
}

.wizard-content {
  min-height: 400px;
}

.step-content {
  width: 100%;
}

.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.import-progress {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

.progress-header {
  text-align: center;
  margin-bottom: 32px;
}

.progress-header h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.progress-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  margin-top: 24px;
}

.stat-item {
  text-align: center;
}

.result-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.mock-file-upload,
.mock-sheet-selector,
.mock-data-preview {
  padding: 40px;
  text-align: center;
  background-color: #f5f7fa;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  color: #909399;
  font-size: 16px;
}

@media (max-width: 768px) {
  .wizard-footer {
    flex-direction: column;
  }
  
  .progress-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .result-actions {
    flex-direction: column;
  }
}
</style>