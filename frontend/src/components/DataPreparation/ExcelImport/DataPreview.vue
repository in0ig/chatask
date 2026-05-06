<template>
  <div class="data-preview">
    <div class="preview-header">
      <h4>数据预览</h4>
      <p class="description">请确认数据格式和字段类型</p>
    </div>
    
    <!-- 表名配置 -->
    <div class="table-config">
      <el-form :model="config" label-width="80px" size="default">
        <el-form-item label="表名:">
          <el-input
            v-model="config.tableName"
            placeholder="请输入表名"
            :maxlength="50"
            show-word-limit
            style="width: 300px"
          />
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 字段配置表格 -->
    <div class="field-config">
      <h5>字段配置</h5>
      <div class="field-list">
        <div v-for="(field, index) in fields" :key="field.name" class="field-item">
          <div class="field-name">{{ field.name }}</div>
          <div class="field-type">{{ field.dataType }}</div>
          <div class="field-samples">
            <span v-for="sample in field.sampleData.slice(0, 2)" :key="sample">{{ sample }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 数据预览表格 -->
    <div class="data-preview-section">
      <div class="preview-title">
        <h5>数据预览 (前 {{ Math.min(previewData.length, maxPreviewRows) }} 行)</h5>
        <div class="preview-stats">
          <span>总行数: {{ totalRows }}</span>
          <span>字段数: {{ fields.length }}</span>
        </div>
      </div>
      
      <div class="preview-table-wrapper">
        <table class="preview-table">
          <thead>
            <tr>
              <th v-for="field in fields" :key="field.name">
                {{ field.displayName || field.name }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in previewData.slice(0, maxPreviewRows)" :key="index">
              <td v-for="field in fields" :key="field.name">
                {{ formatCellValue(row[field.name], field.dataType) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- 数据质量报告 -->
    <div v-if="qualityReport" class="quality-report">
      <h5>数据质量报告</h5>
      <div class="quality-stats">
        <div class="stat-item">
          <span class="stat-label">空值率:</span>
          <span class="stat-value">{{ qualityReport.nullRate }}%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">重复行:</span>
          <span class="stat-value">{{ qualityReport.duplicateRows }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">数据完整性:</span>
          <span class="stat-value">{{ qualityReport.completeness }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// 字段配置接口
export interface FieldConfig {
  name: string
  displayName: string
  dataType: string
  nullable: boolean
  sampleData: any[]
  originalType?: string
}

// 表配置接口
export interface TableConfig {
  tableName: string
  description?: string
}

// 数据质量报告接口
export interface QualityReport {
  nullRate: number
  duplicateRows: number
  completeness: number
  issues: Array<{
    field: string
    message: string
    severity: 'warning' | 'error'
  }>
}

// Props
interface Props {
  previewData: Record<string, any>[]
  fields: FieldConfig[]
  totalRows: number
  config?: TableConfig
  maxPreviewRows?: number
}

const props = withDefaults(defineProps<Props>(), {
  previewData: () => [],
  fields: () => [],
  totalRows: 0,
  config: () => ({ tableName: '' }),
  maxPreviewRows: 10
})

// Emits
interface Emits {
  (e: 'update:fields', fields: FieldConfig[]): void
  (e: 'update:config', config: TableConfig): void
  (e: 'field-type-changed', field: FieldConfig, oldType: string): void
  (e: 'validation-error', field: string, message: string): void
}

const emit = defineEmits<Emits>()

// 响应式数据
const fields = ref<FieldConfig[]>([...props.fields])
const config = ref<TableConfig>({ ...props.config })
const qualityReport = ref<QualityReport | null>(null)

// 数据类型选项
const dataTypes = [
  { label: 'VARCHAR', value: 'VARCHAR' },
  { label: 'INTEGER', value: 'INTEGER' },
  { label: 'DECIMAL', value: 'DECIMAL' },
  { label: 'DATE', value: 'DATE' },
  { label: 'DATETIME', value: 'DATETIME' },
  { label: 'BOOLEAN', value: 'BOOLEAN' },
  { label: 'TEXT', value: 'TEXT' },
  { label: 'JSON', value: 'JSON' }
]

// 监听字段变化
watch(fields, (newFields) => {
  emit('update:fields', newFields)
}, { deep: true })

// 监听配置变化
watch(config, (newConfig) => {
  emit('update:config', newConfig)
}, { deep: true })

// 监听外部字段变化
watch(() => props.fields, (newFields) => {
  fields.value = [...newFields]
}, { deep: true })

// 监听外部配置变化
watch(() => props.config, (newConfig) => {
  config.value = { ...newConfig }
}, { deep: true })

// 计算属性
const getFieldByName = (name: string) => {
  return fields.value.find(field => field.name === name)
}

// 获取类型标签颜色
const getTypeTagType = (dataType?: string) => {
  const typeMap: Record<string, string> = {
    'VARCHAR': '',
    'INTEGER': 'success',
    'DECIMAL': 'warning',
    'DATE': 'info',
    'DATETIME': 'info',
    'BOOLEAN': 'danger',
    'TEXT': '',
    'JSON': 'warning'
  }
  return typeMap[dataType || ''] || ''
}

// 格式化单元格值
const formatCellValue = (value: any, dataType: string): string => {
  if (value === null || value === undefined) {
    return 'NULL'
  }
  
  if (value === '') {
    return '(空字符串)'
  }
  
  // 根据数据类型格式化显示
  switch (dataType) {
    case 'DATE':
      return new Date(value).toLocaleDateString()
    case 'DATETIME':
      return new Date(value).toLocaleString()
    case 'DECIMAL':
      return parseFloat(value).toFixed(2)
    case 'BOOLEAN':
      return value ? '是' : '否'
    default:
      return String(value)
  }
}

// 验证字段名
const validateFieldName = (field: FieldConfig) => {
  const name = field.name.trim()
  
  if (!name) {
    emit('validation-error', field.name, '字段名不能为空')
    return false
  }
  
  // 检查字段名是否重复
  const duplicates = fields.value.filter(f => f.name === name)
  if (duplicates.length > 1) {
    emit('validation-error', field.name, '字段名不能重复')
    return false
  }
  
  // 检查字段名格式（只允许字母、数字、下划线）
  const namePattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/
  if (!namePattern.test(name)) {
    emit('validation-error', field.name, '字段名只能包含字母、数字和下划线，且不能以数字开头')
    return false
  }
  
  return true
}

// 字段类型变更处理
const onTypeChange = (field: FieldConfig) => {
  const oldType = field.originalType || field.dataType
  emit('field-type-changed', field, oldType)
  
  // 验证类型转换是否合理
  validateTypeConversion(field, oldType)
}

// 验证类型转换
const validateTypeConversion = (field: FieldConfig, oldType: string) => {
  const sampleValues = field.sampleData.filter(v => v !== null && v !== undefined && v !== '')
  
  if (sampleValues.length === 0) return
  
  let conversionIssues = 0
  
  sampleValues.forEach(value => {
    if (!canConvertToType(value, field.dataType)) {
      conversionIssues++
    }
  })
  
  if (conversionIssues > 0) {
    const rate = Math.round((conversionIssues / sampleValues.length) * 100)
    ElMessage.warning(`字段 ${field.name} 有 ${rate}% 的数据可能无法转换为 ${field.dataType} 类型`)
  }
}

// 检查值是否可以转换为指定类型
const canConvertToType = (value: any, targetType: string): boolean => {
  switch (targetType) {
    case 'INTEGER':
      return !isNaN(parseInt(value)) && isFinite(value)
    case 'DECIMAL':
      return !isNaN(parseFloat(value)) && isFinite(value)
    case 'DATE':
    case 'DATETIME':
      return !isNaN(Date.parse(value))
    case 'BOOLEAN':
      return ['true', 'false', '1', '0', 'yes', 'no'].includes(String(value).toLowerCase())
    default:
      return true
  }
}

// 重置字段类型
const resetFieldType = (field: FieldConfig, index: number) => {
  if (field.originalType) {
    const oldType = field.dataType
    field.dataType = field.originalType
    emit('field-type-changed', field, oldType)
    ElMessage.success(`已重置字段 ${field.name} 的类型为 ${field.originalType}`)
  }
}

// 生成数据质量报告
const generateQualityReport = () => {
  if (props.previewData.length === 0 || fields.value.length === 0) {
    return
  }
  
  const totalCells = props.previewData.length * fields.value.length
  let nullCells = 0
  let duplicateRows = 0
  const issues: QualityReport['issues'] = []
  
  // 计算空值率
  props.previewData.forEach(row => {
    fields.value.forEach(field => {
      const value = row[field.name]
      if (value === null || value === undefined || value === '') {
        nullCells++
      }
    })
  })
  
  // 检查重复行（简化版本，只检查前几行）
  const rowHashes = new Set()
  props.previewData.forEach(row => {
    const hash = JSON.stringify(row)
    if (rowHashes.has(hash)) {
      duplicateRows++
    } else {
      rowHashes.add(hash)
    }
  })
  
  // 检查字段质量问题
  fields.value.forEach(field => {
    const values = props.previewData.map(row => row[field.name])
    const nonNullValues = values.filter(v => v !== null && v !== undefined && v !== '')
    
    // 检查数据类型一致性
    if (field.dataType === 'INTEGER' || field.dataType === 'DECIMAL') {
      const invalidNumbers = nonNullValues.filter(v => isNaN(Number(v)))
      if (invalidNumbers.length > 0) {
        issues.push({
          field: field.name,
          message: `包含 ${invalidNumbers.length} 个非数字值`,
          severity: 'warning'
        })
      }
    }
    
    // 检查日期格式
    if (field.dataType === 'DATE' || field.dataType === 'DATETIME') {
      const invalidDates = nonNullValues.filter(v => isNaN(Date.parse(v)))
      if (invalidDates.length > 0) {
        issues.push({
          field: field.name,
          message: `包含 ${invalidDates.length} 个无效日期`,
          severity: 'warning'
        })
      }
    }
  })
  
  const nullRate = Math.round((nullCells / totalCells) * 100)
  const completeness = 100 - nullRate
  
  qualityReport.value = {
    nullRate,
    duplicateRows,
    completeness,
    issues
  }
}

// 组件挂载时生成质量报告
onMounted(() => {
  generateQualityReport()
})

// 监听数据变化重新生成报告
watch([() => props.previewData, fields], () => {
  generateQualityReport()
}, { deep: true })

// 暴露方法给父组件
defineExpose({
  fields: computed(() => fields.value),
  config: computed(() => config.value),
  qualityReport: computed(() => qualityReport.value),
  validateAllFields: () => {
    return fields.value.every(field => validateFieldName(field))
  }
})
</script>

<style scoped>
.data-preview {
  width: 100%;
}

.preview-header {
  margin-bottom: 20px;
}

.preview-header h4 {
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

.table-config {
  margin-bottom: 24px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.field-config {
  margin-bottom: 24px;
}

.field-config h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.field-name {
  font-weight: 500;
  min-width: 100px;
}

.field-type {
  color: #409eff;
  font-size: 12px;
  min-width: 80px;
}

.field-samples {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.preview-table-wrapper {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: auto;
  max-height: 400px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
}

.preview-table th,
.preview-table td {
  border: 1px solid #e4e7ed;
  padding: 8px 12px;
  text-align: left;
}

.preview-table th {
  background-color: #fafafa;
  font-weight: 600;
}

.preview-table td {
  font-size: 12px;
}

.data-preview-section {
  margin-bottom: 24px;
}

.preview-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title h5 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.preview-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.preview-table {
  width: 100%;
}

.preview-table :deep(.el-table__header) {
  background-color: #fafafa;
}

.column-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.type-tag {
  font-size: 10px;
  height: 16px;
  line-height: 14px;
}

.null-value {
  color: #c0c4cc;
  font-style: italic;
}

.empty-value {
  color: #f56c6c;
  font-style: italic;
}

.quality-report {
  padding: 16px;
  background-color: #f0f9ff;
  border-radius: 8px;
  border: 1px solid #b3d8ff;
}

.quality-report h5 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.quality-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  color: #606266;
}

.stat-value {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}

.completeness-bar {
  width: 60px;
}

.quality-issues {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-alert {
  margin: 0;
}

.issue-alert :deep(.el-alert__title) {
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .quality-stats {
    flex-direction: column;
    gap: 12px;
  }
  
  .stat-item {
    justify-content: space-between;
  }
}
</style>