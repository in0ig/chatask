import api from '@/services/api'

// 数据表类型定义
export interface DataTable {
  id: string
  name: string
  sourceId: string
  sourceName: string
  fieldCount: number
  rowCount?: number
  lastSynced?: string
}

// 创建数据表请求参数
export interface CreateTableRequest {
  name: string
  sourceId: string
  columns?: Array<{ name: string; type: string; description?: string }>
}

// 同步表结构请求参数
export interface SyncTableRequest {
  tableId: string
  sourceId: string
}

// 表字段类型定义
export interface TableField {
  id: string
  field_name: string  // 后端返回的字段名
  data_type: string   // 后端返回的数据类型
  description?: string
  is_primary_key: boolean
  is_nullable: boolean
}

// SQL 执行请求参数
export interface ExecuteSqlRequest {
  sql: string
  sourceId: string
  tableName?: string
}

// SQL 执行结果
export interface SqlExecutionResult {
  success: boolean
  message: string
  data?: any[]
  columns?: Array<{ name: string; type: string }>
  rowsAffected?: number
  executionTime?: number
}

// SQL 验证结果
export interface SqlValidationResult {
  isValid: boolean
  errors: Array<{
    line: number
    column: number
    message: string
    severity: 'error' | 'warning'
  }>
  suggestions?: string[]
}

// 数据表API服务
export const dataTableApi = {
  // 获取数据表列表（支持分页和筛选）
  getDataTables(params: {
    page?: number
    page_size?: number
    search?: string
    source_id?: string
    status?: boolean
  }): Promise<{
    items: Array<{
      id: string
      table_name: string
      data_source_id: string
      data_source_name?: string
      field_count: number
      row_count?: number
      table_type?: string
      description?: string
      fields?: Array<any>
      relations?: Array<any>
    }>
    total: number
    page: number
    page_size: number
  }> {
    return api.get('/data-tables/', { params })
  },

  // 删除数据表
  deleteDataTable(id: string): Promise<void> {
    return api.delete(`/data-tables/${id}/`)
  },

  // 批量同步表结构
  batchSyncTableStructures(request: {source_id: string, table_names: string[]}): Promise<{
    total_requested: number
    successfully_synced: number
    failed_count: number
    synced_tables: string[]
  }> {
    return api.post('/data-tables/batch-sync-structure/', request)
  },
  
  // 获取所有数据表
  getAll(): Promise<DataTable[]> {
    return this.getDataTables({ page: 1, page_size: 100 }).then(response => 
      response.items.map(item => ({
        id: item.id,
        name: item.table_name,
        sourceId: item.data_source_id,
        sourceName: item.data_source_name || '未知数据源',
        fieldCount: item.field_count,
        rowCount: item.row_count
      }))
    )
  },
  
  // 获取所有数据表 (别名)
  getList(): Promise<DataTable[]> {
    return this.getAll()
  },
  
  // 根据数据源ID获取数据表
  getBySourceId(sourceId: string): Promise<DataTable[]> {
    return this.getDataTables({ source_id: sourceId, page: 1, page_size: 100 }).then(response => 
      response.items.map(item => ({
        id: item.id,
        name: item.table_name,
        sourceId: item.data_source_id,
        sourceName: item.data_source_name || '未知数据源',
        fieldCount: item.field_count,
        rowCount: item.row_count
      }))
    )
  },
  
  // 根据数据源ID获取数据表 (别名)
  getBySource(sourceId: number): Promise<DataTable[]> {
    return this.getBySourceId(sourceId.toString())
  },
  
  // 根据ID获取单个数据表
  getById(id: string): Promise<DataTable> {
    return api.get(`/data-tables/${id}`)
  },
  
  // 创建新的数据表
  create(table: CreateTableRequest): Promise<DataTable> {
    return api.post('/data-tables', table)
  },
  
  // 更新现有数据表
  update(id: string, updates: Partial<CreateTableRequest>): Promise<DataTable> {
    return api.put(`/data-tables/${id}`, updates)
  },
  
  // 删除数据表
  delete(id: string): Promise<void> {
    return api.delete(`/data-tables/${id}`)
  },
  
  // 同步表结构（通过表ID）
  syncStructureById(tableId: string): Promise<DataTable> {
    return api.post(`/data-tables/${tableId}/sync`)
  },
  
  // 获取表字段信息
  getFields(tableId: string): Promise<TableField[]> {
    return api.get(`/data-tables/${tableId}/columns`)
  },
  
  // 获取表完整详情（包含字段、数据字典、表关联）
  getTableDetail(tableId: string): Promise<{
    id: string
    table_name: string
    data_source_id: string
    data_source_name: string
    field_count: number
    table_type: string
    description: string
    fields: Array<{
      id: string
      table_id: string
      field_name: string
      display_name: string
      data_type: string
      description: string
      is_primary_key: boolean
      is_nullable: boolean
      default_value: string | null
      dictionary_id: string | null
      dictionary: {
        id: string
        code: string
        name: string
        items: Array<{
          item_key: string
          item_value: string
          description: string
        }>
      } | null
      is_queryable: boolean
      is_aggregatable: boolean
      sort_order: number
    }>
    relations: Array<{
      id: string
      relation_name: string
      primary_table_id: string
      primary_table_name: string
      primary_field_id: string
      primary_field_name: string
      foreign_table_id: string
      foreign_table_name: string
      foreign_field_id: string
      foreign_field_name: string
      relation_type: string
      description: string
    }>
  }> {
    return api.get(`/data-tables/${tableId}/detail`)
  },
  
  // 获取表数据预览
  // 注意：后端暂未实现此端点，返回空数组
  getPreview(tableId: string, limit: number = 100): Promise<any[]> {
    // TODO: 等待后端实现 /data-tables/{tableId}/preview 端点
    console.warn('数据预览功能暂未实现，返回空数据')
    return Promise.resolve([])
  },
  
  // 执行 SQL 语句
  executeSql(request: ExecuteSqlRequest): Promise<SqlExecutionResult> {
    return api.post('/data-tables/execute-sql', request)
  },
  
  // 验证 SQL 语法
  validateSql(sql: string, sourceId: string): Promise<SqlValidationResult> {
    return api.post('/data-tables/validate-sql', { sql, sourceId })
  },
  
  // 从 SQL 创建数据表
  createFromSql(request: ExecuteSqlRequest): Promise<DataTable> {
    return api.post('/data-tables/create-from-sql', request)
  },
  
  // 从数据源发现表
  discoverTables(sourceId: string): Promise<Array<{table_name: string, comment?: string, row_count: number, schema: string}>> {
    return api.get(`/data-tables/discover/${sourceId}/`, { timeout: 60000 })
  },
  
  // 同步单个表结构
  syncStructure(request: {source_id: number, table_name: string}): Promise<DataTable> {
    return api.post('/data-tables/sync-structure', request)
  },
  
  // 批量同步表结构
  batchSyncStructure(request: {source_id: string, table_names: string[]}): Promise<{total_requested: number, successfully_synced: number, failed_count: number, synced_tables: string[]}> {
    return api.post('/data-tables/batch-sync-structure', request)
  },
  
  // 获取表结构详情（不同步）
  getTableStructure(sourceId: string, tableName: string): Promise<{table_name: string, comment?: string, row_count: number, field_count: number, fields: Array<any>}> {
    return api.get(`/data-tables/structure/${sourceId}/${tableName}`)
  },
  
  // 测试数据源连接
  testConnection(sourceId: string): Promise<{success: boolean, message: string, source_id: string, source_name: string}> {
    return api.post(`/data-tables/test-connection/${sourceId}`)
  },
  
  // 更新表字段
  updateField(tableId: number, fieldId: number, data: Partial<TableField>): Promise<TableField> {
    return api.put(`/data-tables/${tableId}/fields/${fieldId}`, data)
  },
  
  // 更新表字段（使用字段ID）
  updateTableField(fieldId: string, data: {
    display_name?: string
    description?: string
    dictionary_id?: string | null
    is_queryable?: boolean
    is_aggregatable?: boolean
  }): Promise<TableField> {
    return api.put(`/table-fields/${fieldId}`, data)
  },
  
  // 添加表字段
  addField(tableId: number, data: Omit<TableField, 'id'>): Promise<TableField> {
    return api.post(`/data-tables/${tableId}/fields`, data)
  },
  
  // 删除表字段
  deleteField(tableId: number, fieldId: number): Promise<void> {
    return api.delete(`/data-tables/${tableId}/fields/${fieldId}`)
  }
}
