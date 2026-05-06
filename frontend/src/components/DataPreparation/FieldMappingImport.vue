<template>
  <div class="field-mapping-import">
    <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
      <el-alert
        title="导入字段映射"
        description="支持从Excel或CSV文件导入字段映射配置"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <!-- 导入模式选择 -->
      <el-form-item label="导入模式" prop="import_mode">
        <el-radio-group v-model="formData.import_mode">
          <el-radio label="merge">合并模式</el-radio>
          <el-radio label="replace">替换模式</el-radio>
        </el-radio-group>
        <div class="mode-description">
          <p v-if="formData.import_mode === 'merge'" class="description-text">
            合并模式：保留现有映射，只更新导入文件中存在的字段映射
          </p>
          <p v-if="formData.import_mode === 'replace'" class="description-text">
            替换模式：清空现有映射，完全使用导入文件中的映射配置
          </p>
        </div>
      </el-form-item>

      <!-- 文件上传 -->
      <el-form-item label="选择文件" prop="file">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          :accept="'.xlsx,.xls,.csv'"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :before-upload="beforeUpload"
        >
          <el-button type="primary" :icon="Upload">选择文件</el-button>
          <template #tip>
            <div class="el-upload__tip">
              支持 .xlsx, .xls, .csv 格式文件，文件大小不超过 10MB
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <!-- 文件格式说明 -->
      <el-form-item label="格式说明">
        <el-collapse>
          <el-collapse-item title="Excel/CSV文件格式要求" name="format">
            <div class="format-description">
              <p><strong>必需列：</strong></p>
              <ul>
                <li>field_name: 字段名称</li>
                <li>business_name: 业务名称</li>
              </ul>
              
              <p><strong>可选列：</strong></p>
              <ul>
                <li>business_meaning: 业务含义</li>
                <li>dictionary_name: 字典名称</li>
                <li>value_range: 取值范围</li>
                <li>is_required: 是否必填 (true/false)</li>
                <li>default_value: 默认值</li>
              </ul>
              
              <p><strong>示例：</strong></p>
              <el-table :data="exampleData" border size="small" style="margin-top: 8px;">
                <el-table-column prop="field_name" label="field_name" width="100" />
                <el-table-column prop="business_name" label="business_name" width="100" />
                <el-table-column prop="business_meaning" label="business_meaning" width="120" />
                <el-table-column prop="dictionary_name" label="dictionary_name" width="100" />
                <el-table-column prop="is_required" label="is_required" width="100" />
              </el-table>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form-item>

      <!-- 预览导入数据 -->
      <div v-if="previewData.length > 0" class="preview-section">
        <h4>导入数据预览</h4>
        <el-alert
          :title="`将导入 ${previewData.length} 条字段映射记录`"
          type="success"
          show-icon
          :closable="false"
          style="margin-bottom: 12px;"
        />
        
        <el-table :data="previewData.slice(0, 10)" border size="small" max-height="300">
          <el-table-column prop="field_name" label="字段名称" width="120" />
          <el-table-column prop="business_name" label="业务名称" width="120" />
          <el-table-column prop="business_meaning" label="业务含义" min-width="150" />
          <el-table-column prop="dictionary_name" label="字典名称" width="100" />
          <el-table-column prop="is_required" label="必填" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_required ? 'danger' : 'info'" size="small">
                {{ row.is_required ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        
        <div v-if="previewData.length > 10" class="more-data-tip">
          还有 {{ previewData.length - 10 }} 条记录未显示...
        </div>
      </div>

      <!-- 导入统计 -->
      <div v-if="importStats" class="import-stats">
        <h4>导入统计</h4>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-statistic title="总记录数" :value="importStats.total" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="有效记录" :value="importStats.valid" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="无效记录" :value="importStats.invalid" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="重复记录" :value="importStats.duplicate" />
          </el-col>
        </el-row>
      </div>
    </el-form>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleSubmit" 
        :loading="loading"
        :disabled="previewData.length === 0 || (importStats && importStats.valid === 0)"
      >
        确定导入
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import type { FormInstance, FormRules, UploadFile, UploadFiles } from 'element-plus'

// Props
interface Props {
  tableId: string
  loading: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  submit: [importData: any]
  cancel: []
}>()

// 表单引用
const formRef = ref<FormInstance>()
const uploadRef = ref()

// 表单数据
const formData = reactive({
  import_mode: 'merge',
  file: null as File | null
})

// 验证规则
const rules: FormRules = {
  import_mode: [
    { required: true, message: '请选择导入模式', trigger: 'change' }
  ],
  file: [
    { required: true, message: '请选择导入文件', trigger: 'change' }
  ]
}

// 预览数据
const previewData = ref<any[]>([])
const importStats = ref<any>(null)

// 示例数据
const exampleData = [
  {
    field_name: 'user_id',
    business_name: '用户ID',
    business_meaning: '用户唯一标识',
    dictionary_name: '',
    is_required: 'true'
  },
  {
    field_name: 'status',
    business_name: '状态',
    business_meaning: '用户状态',
    dictionary_name: '用户状态字典',
    is_required: 'false'
  }
]

// 方法
const handleFileChange = (file: UploadFile, files: UploadFiles) => {
  if (file.raw) {
    formData.file = file.raw
    parseFile(file.raw)
  }
}

const handleFileRemove = () => {
  formData.file = null
  previewData.value = []
  importStats.value = null
}

const beforeUpload = (file: File) => {
  const isValidType = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                      'application/vnd.ms-excel', 
                      'text/csv'].includes(file.type)
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isValidType) {
    ElMessage.error('只支持 Excel 和 CSV 格式文件!')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  return false // 阻止自动上传
}

const parseFile = async (file: File) => {
  try {
    // 模拟文件解析
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 模拟解析结果
    const mockData = [
      {
        field_name: 'user_id',
        business_name: '用户ID',
        business_meaning: '用户的唯一标识符',
        dictionary_name: '',
        value_range: '',
        is_required: true,
        default_value: '',
        status: 'valid'
      },
      {
        field_name: 'username',
        business_name: '用户名',
        business_meaning: '用户登录名称',
        dictionary_name: '',
        value_range: '3-20字符',
        is_required: true,
        default_value: '',
        status: 'valid'
      },
      {
        field_name: 'status',
        business_name: '状态',
        business_meaning: '用户账户状态',
        dictionary_name: '用户状态字典',
        value_range: '0-2',
        is_required: false,
        default_value: '1',
        status: 'valid'
      },
      {
        field_name: 'invalid_field',
        business_name: '',
        business_meaning: '',
        dictionary_name: '',
        value_range: '',
        is_required: false,
        default_value: '',
        status: 'invalid'
      }
    ]
    
    previewData.value = mockData
    
    // 计算统计信息
    const total = mockData.length
    const valid = mockData.filter(item => item.status === 'valid').length
    const invalid = mockData.filter(item => item.status === 'invalid').length
    const duplicate = mockData.filter(item => item.status === 'duplicate').length
    
    importStats.value = {
      total,
      valid,
      invalid,
      duplicate
    }
    
    ElMessage.success('文件解析完成')
  } catch (error: any) {
    console.error('文件解析失败:', error)
    ElMessage.error('文件解析失败: ' + (error.message || '未知错误'))
  }
}

const getStatusType = (status: string) => {
  const typeMap: Record<string, string> = {
    'valid': 'success',
    'invalid': 'danger',
    'duplicate': 'warning'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status: string) => {
  const textMap: Record<string, string> = {
    'valid': '有效',
    'invalid': '无效',
    'duplicate': '重复'
  }
  return textMap[status] || '未知'
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    
    if (!formData.file) {
      ElMessage.error('请选择导入文件')
      return
    }
    
    if (previewData.value.length === 0) {
      ElMessage.error('没有可导入的数据')
      return
    }
    
    if (importStats.value && importStats.value.valid === 0) {
      ElMessage.error('没有有效的导入数据')
      return
    }

    const submitData = {
      table_id: props.tableId,
      import_mode: formData.import_mode,
      mappings: previewData.value.filter(item => item.status === 'valid')
    }

    emit('submit', submitData)
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped lang="scss">
.field-mapping-import {
  .mode-description {
    margin-top: 8px;
    
    .description-text {
      margin: 0;
      font-size: 12px;
      color: #909399;
    }
  }

  .format-description {
    font-size: 14px;
    
    p {
      margin: 8px 0;
    }
    
    ul {
      margin: 8px 0;
      padding-left: 20px;
      
      li {
        margin: 4px 0;
      }
    }
  }

  .preview-section {
    margin-top: 20px;
    
    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
    }
    
    .more-data-tip {
      text-align: center;
      padding: 8px;
      color: #909399;
      font-size: 12px;
    }
  }

  .import-stats {
    margin-top: 20px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 4px;
    
    h4 {
      margin: 0 0 16px 0;
      color: #303133;
      font-size: 16px;
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid #e4e7ed;
  }
}

:deep(.el-upload__tip) {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>