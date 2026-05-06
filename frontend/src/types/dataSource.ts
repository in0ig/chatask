/**
 * 数据源类型定义
 */

export interface DataSource {
  id: string
  name: string
  type: 'mysql' | 'postgresql' | 'sqlserver' | 'oracle' | 'clickhouse'
  host: string
  port: number
  database: string
  username: string
  password?: string
  status: 'connected' | 'disconnected' | 'error' | 'testing'
  description?: string
  createdAt: string
  updatedAt: string
}

export interface DataSourceConfig {
  name: string
  type: 'mysql' | 'postgresql' | 'sqlserver' | 'oracle' | 'clickhouse'
  host: string
  port: number
  database: string
  username: string
  password: string
  description?: string
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  latency?: number
}

export interface CreateDataSourceRequest {
  name: string
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  description?: string
}

export interface UpdateDataSourceRequest {
  name?: string
  type?: string
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  description?: string
}

// 确保文件被识别为模块
export {};