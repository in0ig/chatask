import type { TableRelation, ApiResponse } from '@/types/dataPreparation'
import { apiClient } from '@/api/index'

export const relationApi = {
  // 表关系管理
  async getRelations(): Promise<ApiResponse<TableRelation[]>> {
    try {
      const response = await apiClient.get('/relations')
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch relations'
      }
    }
  },

  async getRelationsByTable(tableId: number): Promise<ApiResponse<TableRelation[]>> {
    try {
      const response = await apiClient.get(`/tables/${tableId}/relations`)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to fetch table relations'
      }
    }
  },

  async createRelation(relation: Omit<TableRelation, 'id' | 'created_at' | 'updated_at'>): Promise<ApiResponse<TableRelation>> {
    try {
      const response = await apiClient.post('/relations', relation)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create relation'
      }
    }
  },

  async updateRelation(id: number, relation: Partial<TableRelation>): Promise<ApiResponse<TableRelation>> {
    try {
      const response = await apiClient.put(`/relations/${id}`, relation)
      return {
        success: true,
        data: response.data
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to update relation'
      }
    }
  },

  async deleteRelation(id: number): Promise<ApiResponse<void>> {
    try {
      await apiClient.delete(`/relations/${id}`)
      return {
        success: true,
        message: 'Relation deleted successfully'
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to delete relation'
      }
    }
  }
}