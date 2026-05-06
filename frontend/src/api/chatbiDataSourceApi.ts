import api from '@/services/api'
import type { 
  DataSourceConfig, 
  ConnectionTestResult,
  DataSourceListResponse,
  DataSourceResponse,
  ConnectionTestResponse,
  CreateDataSourceRequest,
  UpdateDataSourceRequest
} from '@/types/dataSource'

/** axios 拦截器已解包：单条数据源为扁平 JSON；兼容误包一层 { data } 的情况 */
function backendDataSourceRecord(response: unknown): any {
  if (!response || typeof response !== 'object') return response
  const r = response as Record<string, unknown>
  if (typeof r.id === 'string') return r
  const inner = r.data
  if (inner && typeof inner === 'object' && typeof (inner as Record<string, unknown>).id === 'string') {
    return inner
  }
  return r
}

// ChatBI 数据源 API 服务
export const chatbiDataSourceApi = {
  // 获取所有数据源
  async getDataSources(): Promise<DataSourceListResponse> {
    const response = await api.get('/datasources/')
    // 响应拦截器已经处理了response.data，所以response就是实际数据
    const backendData = response
    
    // 转换后端数据格式到前端格式
    const transformedData = {
      data: backendData.data.map((item: any) => ({
        id: item.id,
        name: item.name,
        type: item.db_type === 'MySQL' ? 'mysql' : 'sqlserver',
        config: {
          host: item.host,
          port: item.port,
          database: item.database_name,
          username: item.username,
          password: '********', // 不显示真实密码
          connectionPool: {
            min: 5,
            max: 20,
            timeout: 30
          }
        },
        status: item.status ? 'active' : 'inactive',
        createdAt: new Date(item.created_at),
        updatedAt: new Date(item.updated_at)
      })),
      total: backendData.total
    }
    
    return transformedData
  },
  
  // 根据 ID 获取单个数据源
  async getDataSourceById(id: string): Promise<DataSourceResponse> {
    const response = await api.get(`/datasources/${id}/`)
    return response
  },
  
  // 创建新的数据源
  async createDataSource(config: DataSourceConfig): Promise<any> {
    const request = {
      name: config.name,
      source_type: 'DATABASE',
      db_type: config.type === 'mysql' ? 'MySQL' : 'SQL Server',
      host: config.host,
      port: config.port,
      database_name: config.database,
      auth_type: 'SQL_AUTH',
      username: config.username,
      password: config.password,
      created_by: 'system' // 临时用户，实际应用中应该从用户会话获取
    }
    
    const response = await api.post('/datasources/', request)
    
    // 转换后端返回的数据格式到前端格式（与 getDataSources 保持一致）
    const backendData = backendDataSourceRecord(response)
    const transformedData = {
      id: backendData.id,
      name: backendData.name,
      type: backendData.db_type === 'MySQL' ? 'mysql' : 'sqlserver',
      config: {
        host: backendData.host,
        port: backendData.port,
        database: backendData.database_name,
        username: backendData.username,
        password: '********', // 不显示真实密码
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      },
      status: backendData.status ? 'active' : 'inactive',
      createdAt: new Date(backendData.created_at),
      updatedAt: new Date(backendData.updated_at)
    }
    
    return transformedData
  },
  
  // 更新现有数据源
  async updateDataSource(id: string, config: DataSourceConfig): Promise<DataSourceResponse> {
    const pwd = config.password?.trim()
    const omitPassword = !pwd || pwd === '********'
    const request: Record<string, unknown> = {
      name: config.name,
      source_type: 'DATABASE',
      db_type: config.type === 'mysql' ? 'MySQL' : 'SQL Server',
      host: config.host,
      port: config.port,
      database_name: config.database,
      auth_type: 'SQL_AUTH',
      username: config.username,
      created_by: 'system' // 临时用户，实际应用中应该从用户会话获取
    }
    if (!omitPassword) {
      request.password = config.password
    }
    
    const response = await api.put(`/datasources/${id}/`, request)
    
    // 转换后端返回的数据格式到前端格式（与 getDataSources 保持一致）
    const backendData = backendDataSourceRecord(response)
    const transformedData = {
      data: {
        id: backendData.id,
        name: backendData.name,
        type: backendData.db_type === 'MySQL' ? 'mysql' : 'sqlserver',
        config: {
          host: backendData.host,
          port: backendData.port,
          database: backendData.database_name,
          username: backendData.username,
          password: '********', // 不显示真实密码
          connectionPool: {
            min: 5,
            max: 20,
            timeout: 30
          }
        },
        status: backendData.status ? 'active' : 'inactive',
        createdAt: new Date(backendData.created_at),
        updatedAt: new Date(backendData.updated_at)
      }
    }
    
    return transformedData
  },
  
  // 删除数据源
  async deleteDataSource(id: string): Promise<void> {
    await api.delete(`/datasources/${id}/`)
  },
  
  // 测试数据源连接
  async testConnection(config: DataSourceConfig): Promise<ConnectionTestResult> {
    const request = {
      name: config.name,
      source_type: 'DATABASE',
      db_type: config.type === 'mysql' ? 'MySQL' : 'SQL Server',
      host: config.host,
      port: config.port,
      database_name: config.database,
      auth_type: 'SQL_AUTH',
      username: config.username,
      password: config.password,
      created_by: 'system' // 临时用户，测试连接时不需要真实用户
    }
    
    const response = await api.post('/datasources/test', request)
    return response
  },
  
  // 获取连接池状态
  async getConnectionPoolStatus(id: string): Promise<any> {
    const response = await api.get(`/datasources/${id}/pool-status/`)
    return response
  },
  
  // 重置连接池
  async resetConnectionPool(id: string): Promise<void> {
    await api.post(`/datasources/${id}/reset-pool/`)
  }
}

// 为了兼容性，也导出为 dataSourceApi
export const dataSourceApi = chatbiDataSourceApi