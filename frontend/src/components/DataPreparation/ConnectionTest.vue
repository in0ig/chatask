<template>
  <div class="connection-test">
    <el-form-item>
      <el-button
        type="primary"
        :loading="isTesting"
        :disabled="!canTest"
        @click="handleTestConnection"
      >
        <el-icon><Connection /></el-icon>
        测试连接
      </el-button>
      
      <!-- 连接状态显示 -->
      <div v-if="testResult" class="test-result">
        <el-tag
          :type="testResult.success ? 'success' : 'danger'"
          :icon="testResult.success ? SuccessFilled : CircleCloseFilled"
          class="result-tag"
        >
          {{ testResult.success ? '连接成功' : '连接失败' }}
        </el-tag>
        
        <span class="result-message">
          {{ testResult.message }}
        </span>
        
        <span v-if="testResult.latencyMs" class="result-latency">
          （{{ testResult.latencyMs }}ms）
        </span>
      </div>
      
      <!-- 连接历史记录 -->
      <div v-if="testHistory.length > 0" class="test-history">
        <el-collapse v-model="historyVisible">
          <el-collapse-item title="连接历史" name="history">
            <div class="history-list">
              <div
                v-for="(record, index) in testHistory"
                :key="index"
                class="history-item"
              >
                <el-tag
                  :type="record.success ? 'success' : 'danger'"
                  size="small"
                  class="history-tag"
                >
                  {{ record.success ? '成功' : '失败' }}
                </el-tag>
                <span class="history-time">{{ formatTime(record.timestamp) }}</span>
                <span class="history-message">{{ record.message }}</span>
                <span v-if="record.latencyMs" class="history-latency">
                  {{ record.latencyMs }}ms
                </span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, SuccessFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { dataSourceApi, type ConnectionTestRequest, type ConnectionTestResponse, DataSourceType, DatabaseType, AuthType } from '@/api/dataSourceApi'

// 定义组件 props
interface Props {
  config: {
    sourceType?: DataSourceType | string
    dbType?: DatabaseType | string
    host?: string
    port?: number
    databaseName?: string
    authType?: AuthType | string
    username?: string
    password?: string
    domain?: string
    name?: string
  }
}

const props = defineProps<Props>()

// 定义组件 emits
const emit = defineEmits<{
  testResult: [result: ConnectionTestResult]
}>()

// 连接测试结果接口
interface ConnectionTestResult {
  success: boolean
  message: string
  latencyMs?: number
}

// 连接测试历史记录接口
interface ConnectionTestRecord extends ConnectionTestResult {
  timestamp: Date
}

// 响应式数据
const isTesting = ref(false)
const testResult = ref<ConnectionTestResult | null>(null)
const testHistory = ref<ConnectionTestRecord[]>([])
const historyVisible = ref<string[]>([])

// 是否可以测试连接
const canTest = computed(() => {
  const { config } = props
  
  // 只有数据库类型才能测试连接
  if (config.sourceType !== 'DATABASE' && config.sourceType !== DataSourceType.DATABASE) {
    return false
  }
  
  // 基本连接信息必须完整
  if (!config.dbType || !config.host || !config.port || !config.databaseName) {
    return false
  }
  
  // SQL Server 需要特殊处理认证方式
  if (config.dbType === 'SQLSERVER' || config.dbType === DatabaseType.SQL_SERVER) {
    if (!config.authType) return false
    
    // SQL 认证需要用户名和密码
    if ((config.authType === 'SQL_AUTH' || config.authType === AuthType.SQL_AUTH) && 
        (!config.username || !config.password)) {
      return false
    }
    
    // Windows 认证不需要用户名密码，但需要域名（可选）
    if (config.authType === 'WINDOWS_AUTH' || config.authType === AuthType.WINDOWS_AUTH) {
      return true
    }
  } else {
    // 其他数据库类型需要用户名和密码
    if (!config.username || !config.password) {
      return false
    }
  }
  
  return true
})

// 处理连接测试
const handleTestConnection = async () => {
  if (!canTest.value) {
    ElMessage.warning('请先填写完整的连接信息')
    return
  }

  isTesting.value = true
  testResult.value = null

  const startTime = Date.now()

  try {
    // 构建连接测试请求
    const testRequest: ConnectionTestRequest = {
      name: props.config.name || 'test-connection',
      sourceType: props.config.sourceType === 'DATABASE' ? DataSourceType.DATABASE : DataSourceType.DATABASE,
      dbType: mapDbType(props.config.dbType),
      host: props.config.host!,
      port: props.config.port!,
      databaseName: props.config.databaseName!,
      authType: mapAuthType(props.config.authType),
      username: props.config.username,
      password: props.config.password,
      domain: props.config.domain,
      createdBy: 'current-user' // 实际应用中应该从用户状态获取
    }

    // 调用真实的 API
    const apiResponse: ConnectionTestResponse = await dataSourceApi.testConnection(testRequest)
    const latencyMs = Date.now() - startTime

    const testResultData: ConnectionTestResult = {
      success: apiResponse.success,
      message: apiResponse.message,
      latencyMs: apiResponse.latency_ms || latencyMs
    }

    testResult.value = testResultData

    // 添加到历史记录
    testHistory.value.unshift({
      ...testResultData,
      timestamp: new Date()
    })

    // 限制历史记录数量
    if (testHistory.value.length > 10) {
      testHistory.value = testHistory.value.slice(0, 10)
    }

    // 发送结果给父组件
    emit('testResult', testResultData)

    // 显示用户提示
    if (testResultData.success) {
      ElMessage.success(`连接测试成功 (${testResultData.latencyMs}ms)`)
    } else {
      ElMessage.error(`连接测试失败: ${testResultData.message}`)
    }

  } catch (error: any) {
    const latencyMs = Date.now() - startTime
    const errorResult: ConnectionTestResult = {
      success: false,
      message: error.response?.data?.message || error.message || '连接测试失败：网络错误或服务器异常',
      latencyMs
    }

    testResult.value = errorResult

    // 添加到历史记录
    testHistory.value.unshift({
      ...errorResult,
      timestamp: new Date()
    })

    // 发送结果给父组件
    emit('testResult', errorResult)

    // 显示错误提示
    ElMessage.error(`连接测试失败: ${errorResult.message}`)

  } finally {
    isTesting.value = false
  }
}

// 映射数据库类型
const mapDbType = (dbType?: string): DatabaseType | undefined => {
  if (!dbType) return undefined
  
  switch (dbType.toUpperCase()) {
    case 'MYSQL':
      return DatabaseType.MYSQL
    case 'SQLSERVER':
    case 'SQL_SERVER':
      return DatabaseType.SQL_SERVER
    case 'POSTGRESQL':
      return DatabaseType.POSTGRESQL
    case 'CLICKHOUSE':
      return DatabaseType.CLICKHOUSE
    default:
      return dbType as DatabaseType
  }
}

// 映射认证类型
const mapAuthType = (authType?: string): AuthType | undefined => {
  if (!authType) return undefined
  
  switch (authType.toUpperCase()) {
    case 'SQL_AUTH':
      return AuthType.SQL_AUTH
    case 'WINDOWS_AUTH':
      return AuthType.WINDOWS_AUTH
    default:
      return authType as AuthType
  }
}

// 格式化时间
const formatTime = (timestamp: Date): string => {
  return timestamp.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 监听配置变化，清除测试结果
watch(() => props.config, () => {
  testResult.value = null
}, { deep: true })

// 清除测试历史
const clearHistory = () => {
  testHistory.value = []
  historyVisible.value = []
}

// 暴露给父组件的方法
defineExpose({
  testConnection: handleTestConnection,
  clearHistory
})
</script>

<style scoped>
.connection-test {
  width: 100%;
}

.test-result {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-tag {
  font-weight: 500;
}

.result-message {
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.result-latency {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.test-history {
  margin-top: 16px;
}

.history-list {
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.history-item:last-child {
  border-bottom: none;
}

.history-tag {
  flex-shrink: 0;
}

.history-time {
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  min-width: 80px;
}

.history-message {
  flex: 1;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.history-latency {
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .test-result {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .history-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .history-time {
    min-width: auto;
  }
}
</style>