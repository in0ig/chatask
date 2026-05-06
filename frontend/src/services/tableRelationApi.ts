import api from '@/services/api'

// 表关联类型定义
export interface TableRelation {
  id: string
  relationName: string
  primaryTableId: string
  primaryTableName: string
  primaryFieldId: string
  primaryFieldName: string
  primaryFieldType: string
  foreignTableId: string
  foreignTableName: string
  foreignFieldId: string
  foreignFieldName: string
  foreignFieldType: string
  joinType: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  description?: string
  status: boolean
  createdBy: string
  createdAt: string
  updatedAt: string
}

// 创建表关联请求参数
export interface CreateTableRelationRequest {
  relationName: string
  primaryTableId: string
  primaryFieldId: string
  foreignTableId: string
  foreignFieldId: string
  joinType: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  description?: string
  status?: boolean
  createdBy: string
}

// 更新表关联请求参数
export interface UpdateTableRelationRequest {
  relationName?: string
  primaryTableId?: string
  primaryFieldId?: string
  foreignTableId?: string
  foreignFieldId?: string
  joinType?: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  description?: string
  status?: boolean
}

// 表关联API服务
export const tableRelationApi = {
  // 获取所有表关联
  getAll(): Promise<TableRelation[]> {
    return api.get('/table-relations').then(response => response.data)
  },
  
  // 根据主表ID获取表关联
  getByPrimaryTableId(primaryTableId: string): Promise<TableRelation[]> {
    return api.get('/table-relations', { params: { primary_table_id: primaryTableId } }).then(response => response.data)
  },
  
  // 根据从表ID获取表关联
  getByForeignTableId(foreignTableId: string): Promise<TableRelation[]> {
    return api.get('/table-relations', { params: { foreign_table_id: foreignTableId } }).then(response => response.data)
  },
  
  // 根据ID获取单个表关联
  getById(id: string): Promise<TableRelation> {
    return api.get(`/table-relations/${id}`).then(response => response.data)
  },
  
  // 创建新的表关联
  create(relation: CreateTableRelationRequest): Promise<TableRelation> {
    return api.post('/table-relations', relation).then(response => response.data)
  },
  
  // 更新现有表关联
  update(id: string, updates: UpdateTableRelationRequest): Promise<TableRelation> {
    return api.put(`/table-relations/${id}`, updates).then(response => response.data)
  },
  
  // 删除表关联
  delete(id: string): Promise<void> {
    return api.delete(`/table-relations/${id}`).then(response => response.data)
  }
}