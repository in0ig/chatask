import type { DataSource, ApiResponse } from '@/types/dataPreparation'
import { apiClient } from '@/api/index'

export const dataSourceApi = {
  // 数据源管理
  async getAll(): Promise<DataSource[]> {
    const response = await apiClient.get('/datasources')
    return response.data || response || []
  },

  async getDataSources(): Promise<ApiResponse<DataSource[]>> {
    try {
      const response = await apiClient.get('/datasources')
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch data sources'
      }
    }
  },

  async createDataSource(dataSource: Omit<DataSource, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<DataSource>> {
    try {
      const response = await apiClient.post('/datasources', dataSource)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create data source'
      }
    }
  },

  async updateDataSource(id: number, dataSource: Partial<DataSource>): Promise<ApiResponse<DataSource>> {
    try {
      const response = await apiClient.put(`/datasources/${id}`, dataSource)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to update data source'
      }
    }
  },

  async deleteDataSource(id: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/datasources/${id}`)
      return {
        success: true,
        message: 'Data source deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to delete data source'
      }
    }
  },

  async testConnection(dataSource: Partial<DataSource>): Promise<ApiResponse<boolean>> {
    try {
      const response = await apiClient.post('/datasources/test-connection', dataSource)
      return {
        success: true,
        data: response.data.success || false
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to test connection'
      }
    }
  },

  // Simplified methods for store compatibility
  async create(dataSource: any): Promise<DataSource> {
    const response = await apiClient.post('/datasources', dataSource)
    return response.data || response
  },

  async update(id: string | number, updates: any): Promise<DataSource> {
    const response = await apiClient.put(`/datasources/${id}`, updates)
    return response.data || response
  },

  async delete(id: string | number): Promise<void> {
    await apiClient.delete(`/datasources/${id}`)
  },

  async activate(id: string | number): Promise<DataSource> {
    const response = await apiClient.post(`/datasources/${id}/activate`)
    return response.data || response
  },

  async uploadExcel(file: File): Promise<DataSource> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/datasources/upload-excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data || response
  }
}