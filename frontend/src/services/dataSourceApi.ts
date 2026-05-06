import api from '@/services/api'

// 数据源类型定义
export interface DataSource {
  id: string
  name: string
  type: 'mysql' | 'excel' | 'api'
  connectionString?: string
  filePath?: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

// 创建数据源请求参数
export interface CreateDataSourceRequest {
  name: string
  type: 'mysql' | 'excel' | 'api'
  connectionString?: string
  filePath?: string
}

// 更新数据源请求参数
export interface UpdateDataSourceRequest extends Partial<CreateDataSourceRequest> {}

// 连接测试请求参数
export interface ConnectionTestRequest {
  type: 'mysql' | 'excel' | 'api'
  connectionString?: string
  filePath?: string
}

// 连接测试响应参数
export interface ConnectionTestResponse {
  success: boolean
  message: string
  latencyMs?: number
}

// 导出数据源响应
export interface ExportDataSourceResponse {
  url: string
  filename: string
}

// 数据源API服务
export const dataSourceApi = {
  // 获取所有数据源
  getAll(): Promise<DataSource[]> {
    return api.get('/data-sources/').then(response => response.data)
  },
  
  // 根据ID获取单个数据源
  getById(id: string): Promise<DataSource> {
    return api.get(`/data-sources/${id}/`).then(response => response.data)
  },
  
  // 创建新的数据源
  create(dataSource: CreateDataSourceRequest): Promise<DataSource> {
    return api.post('/data-sources/', dataSource).then(response => response.data)
  },
  
  // 更新现有数据源
  update(id: string, updates: UpdateDataSourceRequest): Promise<DataSource> {
    return api.put(`/data-sources/${id}/`, updates).then(response => response.data)
  },
  
  // 删除数据源
  delete(id: string): Promise<void> {
    return api.delete(`/data-sources/${id}/`).then(response => response.data)
  },
  
  // 测试连接
  testConnection(config: ConnectionTestRequest): Promise<ConnectionTestResponse> {
    return api.post('/data-sources/test/', config).then(response => response.data)
  },
  
  // 激活数据源
  activate(id: string): Promise<DataSource> {
    return api.put(`/data-sources/${id}/activate/`).then(response => response.data)
  },
  
  // 上传Excel文件
  uploadExcel(file: File): Promise<DataSource> {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post('/data-sources/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }).then(response => response.data)
  },
  
  // 导出数据源
  export(id: string, format: 'excel' | 'csv'): Promise<ExportDataSourceResponse> {
    return api.get(`/data-sources/${id}/download/`, {
      params: { format }
    }).then(response => response.data)
  }
}
