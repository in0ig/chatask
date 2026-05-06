<template>
  <div class="data-sources-container">
    <div class="header">
      <h1>数据源管理</h1>
      <el-button type="primary" @click="openUploadModal">上传新数据源</el-button>
    </div>
    
    <div class="sources-list">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="3" :loading="loading" />
      </div>
      <div v-else-if="dataSources.length === 0" class="empty-state">
        <p>暂无数据源</p>
        <el-button type="primary" @click="openUploadModal">添加数据源</el-button>
      </div>
      <el-card 
        v-for="source in dataSources" 
        :key="source.id" 
        class="source-card"
      >
        <div class="source-header">
          <div class="source-info">
            <h3>{{ source.name }}</h3>
            <span class="source-type">
              {{ 
                source.db_type === 'MySQL' ? 'MySQL' : 
                source.db_type === 'SQL Server' ? 'SQL Server' : 
                source.db_type === 'PostgreSQL' ? 'PostgreSQL' : 
                source.db_type === 'ClickHouse' ? 'ClickHouse' : 
                source.source_type === 'FILE' ? 'Excel' : 
                source.type
              }}
            </span>
            <span v-if="source.connection_status" :class="['status-badge', source.connection_status === 'CONNECTED' ? 'connected' : 'disconnected']">
              {{ source.connection_status === 'CONNECTED' ? '已连接' : source.connection_status === 'FAILED' ? '连接失败' : '测试中' }}
            </span>
          </div>
          <div class="source-actions">
            <el-button 
              size="small" 
              :type="source.status ? 'success' : 'warning'"
              @click="toggleActive(source)"
            >
              {{ source.status ? '已激活' : '激活' }}
            </el-button>
            <el-button 
              size="small" 
              type="primary" 
              @click="editSource(source)"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="info" 
              @click="testConnection(source)"
              :disabled="loading"
            >
              测试连接
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteSource(source)"
            >
              删除
            </el-button>
          </div>
        </div>
        
        <div class="source-details">
          <p><strong>连接信息：</strong>{{ 
            source.source_type === 'FILE' ? 'Excel文件' : 
            source.connection_string || source.file_path 
          }}</p>
          <p><strong>创建时间：</strong>{{ formatDate(source.created_at) }}</p>
          <p><strong>更新时间：</strong>{{ formatDate(source.updated_at) }}</p>
          <p v-if="source.last_test_time"><strong>最后测试时间：</strong>{{ formatDate(source.last_test_time) }}</p>
        </div>
      </el-card>
    </div>
    
    <!-- 上传模态框 -->
    <el-dialog 
      v-model="uploadModalVisible" 
      title="上传数据源" 
      width="600px"
    >
      <div class="upload-content">
        <el-radio-group v-model="uploadType" class="upload-type">
          <el-radio value="excel">Excel 文件</el-radio>
          <el-radio value="mysql">MySQL 数据库</el-radio>
          <el-radio value="sqlserver">SQL Server 数据库</el-radio>
          <el-radio value="postgresql">PostgreSQL 数据库</el-radio>
          <el-radio value="clickhouse">ClickHouse 数据库</el-radio>
        </el-radio-group>
        
        <div v-if="uploadType === 'excel'" class="upload-excel">
          <el-upload
            drag
            action="#"
            accept=".xlsx,.xls"
            @change="handleExcelUpload"
          >
            <i class="el-icon-upload"></i>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">支持 .xlsx 和 .xls 格式</div>
            </template>
          </el-upload>
          <el-input 
            v-model="excelName" 
            placeholder="请输入数据源名称" 
            class="upload-name"
          />
        </div>
        
        <div v-else-if="uploadType === 'mysql'" class="upload-database">
          <el-form :model="mysqlForm" label-width="100px" class="database-form">
            <el-form-item label="主机地址">
              <el-input v-model="mysqlForm.host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="mysqlForm.port" placeholder="3306" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="mysqlForm.database" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="mysqlForm.username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="mysqlForm.password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="数据源名称">
              <el-input v-model="mysqlForm.name" />
            </el-form-item>
            <el-form-item>
              <el-button type="info" @click="testMysqlConnection" :disabled="loading">测试连接</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div v-else-if="uploadType === 'sqlserver'" class="upload-database">
          <el-form :model="sqlServerForm" label-width="100px" class="database-form">
            <el-form-item label="主机地址">
              <el-input v-model="sqlServerForm.host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="sqlServerForm.port" placeholder="1433" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="sqlServerForm.database" />
            </el-form-item>
            <el-form-item label="认证方式">
              <el-radio-group v-model="sqlServerForm.authType">
                <el-radio value="SQL_AUTH">SQL认证</el-radio>
                <el-radio value="WINDOWS_AUTH">Windows认证</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="用户名" v-if="sqlServerForm.authType === 'SQL_AUTH'">
              <el-input v-model="sqlServerForm.username" />
            </el-form-item>
            <el-form-item label="密码" v-if="sqlServerForm.authType === 'SQL_AUTH'">
              <el-input 
                v-model="sqlServerForm.password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="域名" v-if="sqlServerForm.authType === 'WINDOWS_AUTH'">
              <el-input v-model="sqlServerForm.domain" />
            </el-form-item>
            <el-form-item label="数据源名称">
              <el-input v-model="sqlServerForm.name" />
            </el-form-item>
            <el-form-item>
              <el-button type="info" @click="testSqlServerConnection" :disabled="loading">测试连接</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div v-else-if="uploadType === 'postgresql'" class="upload-database">
          <el-form :model="postgresqlForm" label-width="100px" class="database-form">
            <el-form-item label="主机地址">
              <el-input v-model="postgresqlForm.host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="postgresqlForm.port" placeholder="5432" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="postgresqlForm.database" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="postgresqlForm.username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="postgresqlForm.password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="数据源名称">
              <el-input v-model="postgresqlForm.name" />
            </el-form-item>
            <el-form-item>
              <el-button type="info" @click="testPostgresqlConnection" :disabled="loading">测试连接</el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <div v-else-if="uploadType === 'clickhouse'" class="upload-database">
          <el-form :model="clickhouseForm" label-width="100px" class="database-form">
            <el-form-item label="主机地址">
              <el-input v-model="clickhouseForm.host" placeholder="localhost" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="clickhouseForm.port" placeholder="8123" />
            </el-form-item>
            <el-form-item label="数据库名">
              <el-input v-model="clickhouseForm.database" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="clickhouseForm.username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="clickhouseForm.password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="数据源名称">
              <el-input v-model="clickhouseForm.name" />
            </el-form-item>
            <el-form-item>
              <el-button type="info" @click="testClickhouseConnection" :disabled="loading">测试连接</el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="uploadModalVisible = false">取消</el-button>
        <el-button type="primary" @click="submitUpload">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'


// 数据源列表（从后端API获取）
const dataSources = ref([])

// 上传模态框状态
const uploadModalVisible = ref(false)
const uploadType = ref('excel')
const excelName = ref('')

// MySQL 表单数据
const mysqlForm = reactive({
  host: 'localhost',
  port: '3306',
  database: '',
  username: '',
  password: '',
  name: ''
})

// SQL Server 表单数据
const sqlServerForm = reactive({
  host: 'localhost',
  port: '1433',
  database: '',
  authType: 'SQL_AUTH',
  username: '',
  password: '',
  domain: '',
  name: ''
})

// PostgreSQL 表单数据
const postgresqlForm = reactive({
  host: 'localhost',
  port: '5432',
  database: '',
  username: '',
  password: '',
  name: ''
})

// ClickHouse 表单数据
const clickhouseForm = reactive({
  host: 'localhost',
  port: '8123',
  database: '',
  username: '',
  password: '',
  name: ''
})

// 格式化日期
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// API调用函数
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 获取数据源列表
const getDataSources = async () => {
  const response = await api.get('/data-sources/')
  return response.data
}

// 创建数据源
const createDataSource = async (dataSource) => {
  const response = await api.post('/data-sources/', dataSource)
  return response.data
}

// 更新数据源
const updateDataSource = async (id, dataSource) => {
  const response = await api.put(`/data-sources/${id}/`, dataSource)
  return response.data
}

// 删除数据源
const deleteDataSource = async (id) => {
  await api.delete(`/data-sources/${id}/`)
}

// 测试数据源连接
const testConnection = async (source) => {
  try {
    loading.value = true
    
    // 准备测试数据
    const connectionData = {
      name: source.name,
      source_type: source.source_type,
      db_type: source.db_type,
      host: source.host,
      port: source.port,
      database_name: source.database_name,
      auth_type: source.auth_type,
      username: source.username,
      password: source.password,
      domain: source.domain,
      file_path: source.file_path,
      description: source.description
    }
    
    const result = await testConnection(connectionData)
    
    if (result.success) {
      ElMessage.success(`连接测试成功！延迟: ${result.latency_ms}ms`)
      // 更新本地数据源状态
      const index = dataSources.value.findIndex(s => s.id === source.id)
      if (index !== -1) {
        dataSources.value[index].connection_status = 'CONNECTED'
        dataSources.value[index].last_test_time = new Date().toISOString()
      }
    } else {
      ElMessage.error(`连接测试失败: ${result.message}`)
      // 更新本地数据源状态
      const index = dataSources.value.findIndex(s => s.id === source.id)
      if (index !== -1) {
        dataSources.value[index].connection_status = 'FAILED'
        dataSources.value[index].last_test_time = new Date().toISOString()
      }
    }
  } catch (error) {
    ElMessage.error('连接测试失败：' + error.message)
    // 更新本地数据源状态
    const index = dataSources.value.findIndex(s => s.id === source.id)
    if (index !== -1) {
      dataSources.value[index].connection_status = 'FAILED'
      dataSources.value[index].last_test_time = new Date().toISOString()
    }
  } finally {
    loading.value = false
  }
}

// 测试MySQL连接
const testMysqlConnection = async () => {
  if (!mysqlForm.host || !mysqlForm.port || !mysqlForm.database || !mysqlForm.username) {
    ElMessage.error('请填写所有必填字段')
    return
  }
  
  try {
    loading.value = true
    const result = await testConnection({
      name: mysqlForm.name,
      source_type: 'DATABASE',
      db_type: 'MySQL',
      host: mysqlForm.host,
      port: parseInt(mysqlForm.port),
      database_name: mysqlForm.database,
      username: mysqlForm.username,
      password: mysqlForm.password
    })
    
    if (result.success) {
      ElMessage.success(`MySQL连接测试成功！延迟: ${result.latency_ms}ms`)
    } else {
      ElMessage.error(`MySQL连接测试失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error('MySQL连接测试失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 测试SQL Server连接
const testSqlServerConnection = async () => {
  if (!sqlServerForm.host || !sqlServerForm.port || !sqlServerForm.database) {
    ElMessage.error('请填写所有必填字段')
    return
  }
  
  if (sqlServerForm.authType === 'SQL_AUTH' && (!sqlServerForm.username || !sqlServerForm.password)) {
    ElMessage.error('SQL认证方式下，用户名和密码为必填项')
    return
  }
  
  if (sqlServerForm.authType === 'WINDOWS_AUTH' && !sqlServerForm.domain) {
    ElMessage.error('Windows认证方式下，域名字段为必填项')
    return
  }
  
  try {
    loading.value = true
    const result = await testConnection({
      name: sqlServerForm.name,
      source_type: 'DATABASE',
      db_type: 'SQL Server',
      host: sqlServerForm.host,
      port: parseInt(sqlServerForm.port),
      database_name: sqlServerForm.database,
      auth_type: sqlServerForm.authType,
      username: sqlServerForm.username,
      password: sqlServerForm.password,
      domain: sqlServerForm.domain
    })
    
    if (result.success) {
      ElMessage.success(`SQL Server连接测试成功！延迟: ${result.latency_ms}ms`)
    } else {
      ElMessage.error(`SQL Server连接测试失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error('SQL Server连接测试失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 测试PostgreSQL连接
const testPostgresqlConnection = async () => {
  if (!postgresqlForm.host || !postgresqlForm.port || !postgresqlForm.database || !postgresqlForm.username) {
    ElMessage.error('请填写所有必填字段')
    return
  }
  
  try {
    loading.value = true
    const result = await testConnection({
      name: postgresqlForm.name,
      source_type: 'DATABASE',
      db_type: 'PostgreSQL',
      host: postgresqlForm.host,
      port: parseInt(postgresqlForm.port),
      database_name: postgresqlForm.database,
      username: postgresqlForm.username,
      password: postgresqlForm.password
    })
    
    if (result.success) {
      ElMessage.success(`PostgreSQL连接测试成功！延迟: ${result.latency_ms}ms`)
    } else {
      ElMessage.error(`PostgreSQL连接测试失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error('PostgreSQL连接测试失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 测试ClickHouse连接
const testClickhouseConnection = async () => {
  if (!clickhouseForm.host || !clickhouseForm.port || !clickhouseForm.database || !clickhouseForm.username) {
    ElMessage.error('请填写所有必填字段')
    return
  }
  
  try {
    loading.value = true
    const result = await testConnection({
      name: clickhouseForm.name,
      source_type: 'DATABASE',
      db_type: 'ClickHouse',
      host: clickhouseForm.host,
      port: parseInt(clickhouseForm.port),
      database_name: clickhouseForm.database,
      username: clickhouseForm.username,
      password: clickhouseForm.password
    })
    
    if (result.success) {
      ElMessage.success(`ClickHouse连接测试成功！延迟: ${result.latency_ms}ms`)
    } else {
      ElMessage.error(`ClickHouse连接测试失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error('ClickHouse连接测试失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 切换激活状态
const toggleActive = async (source) => {
  const newStatus = !source.status
  source.status = newStatus // 更新本地状态
  
  try {
    loading.value = true
    // 调用后端API更新状态
    const updatedSource = await updateDataSource(source.id, {
      status: newStatus
    })
    
    // 更新本地数据源列表
    const index = dataSources.value.findIndex(s => s.id === source.id)
    if (index !== -1) {
      dataSources.value[index] = updatedSource
    }
    
    ElMessage.success(`数据源 '${source.name}' ${newStatus ? '已激活' : '已停用'}`)
  } catch (error) {
    // 如果API调用失败，恢复本地状态
    source.status = !newStatus
    ElMessage.error('切换数据源状态失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 编辑数据源
const editSource = (source) => {
  ElMessage.info(`编辑数据源: ${source.name}`)
  // 这里可以打开一个编辑对话框，但根据需求，我们保持现有UI不变
  // 实际实现中，这里应该打开一个编辑模态框，预填充数据并调用updateDataSource API
}

// 删除数据源
const deleteSource = async (source) => {
  ElMessageBox.confirm(
    `确定要删除数据源 '${source.name}' 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      loading.value = true
      await deleteDataSource(source.id)
      // 从列表中移除
      const index = dataSources.value.findIndex(s => s.id === source.id)
      if (index !== -1) {
        dataSources.value.splice(index, 1)
      }
      ElMessage.success('数据源已删除')
    } catch (error) {
      ElMessage.error('删除数据源失败：' + error.message)
    } finally {
      loading.value = false
    }
  }).catch(() => {
    // 取消删除
  })
}

// 打开上传模态框
const openUploadModal = () => {
  uploadModalVisible.value = true
  uploadType.value = 'excel'
  excelName.value = ''
  
  // 重置所有表单
  mysqlForm.host = 'localhost'
  mysqlForm.port = '3306'
  mysqlForm.database = ''
  mysqlForm.username = ''
  mysqlForm.password = ''
  mysqlForm.name = ''
  
  sqlServerForm.host = 'localhost'
  sqlServerForm.port = '1433'
  sqlServerForm.database = ''
  sqlServerForm.authType = 'SQL_AUTH'
  sqlServerForm.username = ''
  sqlServerForm.password = ''
  sqlServerForm.domain = ''
  sqlServerForm.name = ''
  
  postgresqlForm.host = 'localhost'
  postgresqlForm.port = '5432'
  postgresqlForm.database = ''
  postgresqlForm.username = ''
  postgresqlForm.password = ''
  postgresqlForm.name = ''
  
  clickhouseForm.host = 'localhost'
  clickhouseForm.port = '8123'
  clickhouseForm.database = ''
  clickhouseForm.username = ''
  clickhouseForm.password = ''
  clickhouseForm.name = ''
}

// 加载状态
const loading = ref(false)

// 初始化数据源列表
const initDataSourceList = async () => {
  loading.value = true
  try {
    const sources = await getDataSources()
    dataSources.value = sources
  } catch (error) {
    ElMessage.error('获取数据源列表失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载数据源列表
onMounted(() => {
  initDataSourceList()
})

// 处理 Excel 文件上传
const handleExcelUpload = (file) => {
  console.log('Excel文件上传:', file)
  // 在当前实现中，我们不处理实际的文件上传，因为后端API没有提供文件上传端点
  // 文件上传功能需要后端支持，当前仅创建数据源记录
}

// 提交上传
const submitUpload = async () => {
  if (uploadType.value === 'excel') {
    if (!excelName.value.trim()) {
      ElMessage.error('请输入数据源名称')
      return
    }
    
    const dataSource = {
      name: excelName.value,
      source_type: 'FILE',
      status: true,
      created_by: 'system' // 这里应该从用户认证获取
    }
    
    try {
      loading.value = true
      const newSource = await createDataSource(dataSource)
      dataSources.value.unshift(newSource)
      ElMessage.success('Excel数据源创建成功，请通过其他方式上传Excel文件')
    } catch (error) {
      ElMessage.error('Excel数据源创建失败：' + error.message)
    } finally {
      loading.value = false
    }
  } else if (uploadType.value === 'mysql') {
    // 验证 MySQL 表单
    if (!mysqlForm.database || !mysqlForm.username || !mysqlForm.name) {
      ElMessage.error('请填写必填字段')
      return
    }
    
    const dataSource = {
      name: mysqlForm.name,
      source_type: 'DATABASE',
      db_type: 'MySQL',
      host: mysqlForm.host,
      port: parseInt(mysqlForm.port),
      database_name: mysqlForm.database,
      username: mysqlForm.username,
      password: mysqlForm.password,
      status: true,
      created_by: 'system'
    }
    
    try {
      loading.value = true
      const newSource = await createDataSource(dataSource)
      dataSources.value.unshift(newSource)
      ElMessage.success('MySQL数据源配置成功')
    } catch (error) {
      ElMessage.error('MySQL数据源配置失败：' + error.message)
    } finally {
      loading.value = false
    }
  } else if (uploadType.value === 'sqlserver') {
    // 验证 SQL Server 表单
    if (!sqlServerForm.database || !sqlServerForm.name) {
      ElMessage.error('请填写必填字段')
      return
    }
    
    if (sqlServerForm.authType === 'SQL_AUTH' && (!sqlServerForm.username || !sqlServerForm.password)) {
      ElMessage.error('SQL认证方式下，用户名和密码为必填项')
      return
    }
    
    if (sqlServerForm.authType === 'WINDOWS_AUTH' && !sqlServerForm.domain) {
      ElMessage.error('Windows认证方式下，域名字段为必填项')
      return
    }
    
    const dataSource = {
      name: sqlServerForm.name,
      source_type: 'DATABASE',
      db_type: 'SQL Server',
      host: sqlServerForm.host,
      port: parseInt(sqlServerForm.port),
      database_name: sqlServerForm.database,
      auth_type: sqlServerForm.authType,
      username: sqlServerForm.username,
      password: sqlServerForm.password,
      domain: sqlServerForm.domain,
      status: true,
      created_by: 'system'
    }
    
    try {
      loading.value = true
      const newSource = await createDataSource(dataSource)
      dataSources.value.unshift(newSource)
      ElMessage.success('SQL Server数据源配置成功')
    } catch (error) {
      ElMessage.error('SQL Server数据源配置失败：' + error.message)
    } finally {
      loading.value = false
    }
  } else if (uploadType.value === 'postgresql') {
    // 验证 PostgreSQL 表单
    if (!postgresqlForm.database || !postgresqlForm.username || !postgresqlForm.name) {
      ElMessage.error('请填写必填字段')
      return
    }
    
    const dataSource = {
      name: postgresqlForm.name,
      source_type: 'DATABASE',
      db_type: 'PostgreSQL',
      host: postgresqlForm.host,
      port: parseInt(postgresqlForm.port),
      database_name: postgresqlForm.database,
      username: postgresqlForm.username,
      password: postgresqlForm.password,
      status: true,
      created_by: 'system'
    }
    
    try {
      loading.value = true
      const newSource = await createDataSource(dataSource)
      dataSources.value.unshift(newSource)
      ElMessage.success('PostgreSQL数据源配置成功')
    } catch (error) {
      ElMessage.error('PostgreSQL数据源配置失败：' + error.message)
    } finally {
      loading.value = false
    }
  } else if (uploadType.value === 'clickhouse') {
    // 验证 ClickHouse 表单
    if (!clickhouseForm.database || !clickhouseForm.username || !clickhouseForm.name) {
      ElMessage.error('请填写必填字段')
      return
    }
    
    const dataSource = {
      name: clickhouseForm.name,
      source_type: 'DATABASE',
      db_type: 'ClickHouse',
      host: clickhouseForm.host,
      port: parseInt(clickhouseForm.port),
      database_name: clickhouseForm.database,
      username: clickhouseForm.username,
      password: clickhouseForm.password,
      status: true,
      created_by: 'system'
    }
    
    try {
      loading.value = true
      const newSource = await createDataSource(dataSource)
      dataSources.value.unshift(newSource)
      ElMessage.success('ClickHouse数据源配置成功')
    } catch (error) {
      ElMessage.error('ClickHouse数据源配置失败：' + error.message)
    } finally {
      loading.value = false
    }
  }
  
  uploadModalVisible.value = false
}
</script>

<style scoped>
.data-sources-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.sources-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.source-card {
  transition: all 0.3s ease;
}

.source-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.source-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.source-type {
  background-color: #e8f5e9;
  color: #2e7d32;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge {
  margin-left: 10px;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.connected {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.disconnected {
  background-color: #ffebee;
  color: #c62828;
}

.source-actions {
  display: flex;
  gap: 8px;
}

.source-details {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

.upload-content {
  padding: 16px 0;
}

.upload-type {
  margin-bottom: 20px;
}

.upload-excel {
  padding: 16px;
  border: 1px dashed #ddd;
  border-radius: 8px;
  margin-bottom: 16px;
}

.upload-name {
  margin-bottom: 16px;
}

.upload-database {
  padding: 16px;
}

.database-form {
  width: 100%;
}

.database-form .el-form-item {
  margin-bottom: 16px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  color: #666;
}

.empty-state p {
  margin-bottom: 20px;
  font-size: 16px;
}
</style>