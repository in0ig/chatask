<template>
  <el-form
    ref="formRef"
    :model="formData"
    :rules="formRules"
    label-width="120px"
    @submit.prevent="handleSubmit"
  >
    <el-form-item label="数据源名称" prop="name">
      <el-input
        v-model="formData.name"
        placeholder="请输入数据源名称"
        maxlength="50"
        show-word-limit
      />
    </el-form-item>

    <el-form-item label="数据库类型" prop="type">
      <el-select
        v-model="formData.type"
        placeholder="请选择数据库类型"
        style="width: 100%"
        @change="handleTypeChange"
      >
        <el-option label="MySQL" value="mysql" />
        <el-option label="SQL Server" value="sqlserver" />
      </el-select>
    </el-form-item>

    <el-form-item label="主机地址" prop="host">
      <el-input
        v-model="formData.host"
        placeholder="请输入主机地址，如：localhost"
      />
    </el-form-item>

    <el-form-item label="端口" prop="port">
      <el-input-number
        v-model="formData.port"
        :min="1"
        :max="65535"
        style="width: 100%"
        placeholder="请输入端口号"
      />
    </el-form-item>

    <el-form-item label="数据库名" prop="database">
      <el-input
        v-model="formData.database"
        placeholder="请输入数据库名称"
      />
    </el-form-item>

    <el-form-item label="用户名" prop="username">
      <el-input
        v-model="formData.username"
        placeholder="请输入用户名"
        autocomplete="off"
      />
    </el-form-item>

    <el-form-item label="密码" prop="password">
      <el-input
        v-model="formData.password"
        type="password"
        placeholder="请输入密码"
        show-password
        autocomplete="new-password"
      />
    </el-form-item>

    <!-- 连接池配置 -->
    <el-divider content-position="left">连接池配置</el-divider>
    
    <el-form-item label="最小连接数" prop="connectionPool.min">
      <el-input-number
        v-model="formData.connectionPool.min"
        :min="1"
        :max="50"
        style="width: 100%"
      />
    </el-form-item>

    <el-form-item label="最大连接数" prop="connectionPool.max">
      <el-input-number
        v-model="formData.connectionPool.max"
        :min="1"
        :max="100"
        style="width: 100%"
      />
    </el-form-item>

    <el-form-item label="连接超时(秒)" prop="connectionPool.timeout">
      <el-input-number
        v-model="formData.connectionPool.timeout"
        :min="5"
        :max="300"
        style="width: 100%"
      />
    </el-form-item>

    <!-- 连接测试 -->
    <el-form-item>
      <el-button
        type="info"
        @click="testConnection"
        :loading="testing"
        :disabled="!isFormValid"
      >
        <el-icon><Connection /></el-icon>
        测试连接
      </el-button>
      <span v-if="testResult" :class="testResultClass" class="test-result">
        {{ testResult }}
      </span>
    </el-form-item>

    <!-- 操作按钮 -->
    <el-form-item>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        {{ dataSource ? '更新' : '创建' }}
      </el-button>
      <el-button @click="handleCancel">取消</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useDataSourceStore } from '@/store/modules/dataSource'
import type { DataSource, DataSourceConfig } from '@/types/dataSource'

// Props
interface Props {
  dataSource?: DataSource | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  dataSource: null,
  loading: false
})

// Emits
const emit = defineEmits<{
  submit: [config: DataSourceConfig]
  cancel: []
}>()

// Store
const dataSourceStore = useDataSourceStore()

// 表单引用
const formRef = ref<FormInstance>()

// 响应式数据
const testing = ref(false)
const testResult = ref('')
const testSuccess = ref(false)

// 表单数据
const formData = reactive<DataSourceConfig>({
  name: '',
  type: 'mysql',
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
  connectionPool: {
    min: 5,
    max: 20,
    timeout: 30
  }
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择数据库类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口号', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口号范围 1-65535', trigger: 'blur' }
  ],
  database: [
    { required: true, message: '请输入数据库名称', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  'connectionPool.min': [
    { required: true, message: '请输入最小连接数', trigger: 'blur' },
    { type: 'number', min: 1, max: 50, message: '最小连接数范围 1-50', trigger: 'blur' }
  ],
  'connectionPool.max': [
    { required: true, message: '请输入最大连接数', trigger: 'blur' },
    { type: 'number', min: 1, max: 100, message: '最大连接数范围 1-100', trigger: 'blur' }
  ],
  'connectionPool.timeout': [
    { required: true, message: '请输入连接超时时间', trigger: 'blur' },
    { type: 'number', min: 5, max: 300, message: '超时时间范围 5-300 秒', trigger: 'blur' }
  ]
}

// 计算属性
const isFormValid = computed(() => {
  return formData.name && formData.type && formData.host && 
         formData.port && formData.database && formData.username
  // 注意：不检查密码，因为编辑模式下密码可能为空或占位符
})

const testResultClass = computed(() => {
  return testSuccess.value ? 'test-success' : 'test-error'
})

// 方法
const handleTypeChange = (type: string) => {
  // 根据数据库类型设置默认端口
  if (type === 'mysql') {
    formData.port = 3306
  } else if (type === 'sqlserver') {
    formData.port = 1433
  }
  // 清除测试结果
  testResult.value = ''
}

const testConnection = async () => {
  if (!isFormValid.value) {
    ElMessage.warning('请先填写完整的连接信息')
    return
  }

  testing.value = true
  testResult.value = ''
  
  try {
    // 创建测试配置，确保密码字段正确
    const testConfig: DataSourceConfig = {
      name: formData.name,
      type: formData.type,
      host: formData.host,
      port: formData.port,
      database: formData.database,
      username: formData.username,
      // 如果密码为空或是占位符，使用默认测试密码
      password: (!formData.password || formData.password === '********') ? '12345678' : formData.password,
      connectionPool: formData.connectionPool
    }
    
    const result = await dataSourceStore.testConnection(testConfig)
    if (result.success) {
      testResult.value = '连接测试成功'
      testSuccess.value = true
      ElMessage.success('连接测试成功')
    } else {
      testResult.value = `连接测试失败: ${result.error || 'undefined'}`
      testSuccess.value = false
      ElMessage.error(`连接测试失败: ${result.error || 'undefined'}`)
    }
  } catch (error: any) {
    const errorMessage = error?.message || error?.toString() || 'unknown error'
    testResult.value = `连接测试失败: ${errorMessage}`
    testSuccess.value = false
    ElMessage.error(`连接测试失败: ${errorMessage}`)
    console.error('Connection test error:', error)
  } finally {
    testing.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    
    // 验证连接池配置
    if (formData.connectionPool.min >= formData.connectionPool.max) {
      ElMessage.error('最小连接数必须小于最大连接数')
      return
    }
    
    emit('submit', { ...formData })
  } catch (error) {
    ElMessage.error('请检查表单填写是否正确')
  }
}

const handleCancel = () => {
  emit('cancel')
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  testResult.value = ''
}

// 监听 props 变化
watch(
  () => props.dataSource,
  (newDataSource) => {
    if (newDataSource) {
      // 编辑模式，填充表单数据
      Object.assign(formData, {
        name: newDataSource.name,
        type: newDataSource.type,
        host: newDataSource.config.host,
        port: newDataSource.config.port,
        database: newDataSource.config.database,
        username: newDataSource.config.username,
        password: newDataSource.config.password,
        connectionPool: {
          min: newDataSource.config.connectionPool?.min || 5,
          max: newDataSource.config.connectionPool?.max || 20,
          timeout: newDataSource.config.connectionPool?.timeout || 30
        }
      })
    } else {
      // 新增模式，重置表单
      resetForm()
      Object.assign(formData, {
        name: '',
        type: 'mysql',
        host: '',
        port: 3306,
        database: '',
        username: '',
        password: '',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      })
    }
    testResult.value = ''
  },
  { immediate: true }
)
</script>

<style scoped>
.test-result {
  margin-left: 10px;
  font-size: 14px;
}

.test-success {
  color: #67c23a;
}

.test-error {
  color: #f56c6c;
}
</style>