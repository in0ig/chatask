<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="120px"
    class="data-source-form"
    @submit.prevent="handleSave"
  >
    <!-- 数据源类型 -->
    <el-form-item label="数据源类型" prop="sourceType">
      <el-select
        v-model="form.sourceType"
        placeholder="请选择数据源类型"
        @change="onSourceTypeChange"
        :disabled="isEditing"
      >
        <el-option label="数据库" value="DATABASE" />
        <el-option label="Excel 文件" value="FILE" />
      </el-select>
    </el-form-item>

    <!-- 数据源名称 -->
    <el-form-item label="数据源名称" prop="name">
      <el-input
        v-model="form.name"
        placeholder="请输入数据源名称"
        :disabled="isEditing"
        clearable
      />
    </el-form-item>

    <!-- 数据库类型 -->
    <el-form-item 
      v-if="form.sourceType === 'DATABASE'"
      label="数据库类型" 
      prop="dbType"
    >
      <el-select
        v-model="form.dbType"
        placeholder="请选择数据库类型"
        @change="onDbTypeChange"
        :disabled="isEditing"
      >
        <el-option
          v-for="type in dbTypes"
          :key="type.value"
          :label="type.label"
          :value="type.value"
        />
      </el-select>
    </el-form-item>

    <!-- 主机地址 -->
    <el-form-item 
      v-if="form.sourceType === 'DATABASE'"
      label="主机地址" 
      prop="host"
    >
      <el-input
        v-model="form.host"
        placeholder="请输入主机地址"
        clearable
      />
    </el-form-item>

    <!-- 端口号 -->
    <el-form-item 
      v-if="form.sourceType === 'DATABASE'"
      label="端口号" 
      prop="port"
    >
      <el-input-number
        v-model="form.port"
        :min="1"
        :max="65535"
        placeholder="请输入端口号"
        style="width: 100%"
      />
    </el-form-item>

    <!-- 数据库名称 -->
    <el-form-item 
      v-if="form.sourceType === 'DATABASE'"
      label="数据库名称" 
      prop="databaseName"
    >
      <el-input
        v-model="form.databaseName"
        placeholder="请输入数据库名称"
        clearable
      />
    </el-form-item>

    <!-- SQL Server 认证方式 -->
    <el-form-item
      v-if="form.sourceType === 'DATABASE' && form.dbType === 'SQLSERVER'"
      label="认证方式"
      prop="authType"
    >
      <el-radio-group
        v-model="form.authType"
        @change="onAuthTypeChange"
      >
        <el-radio value="SQL_AUTH">SQL Server 身份验证</el-radio>
        <el-radio value="WINDOWS_AUTH">Windows 身份验证</el-radio>
      </el-radio-group>
    </el-form-item>

    <!-- 用户名 -->
    <el-form-item
      v-if="shouldShowCredentials"
      label="用户名"
      prop="username"
    >
      <el-input
        v-model="form.username"
        placeholder="请输入用户名"
        clearable
      />
    </el-form-item>

    <!-- 密码 -->
    <el-form-item
      v-if="shouldShowCredentials"
      label="密码"
      prop="password"
    >
      <el-input
        v-model="form.password"
        type="password"
        placeholder="请输入密码"
        clearable
        show-password
      />
    </el-form-item>

    <!-- 域名 -->
    <el-form-item
      v-if="form.sourceType === 'DATABASE' && form.dbType === 'SQLSERVER' && form.authType === 'WINDOWS_AUTH'"
      label="域名"
      prop="domain"
    >
      <el-input
        v-model="form.domain"
        placeholder="请输入域名（可选）"
        clearable
      />
    </el-form-item>

    <!-- Excel 文件路径 -->
    <el-form-item 
      v-if="form.sourceType === 'FILE'"
      label="文件路径" 
      prop="filePath"
    >
      <el-input
        v-model="form.filePath"
        placeholder="请输入 Excel 文件路径"
        clearable
        readonly
      >
        <template #append>
          <el-button @click="handleSelectFile">选择文件</el-button>
        </template>
      </el-input>
    </el-form-item>

    <!-- 描述 -->
    <el-form-item label="描述">
      <el-input
        v-model="form.description"
        type="textarea"
        placeholder="请输入描述信息"
        :rows="3"
        clearable
      />
    </el-form-item>

    <!-- 连接测试组件 -->
    <ConnectionTest
      v-if="form.sourceType === 'DATABASE'"
      :config="connectionConfig"
      @test-result="handleConnectionResult"
    />

    <!-- 操作按钮 -->
    <el-form-item>
      <el-button @click="handleCancel">取消</el-button>
      <el-button
        type="primary"
        :disabled="!isFormValid"
        @click="handleSave"
      >
        保存
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import ConnectionTest from './ConnectionTest.vue'
import type { DataSource } from '@/store/modules/dataPreparation'

// 定义组件 props
interface Props {
  mode?: 'create' | 'edit'
  initialData?: DataSource | null
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'create',
  initialData: null
})

// 定义组件 emits
const emit = defineEmits<{
  submit: [data: DataSourceFormData]
  cancel: []
}>()

// 数据源表单数据接口
interface DataSourceFormData {
  id?: string
  name: string
  sourceType: 'DATABASE' | 'FILE'
  dbType?: 'MYSQL' | 'SQLSERVER' | 'POSTGRESQL' | 'CLICKHOUSE'
  host?: string
  port?: number
  databaseName?: string
  authType?: 'SQL_AUTH' | 'WINDOWS_AUTH'
  username?: string
  password?: string
  domain?: string
  filePath?: string
  description?: string
}

// 连接测试结果接口
interface ConnectionTestResult {
  success: boolean
  message: string
  latencyMs?: number
}

// 定义数据库类型选项
const dbTypes = [
  { value: 'MYSQL', label: 'MySQL' },
  { value: 'SQLSERVER', label: 'SQL Server' },
  { value: 'POSTGRESQL', label: 'PostgreSQL' },
  { value: 'CLICKHOUSE', label: 'ClickHouse' }
]

// 默认端口映射
const defaultPorts: Record<string, number> = {
  MYSQL: 3306,
  SQLSERVER: 1433,
  POSTGRESQL: 5432,
  CLICKHOUSE: 8123
}

// 表单数据
const form = ref<DataSourceFormData>({
  name: '',
  sourceType: 'DATABASE',
  dbType: 'MYSQL',
  host: '',
  port: 3306,
  databaseName: '',
  authType: 'SQL_AUTH',
  username: '',
  password: '',
  domain: '',
  filePath: '',
  description: ''
})

// 表单引用
const formRef = ref()

// 是否为编辑模式
const isEditing = computed(() => props.mode === 'edit')

// 是否显示凭据字段
const shouldShowCredentials = computed(() => {
  if (form.value.sourceType !== 'DATABASE') return false
  if (form.value.dbType === 'SQLSERVER') {
    return form.value.authType === 'SQL_AUTH'
  }
  return true
})

// 连接配置（用于传递给 ConnectionTest 组件）
const connectionConfig = computed(() => ({
  sourceType: form.value.sourceType,
  dbType: form.value.dbType,
  host: form.value.host,
  port: form.value.port,
  databaseName: form.value.databaseName,
  authType: form.value.authType,
  username: form.value.username,
  password: form.value.password,
  domain: form.value.domain
}))

// 表单验证规则
const rules = ref({
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  sourceType: [
    { required: true, message: '请选择数据源类型', trigger: 'change' }
  ],
  dbType: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' },
    { 
      pattern: /^(?:[a-zA-Z0-9.-]+|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/, 
      message: '请输入有效的主机地址', 
      trigger: 'blur' 
    }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口号必须在 1-65535 之间', trigger: 'blur' }
  ],
  databaseName: [
    { required: true, message: '请输入数据库名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  domain: [
    { required: false, message: '请输入有效的域名', trigger: 'blur', pattern: /^[a-zA-Z0-9.-]*$/ }
  ],
  filePath: [
    { required: true, message: '请选择 Excel 文件', trigger: 'blur' }
  ]
})

// 表单是否有效
const isFormValid = computed(() => {
  if (!form.value.name) return false
  
  if (form.value.sourceType === 'DATABASE') {
    if (!form.value.dbType || !form.value.host || !form.value.port || !form.value.databaseName) {
      return false
    }
    
    if (shouldShowCredentials.value) {
      if (!form.value.username || !form.value.password) {
        return false
      }
    }
  } else if (form.value.sourceType === 'FILE') {
    if (!form.value.filePath) return false
  }
  
  return true
})

// 监听数据源类型变化
const onSourceTypeChange = () => {
  if (form.value.sourceType === 'DATABASE') {
    form.value.filePath = ''
    form.value.dbType = 'MYSQL'
    form.value.port = defaultPorts.MYSQL
    form.value.authType = 'SQL_AUTH'
  } else {
    form.value.dbType = undefined
    form.value.host = ''
    form.value.port = undefined
    form.value.databaseName = ''
    form.value.username = ''
    form.value.password = ''
    form.value.domain = ''
    form.value.authType = undefined
  }
}

// 监听数据库类型变化
const onDbTypeChange = () => {
  if (form.value.dbType && defaultPorts[form.value.dbType]) {
    form.value.port = defaultPorts[form.value.dbType]
  }
  
  if (form.value.dbType !== 'SQLSERVER') {
    form.value.authType = 'SQL_AUTH'
    form.value.domain = ''
  }
}

// 监听认证方式变化
const onAuthTypeChange = () => {
  if (form.value.authType === 'WINDOWS_AUTH') {
    form.value.username = ''
    form.value.password = ''
  } else {
    form.value.domain = ''
  }
}

// 处理文件选择
const handleSelectFile = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      form.value.filePath = file.name
    }
  }
  input.click()
}

// 处理连接测试结果
const handleConnectionResult = (result: ConnectionTestResult) => {
  if (result.success) {
    ElMessage.success(`连接测试成功${result.latencyMs ? `（${result.latencyMs}ms）` : ''}`)
  } else {
    ElMessage.error(`连接测试失败：${result.message}`)
  }
}

// 处理保存
const handleSave = async () => {
  try {
    const isValid = await formRef.value?.validate()
    if (!isValid) {
      ElMessage.error('请先填写所有必填字段')
      return
    }

    emit('submit', { ...form.value })
    ElMessage.success(isEditing.value ? '数据源更新成功' : '数据源创建成功')
  } catch (error) {
    console.error('表单验证失败:', error)
    ElMessage.error('请检查表单填写是否正确')
  }
}

// 处理取消
const handleCancel = () => {
  emit('cancel')
}

// 重置表单
const resetForm = () => {
  form.value = {
    name: '',
    sourceType: 'DATABASE',
    dbType: 'MYSQL',
    host: '',
    port: 3306,
    databaseName: '',
    authType: 'SQL_AUTH',
    username: '',
    password: '',
    domain: '',
    filePath: '',
    description: ''
  }
  
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

// 初始化表单数据
const initForm = () => {
  if (props.initialData) {
    form.value = {
      ...props.initialData,
      port: props.initialData.port || defaultPorts[props.initialData.dbType || 'MYSQL'],
      authType: props.initialData.authType || 'SQL_AUTH'
    }
  }
}

// 监听 props 变化
watch(() => props.initialData, initForm, { immediate: true })

// 暴露给父组件的方法
defineExpose({
  resetForm,
  validate: () => formRef.value?.validate()
})
</script>

<style scoped>
.data-source-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-source-form {
    padding: 10px;
    margin: 0;
  }
  
  .el-form-item {
    margin-bottom: 12px;
  }
  
  .el-form-item__label {
    width: 100px !important;
  }
}
</style>