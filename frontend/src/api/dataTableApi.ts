import type { DataTable, TableField, ApiResponse } from '@/types/dataPreparation'
import { apiClient } from '@/api/index'

const unwrapList = <T>(payload: any): T[] => {
  if (!payload) return []
  if (Array.isArray(payload)) return payload as T[]
  if (Array.isArray(payload.items)) return payload.items as T[]
  if (Array.isArray(payload.data_tables)) return payload.data_tables as T[]
  if (Array.isArray(payload.data)) return payload.data as T[]
  return []
}

export const dataTableApi = {
  // 数据表管理
  async getDataTables(): Promise<ApiResponse<DataTable[]>> {
    try {
      const response = await apiClient.get('/data-tables')
      return {
        success: true,
        data: unwrapList<DataTable>(response)
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch data tables'
      }
    }
  },

  async getDataTablesByDataSource(dataSourceId: number): Promise<ApiResponse<DataTable[]>> {
    try {
      const response = await apiClient.get(`/datasources/${dataSourceId}/tables`)
      return {
        success: true,
        data: unwrapList<DataTable>(response)
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch data tables by data source'
      }
    }
  },

  async createDataTable(dataTable: Omit<DataTable, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<DataTable>> {
    try {
      const response = await apiClient.post('/data-tables', dataTable)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create data table'
      }
    }
  },

  async updateDataTable(id: number, dataTable: Partial<DataTable>): Promise<ApiResponse<DataTable>> {
    try {
      const response = await apiClient.put(`/data-tables/${id}`, dataTable)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to update data table'
      }
    }
  },

  async deleteDataTable(id: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/data-tables/${id}`)
      return {
        success: true,
        message: 'Data table deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to delete data table'
      }
    }
  },

  // 表字段管理
  async getTableFields(tableId: number): Promise<ApiResponse<TableField[]>> {
    try {
      const response = await apiClient.get(`/data-tables/${tableId}/fields`)
      return {
        success: true,
        data: unwrapList<TableField>(response)
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch table fields'
      }
    }
  },

  async getAllTableFields(): Promise<ApiResponse<TableField[]>> {
    try {
      const response = await apiClient.get('/table-fields')
      return {
        success: true,
        data: unwrapList<TableField>(response)
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch all table fields'
      }
    }
  },

  async createTableField(field: Omit<TableField, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<TableField>> {
    try {
      const response = await apiClient.post('/table-fields', field)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create table field'
      }
    }
  },

  async updateTableField(id: number, field: Partial<TableField>): Promise<ApiResponse<TableField>> {
    try {
      const response = await apiClient.put(`/table-fields/${id}`, field)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to update table field'
      }
    }
  },

  async deleteTableField(id: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/table-fields/${id}`)
      return {
        success: true,
        message: 'Table field deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to delete table field'
      }
    }
  }
}