import type { FieldMapping, ApiResponse } from '@/types/dataPreparation'
import { apiClient } from '@/api/index'

export const fieldMappingApi = {
  // 字段映射管理
  async getFieldMappings(): Promise<ApiResponse<FieldMapping[]>> {
    try {
      const response = await apiClient.get('/field-mappings')
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch field mappings'
      }
    }
  },

  async getFieldMappingsByTable(tableId: number): Promise<ApiResponse<FieldMapping[]>> {
    try {
      const response = await apiClient.get(`/tables/${tableId}/field-mappings`)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch table field mappings'
      }
    }
  },

  async createFieldMapping(mapping: Omit<FieldMapping, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<FieldMapping>> {
    try {
      const response = await apiClient.post('/field-mappings', mapping)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create field mapping'
      }
    }
  },

  async updateFieldMapping(id: number, mapping: Partial<FieldMapping>): Promise<ApiResponse<FieldMapping>> {
    try {
      const response = await apiClient.put(`/field-mappings/${id}`, mapping)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to update field mapping'
      }
    }
  },

  async deleteFieldMapping(id: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/field-mappings/${id}`)
      return {
        success: true,
        message: 'Field mapping deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to delete field mapping'
      }
    }
  },

  // 批量操作
  async batchCreateFieldMappings(mappings: Omit<FieldMapping, 'id' | 'created_at' | 'updated_at'>[]): Promise<ApiResponse<FieldMapping[]>> {
    try {
      const response = await apiClient.post('/field-mappings/batch', { mappings })
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to batch create field mappings'
      }
    }
  },

  async batchUpdateFieldMappings(updates: { id: number; data: Partial<FieldMapping> }[]): Promise<ApiResponse<FieldMapping[]>> {
    try {
      const response = await apiClient.put('/field-mappings/batch', { updates })
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to batch update field mappings'
      }
    }
  },

  async batchDeleteFieldMappings(ids: number[]): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete('/field-mappings/batch', { data: { ids } })
      return {
        success: true,
        message: 'Field mappings deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to batch delete field mappings'
      }
    }
  },

  // 导入导出
  async importFieldMappings(file: File, tableId: number): Promise<ApiResponse<void>> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('table_id', tableId.toString())
      
      const response = await apiClient.post('/field-mappings/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      return {
        success: true,
        message: response.data.message || 'Field mappings imported successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to import field mappings'
      }
    }
  },

  async exportFieldMappings(tableId: number): Promise<Blob> {
    const response = await apiClient.get(`/tables/${tableId}/field-mappings/export`, {
      responseType: 'blob'
    })
    return response.data
  }
}