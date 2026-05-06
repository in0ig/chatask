/**
 * Data Preparation Store - 管理数据准备相关状态
 * 对应 PRD 模块 1（左侧导航与数据准备）
 */
import { defineStore } from 'pinia'
import { useUIStore } from './ui'
import { dataSourceApi, DataSource, CreateDataSourceRequest, UpdateDataSourceRequest, ConnectionTestRequest } from '@/services/dataSourceApi'
import { dataTableApi, DataTable, CreateTableRequest } from '@/services/dataTableApi'
import { dictionaryApi, DictionaryEntry, CreateDictionaryEntryRequest, UpdateDictionaryEntryRequest } from '@/services/dictionaryApi'

export interface DataPrepState {
  // 数据源
  dataSources: DataSource[]
  activeDataSourceId: string | null
  
  // 数据表
  dataTables: DataTable[]
  
  // 字典表
  dictionaries: DictionaryEntry[]
  
  // 连接测试状态
  connectionTestResult: {
    success: boolean
    message: string
  } | null
  
  // 权限配置
  permissions: {
    query: boolean
    report: boolean
    export: boolean
  }
  tablePermissions: string[]
  
  // 增强的缓存系统
  dataSourceCache: { 
    data: DataSource[]
    timestamp: Date
    version: number // 缓存版本，用于缓存失效
  } | null
  
  // 数据表缓存
  dataTableCache: Map<string, {
    data: DataTable[]
    timestamp: Date
    sourceId: string
  }>
  
  // 字典缓存
  dictionaryCache: {
    data: DictionaryEntry[]
    timestamp: Date
    byTable: Map<string, DictionaryEntry[]> // 按表名索引
  } | null
  
  // 表关联
  tableRelations: TableRelation[]
  
  // 预加载状态
  preloadStatus: {
    dataSources: boolean
    dataTables: boolean
    dictionaries: boolean
  }
  
  // 性能监控
  performanceMetrics: {
    lastLoadTime: number
    averageLoadTime: number
    loadCount: number
    cacheHitRate: number
    totalCacheHits: number
    totalCacheRequests: number
  }
  
  // 加载状态和错误处理
  isLoading: boolean
  error: string | null
  
  // 数据源专用加载状态和错误
  isLoadingDataSources: boolean
  dataSourceError: string | null
}

// 表关联接口类型定义
export interface TableRelation {
  id: number
  source_table: string
  source_column: string
  target_table: string
  target_column: string
  relation_type: 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many'
  is_active: boolean
  created_at: string
}

export interface CreateTableRelationRequest {
  source_table_id: string
  source_column_id: string
  target_table_id: string
  target_column_id: string
  relation_type: 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many'
  description?: string
}

export interface UpdateTableRelationRequest {
  source_table_id?: string
  source_column_id?: string
  target_table_id?: string
  target_column_id?: string
  relation_type?: 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many'
  description?: string
  is_active?: boolean
}

// 表关联 API 服务
import api from '@/services/api'

const tableRelationApi = {
  // 获取表关联列表
  getAll: async (
    sourceTableId?: string,
    targetTableId?: string,
    isActive?: boolean,
    page: number = 1,
    pageSize: number = 10
  ): Promise<TableRelation[]> => {
    const params = new URLSearchParams()
    
    if (sourceTableId) params.append('primary_table_id', sourceTableId)
    if (targetTableId) params.append('foreign_table_id', targetTableId)
    if (isActive !== undefined) params.append('status', isActive.toString())
    
    // 分页参数
    params.append('skip', ((page - 1) * pageSize).toString())
    params.append('limit', pageSize.toString())
    
    const response = await api.get('/table-relations', { params })
    return response.data.map((relation: any) => ({
      id: relation.id,
      source_table: relation.primary_table_name,
      source_column: relation.primary_field_name,
      target_table: relation.foreign_table_name,
      target_column: relation.foreign_field_name,
      relation_type: mapJoinTypeToRelationType(relation.join_type),
      is_active: relation.status,
      created_at: relation.created_at
    }))
  },
  
  // 获取单个表关联
  get: async (id: number): Promise<TableRelation> => {
    const response = await api.get(`/api/table-relations/${id}`)
    const relation = response.data
    
    return {
      id: relation.id,
      source_table: relation.primary_table_name,
      source_column: relation.primary_field_name,
      target_table: relation.foreign_table_name,
      target_column: relation.foreign_field_name,
      relation_type: mapJoinTypeToRelationType(relation.join_type),
      is_active: relation.status,
      created_at: relation.created_at
    }
  },
  
  // 创建表关联
  create: async (data: CreateTableRelationRequest): Promise<TableRelation> => {
    const response = await api.post('/table-relations', {
    relation_name: `${data.source_table_id} -> ${data.target_table_id}`,
    primary_table_id: data.source_table_id,
    primary_field_id: data.source_column_id,
    foreign_table_id: data.target_table_id,
    foreign_field_id: data.target_column_id,
    join_type: mapRelationTypeToJoinType(data.relation_type),
    description: data.description,
    created_by: 'user' // This should come from auth context
  })
    
    const relation = response.data
    return {
      id: relation.id,
      source_table: relation.primary_table_name,
      source_column: relation.primary_field_name,
      target_table: relation.foreign_table_name,
      target_column: relation.foreign_field_name,
      relation_type: mapJoinTypeToRelationType(relation.join_type),
      is_active: relation.status,
      created_at: relation.created_at
    }
  },
  
  // 更新表关联
  update: async (id: number, data: UpdateTableRelationRequest): Promise<TableRelation> => {
    const requestBody: any = {}
    
    if (data.source_table_id) requestBody.primary_table_id = data.source_table_id
    if (data.source_column_id) requestBody.primary_field_id = data.source_column_id
    if (data.target_table_id) requestBody.foreign_table_id = data.target_table_id
    if (data.target_column_id) requestBody.foreign_field_id = data.target_column_id
    if (data.relation_type) requestBody.join_type = mapRelationTypeToJoinType(data.relation_type)
    if (data.description !== undefined) requestBody.description = data.description
    if (data.is_active !== undefined) requestBody.status = data.is_active
    
    const response = await api.put(`/api/table-relations/${id}`, requestBody)
    const relation = response.data
    
    return {
      id: relation.id,
      source_table: relation.primary_table_name,
      source_column: relation.primary_field_name,
      target_table: relation.foreign_table_name,
      target_column: relation.foreign_field_name,
      relation_type: mapJoinTypeToRelationType(relation.join_type),
      is_active: relation.status,
      created_at: relation.created_at
    }
  },
  
  // 删除单个表关联
  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/table-relations/${id}`)
  },
  
  // 批量删除表关联
  deleteMultiple: async (ids: number[]): Promise<void> => {
    // Backend doesn't have a bulk delete endpoint, so we need to delete one by one
    const promises = ids.map(id => tableRelationApi.delete(id))
    await Promise.all(promises)
  }
}

// 映射函数：前端类型 <-> 后端类型
function mapRelationTypeToJoinType(relationType: 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many'): string {
  switch (relationType) {
    case 'one_to_one':
      return 'INNER'
    case 'one_to_many':
      return 'LEFT'
    case 'many_to_one':
      return 'RIGHT'
    case 'many_to_many':
      return 'FULL'
    default:
      return 'INNER'
  }
}

function mapJoinTypeToRelationType(joinType: string): 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many' {
  switch (joinType.toUpperCase()) {
    case 'INNER':
      return 'one_to_one'
    case 'LEFT':
      return 'one_to_many'
    case 'RIGHT':
      return 'many_to_one'
    case 'FULL':
      return 'many_to_many'
    default:
      return 'one_to_one'
  }
}

export const useDataPrepStore = defineStore('dataPrep', {
  state: (): DataPrepState => ({
    dataSources: [],
    activeDataSourceId: null,
    dataTables: [],
    dictionaries: [],
    connectionTestResult: null,
    permissions: {
      query: true,
      report: true,
      export: true
    },
    tablePermissions: [],
    
    // 增强的缓存系统
    dataSourceCache: null,
    dataTableCache: new Map(),
    dictionaryCache: null,
    
    // 表关联
    tableRelations: [],
    
    // 预加载状态
    preloadStatus: {
      dataSources: false,
      dataTables: false,
      dictionaries: false
    },
    
    // 性能监控
    performanceMetrics: {
      lastLoadTime: 0,
      averageLoadTime: 0,
      loadCount: 0,
      cacheHitRate: 0,
      totalCacheHits: 0,
      totalCacheRequests: 0
    },
    
    // 加载状态和错误处理
    isLoading: false,
    error: null,
    
    // 数据源专用加载状态和错误
    isLoadingDataSources: false,
    dataSourceError: null
  }),
  
  getters: {
    // 活跃的数据源
    activeDataSource: (state) => {
      return state.dataSources.find(ds => ds.id === state.activeDataSourceId) || null
    },
    
    // 是否有活跃数据源
    hasActiveDataSource: (state) => {
      return state.activeDataSourceId !== null
    },
    
    // 根据数据源ID获取数据表
    getTablesBySourceId: (state) => (sourceId: string) => {
      // 防御性编程：确保 dataTables 是数组
      if (!Array.isArray(state.dataTables)) {
        console.warn('dataTables 不是数组:', state.dataTables)
        return []
      }
      return state.dataTables.filter(t => t.sourceId === sourceId)
    },

    // 根据数据源ID获取数据表（别名方法，用于 Home.vue）
    getDataTablesBySourceId: (state) => (sourceId: string) => {
      // 防御性编程：确保 dataTables 是数组
      if (!Array.isArray(state.dataTables)) {
        console.warn('dataTables 不是数组:', state.dataTables)
        return []
      }
      return state.dataTables.filter(t => t.sourceId === sourceId)
    },
    
    // 字典映射函数 - 优化版本，使用缓存索引
    mapValue: (state) => (rawValue: string | number, tableName: string, fieldName: string): string => {
      // 使用缓存的按表索引来快速查找
      if (state.dictionaryCache?.byTable) {
        const tableEntries = state.dictionaryCache.byTable.get(tableName)
        if (tableEntries) {
          const entry = tableEntries.find(d => d.fieldName === fieldName && d.key === String(rawValue))
          return entry ? entry.value : String(rawValue)
        }
      }
      
      // 回退到原始查找方式
      const entry = state.dictionaries.find(
        d => d.tableName === tableName && 
             d.fieldName === fieldName && 
             d.key === String(rawValue)
      )
      return entry ? entry.value : String(rawValue)
    },
    
    // 性能指标计算
    getCacheEfficiency: (state) => {
      const { totalCacheHits, totalCacheRequests } = state.performanceMetrics
      return totalCacheRequests > 0 ? (totalCacheHits / totalCacheRequests) * 100 : 0
    },
    
    // 获取预加载状态
    getPreloadProgress: (state) => {
      const { dataSources, dataTables, dictionaries } = state.preloadStatus
      const completed = [dataSources, dataTables, dictionaries].filter(Boolean).length
      return (completed / 3) * 100
    }
  },
  
  actions: {
    // ========== 数据源管理 - 性能优化版本 ==========
    
    async loadDataSources(forceRefresh: boolean = false) {
      const startTime = performance.now()
      const uiStore = useUIStore()
      
      // 更新缓存请求统计
      this.performanceMetrics.totalCacheRequests++
      
      // 智能缓存检查：如果缓存存在且未过期，且不强制刷新
      if (!forceRefresh && this.isDataSourceCacheValid()) {
        this.dataSources = [...this.dataSourceCache!.data]
        
        // 设置活跃数据源
        const activeSource = this.dataSources.find(ds => ds.isActive)
        if (activeSource) {
          this.activeDataSourceId = activeSource.id
        }
        
        // 更新缓存命中统计
        this.performanceMetrics.totalCacheHits++
        this.updateCacheHitRate()
        
        // 缓存命中，无需网络请求
        return
      }
      
      // 设置数据源专用加载状态
      this.isLoadingDataSources = true
      this.dataSourceError = null
      
      try {
        const data = await dataSourceApi.getAll()
        
        // 确保 data 是数组，如果不是则使用空数组
        const dataArray = Array.isArray(data) ? data : []
        
        this.dataSources = dataArray.map((ds: any) => ({
          ...ds,
          createdAt: ds.createdAt ? new Date(ds.createdAt).toISOString() : new Date().toISOString(),
          updatedAt: ds.updatedAt ? new Date(ds.updatedAt).toISOString() : new Date().toISOString()
        }))
        
        // 设置活跃数据源
        const activeSource = this.dataSources.find(ds => ds.isActive)
        if (activeSource) {
          this.activeDataSourceId = activeSource.id
        }
        
        // 更新增强缓存
        this.updateDataSourceCache(this.dataSources)
        
        // 更新性能指标
        const loadTime = performance.now() - startTime
        this.updatePerformanceMetrics(loadTime)
        
        // 标记预加载完成
        this.preloadStatus.dataSources = true
        
        // 触发相关数据的预加载
        this.preloadRelatedData()
        
      } catch (error: any) {
        // 增强错误处理
        const errorMessage = error?.response?.data?.detail || error?.message || '加载数据源失败'
        this.dataSourceError = errorMessage
        
        // 记录详细错误日志
        console.error('DataPrep Store - loadDataSources 错误:', {
          message: errorMessage,
          status: error?.response?.status,
          statusText: error?.response?.statusText,
          url: error?.config?.url,
          timestamp: new Date().toISOString(),
          loadTime: performance.now() - startTime
        })
        
        // 显示用户友好的错误提示
        uiStore.showToast(`数据源加载失败: ${errorMessage}`, 'error')
      } finally {
        this.isLoadingDataSources = false
      }
    },
    
    // 预加载相关数据
    async preloadRelatedData() {
      if (this.activeDataSourceId && !this.preloadStatus.dataTables) {
        // 异步预加载数据表，不阻塞主流程
        this.loadDataTables(this.activeDataSourceId).catch(error => {
          console.warn('预加载数据表失败:', error)
        })
      }
      
      if (!this.preloadStatus.dictionaries) {
        // 异步预加载字典数据
        this.loadDictionaries().catch(error => {
          console.warn('预加载字典数据失败:', error)
        })
      }
    },
    
    // 更新数据源缓存
    updateDataSourceCache(data: DataSource[]) {
      const currentVersion = this.dataSourceCache?.version || 0
      this.dataSourceCache = {
        data: [...data],
        timestamp: new Date(),
        version: currentVersion + 1
      }
    },
    
    // 更新性能指标
    updatePerformanceMetrics(loadTime: number) {
      const metrics = this.performanceMetrics
      metrics.lastLoadTime = loadTime
      metrics.loadCount++
      
      // 计算平均加载时间（移动平均）
      if (metrics.loadCount === 1) {
        metrics.averageLoadTime = loadTime
      } else {
        metrics.averageLoadTime = (metrics.averageLoadTime * 0.8) + (loadTime * 0.2)
      }
      
      this.updateCacheHitRate()
    },
    
    // 更新缓存命中率
    updateCacheHitRate() {
      const { totalCacheHits, totalCacheRequests } = this.performanceMetrics
      this.performanceMetrics.cacheHitRate = totalCacheRequests > 0 
        ? (totalCacheHits / totalCacheRequests) * 100 
        : 0
    },
    
    // ========== 权限管理 ==========
    
    updatePermission(permission: keyof DataPrepState['permissions'], value: boolean) {
      this.permissions[permission] = value
      // 在实际应用中，这里应该调用 API 保存到后端
      console.log('Permission updated:', permission, value)
    },
    
    updateTablePermissions(tableIds: string[]) {
      this.tablePermissions = tableIds
      // 在实际应用中，这里应该调用 API 保存到后端
      console.log('Table permissions updated:', tableIds)
    },
    
    async createDataSource(dataSource: Partial<DataSource>) {
      const uiStore = useUIStore()
      try {
        const newDataSource = await dataSourceApi.create(dataSource as CreateDataSourceRequest)
        this.dataSources.push({
          ...newDataSource,
          createdAt: newDataSource.createdAt ? newDataSource.createdAt : new Date().toISOString(),
          updatedAt: newDataSource.updatedAt ? newDataSource.updatedAt : new Date().toISOString()
        })
        
        uiStore.showToast('数据源创建成功', 'success')
        return newDataSource
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async updateDataSource(id: string, updates: Partial<DataSource>) {
      const uiStore = useUIStore()
      try {
        const updatedDataSource = await dataSourceApi.update(id, updates as UpdateDataSourceRequest)
        const index = this.dataSources.findIndex(ds => ds.id === id)
        if (index !== -1) {
          this.dataSources[index] = {
            ...updatedDataSource,
            createdAt: updatedDataSource.createdAt,
            updatedAt: updatedDataSource.updatedAt
          }
        }
        
        uiStore.showToast('数据源更新成功', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async deleteDataSource(id: string) {
      const uiStore = useUIStore()
      try {
        await dataSourceApi.delete(id)
        this.dataSources = this.dataSources.filter(ds => ds.id !== id)
        if (this.activeDataSourceId === id) {
          this.activeDataSourceId = this.dataSources[0]?.id || null
        }
        
        uiStore.showToast('数据源已删除', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async testConnection(connectionConfig: any) {
      const uiStore = useUIStore()
      this.connectionTestResult = null
      
      try {
        const result = await dataSourceApi.testConnection(connectionConfig as ConnectionTestRequest)
        this.connectionTestResult = result
        
        if (result.success) {
          uiStore.showToast('连接测试成功', 'success')
        } else {
          uiStore.showToast(`连接失败：${result.message}`, 'error')
        }
        
        return result
      } catch (error: any) {
        const errorResult = {
          success: false,
          message: error?.message || 'Unknown error'
        }
        this.connectionTestResult = errorResult
        uiStore.showToast(`连接测试失败：${error?.message || 'Unknown error'}`, 'error')
        return errorResult
      }
    },
    
    async activateDataSource(id: string) {
      const uiStore = useUIStore()
      try {
        const updatedDataSource = await dataSourceApi.activate(id)
        
        // 更新所有数据源的激活状态
        this.dataSources = this.dataSources.map(ds => ({
          ...ds,
          isActive: ds.id === id
        }))
        this.activeDataSourceId = id
        
        uiStore.showToast('数据源已激活', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async uploadExcelFile(file: File) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在上传文件...')
      
      try {
        const dataSource = await dataSourceApi.uploadExcel(file)
        this.dataSources.push({
          ...dataSource,
          createdAt: dataSource.createdAt,
          updatedAt: dataSource.updatedAt
        })
        
        // 自动激活新上传的数据源
        await this.activateDataSource(dataSource.id)
        
        uiStore.showToast('文件上传成功', 'success')
        return dataSource
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    // ========== 数据表管理 - 性能优化版本 ==========
    
    async loadDataTables(sourceId?: string, useCache: boolean = true) {
      const uiStore = useUIStore()
      const cacheKey = sourceId || 'all'
      
      // 检查缓存
      if (useCache && this.dataTableCache.has(cacheKey)) {
        const cached = this.dataTableCache.get(cacheKey)!
        const cacheAge = Date.now() - cached.timestamp.getTime()
        
        // 缓存有效期：10分钟
        if (cacheAge < 10 * 60 * 1000) {
          this.dataTables = [...cached.data]
          this.preloadStatus.dataTables = true
          return
        }
      }
      
      try {
        let data: any
        if (sourceId) {
          data = await dataTableApi.getBySourceId(sourceId)
        } else {
          data = await dataTableApi.getAll()
        }
        
        // 确保 data 是数组，如果不是则使用空数组
        let dataArray: DataTable[] = []
        if (Array.isArray(data)) {
          dataArray = data
        } else if (data && typeof data === 'object') {
          // 如果返回的是对象，可能包含 items 或 data 字段
          if (Array.isArray(data.items)) {
            dataArray = data.items
          } else if (Array.isArray(data.data)) {
            dataArray = data.data
          } else {
            console.warn('API 返回的数据格式不正确:', data)
            dataArray = []
          }
        }
        
        this.dataTables = dataArray
        
        // 更新缓存
        this.dataTableCache.set(cacheKey, {
          data: [...dataArray],
          timestamp: new Date(),
          sourceId: sourceId || 'all'
        })
        
        this.preloadStatus.dataTables = true
        
      } catch (error: any) {
        console.error('加载数据表失败:', error)
        // 确保即使出错也设置为空数组，避免 filter 错误
        this.dataTables = []
        uiStore.showToast(error?.message || '加载数据表失败', 'error')
      }
    },
    
    async syncTableStructure(tableId: string) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在同步表结构...')
      
      try {
        const updatedTable = await dataTableApi.syncStructure(tableId)
        const index = this.dataTables.findIndex(t => t.id === tableId)
        if (index !== -1) {
          this.dataTables[index] = updatedTable
        }
        
        uiStore.showToast('表结构同步成功', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    // ========== 字典表管理 - 性能优化版本 ==========
    
    async loadDictionaries(useCache: boolean = true) {
      const uiStore = useUIStore()
      
      // 检查缓存
      if (useCache && this.dictionaryCache) {
        const cacheAge = Date.now() - this.dictionaryCache.timestamp.getTime()
        
        // 缓存有效期：15分钟（字典数据变化较少）
        if (cacheAge < 15 * 60 * 1000) {
          this.dictionaries = [...this.dictionaryCache.data]
          this.preloadStatus.dictionaries = true
          return
        }
      }
      
      try {
        const data = await dictionaryApi.getAll()
        this.dictionaries = data
        
        // 构建按表名的索引缓存
        const byTableIndex = new Map<string, DictionaryEntry[]>()
        data.forEach(entry => {
          if (!byTableIndex.has(entry.tableName)) {
            byTableIndex.set(entry.tableName, [])
          }
          byTableIndex.get(entry.tableName)!.push(entry)
        })
        
        // 更新缓存
        this.dictionaryCache = {
          data: [...data],
          timestamp: new Date(),
          byTable: byTableIndex
        }
        
        this.preloadStatus.dictionaries = true
        
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
      }
    },
    
    async createDictionaryEntry(entry: Omit<DictionaryEntry, 'id'>) {
      const uiStore = useUIStore()
      try {
        const newEntry = await dictionaryApi.create(entry as CreateDictionaryEntryRequest)
        this.dictionaries.push(newEntry)
        
        uiStore.showToast('字典条目创建成功', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async updateDictionaryEntry(id: string, updates: Partial<DictionaryEntry>) {
      const uiStore = useUIStore()
      try {
        const updatedEntry = await dictionaryApi.update(id, updates as UpdateDictionaryEntryRequest)
        const index = this.dictionaries.findIndex(d => d.id === id)
        if (index !== -1) {
          this.dictionaries[index] = updatedEntry
        }
        
        uiStore.showToast('字典条目更新成功', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    async deleteDictionaryEntry(id: string) {
      const uiStore = useUIStore()
      try {
        await dictionaryApi.delete(id)
        this.dictionaries = this.dictionaries.filter(d => d.id !== id)
        
        uiStore.showToast('字典条目已删除', 'success')
      } catch (error: any) {
        uiStore.showToast(error?.message || 'Unknown error', 'error')
        throw error
      }
    },
    
    // ========== 缓存管理 - 增强版本 ==========
    
    // 清空所有缓存
    clearAllCaches() {
      this.dataSourceCache = null
      this.dataTableCache.clear()
      this.dictionaryCache = null
      
      // 重置预加载状态
      this.preloadStatus = {
        dataSources: false,
        dataTables: false,
        dictionaries: false
      }
      
      console.log('所有缓存已清空')
    },
    
    // 智能缓存失效
    invalidateCache(type: 'dataSources' | 'dataTables' | 'dictionaries' | 'all', sourceId?: string) {
      switch (type) {
        case 'dataSources':
          this.dataSourceCache = null
          this.preloadStatus.dataSources = false
          break
          
        case 'dataTables':
          if (sourceId) {
            this.dataTableCache.delete(sourceId)
          } else {
            this.dataTableCache.clear()
          }
          this.preloadStatus.dataTables = false
          break
          
        case 'dictionaries':
          this.dictionaryCache = null
          this.preloadStatus.dictionaries = false
          break
          
        case 'all':
          this.clearAllCaches()
          break
      }
      
      console.log(`缓存失效: ${type}${sourceId ? ` (${sourceId})` : ''}`)
    },
    
    // 缓存预热
    async warmupCache() {
      console.log('开始缓存预热...')
      const startTime = performance.now()
      
      try {
        // 并行预加载核心数据
        await Promise.allSettled([
          this.loadDataSources(),
          this.loadDictionaries()
        ])
        
        // 如果有活跃数据源，预加载其数据表
        if (this.activeDataSourceId) {
          await this.loadDataTables(this.activeDataSourceId)
        }
        
        const warmupTime = performance.now() - startTime
        console.log(`缓存预热完成，耗时: ${warmupTime.toFixed(2)}ms`)
        
      } catch (error) {
        console.error('缓存预热失败:', error)
      }
    },
    
    // 清空数据源缓存
    clearDataSourceCache() {
      this.dataSourceCache = null
      this.preloadStatus.dataSources = false
    },
    
    // 重置数据源状态
    resetDataSourceState() {
      this.dataSources = []
      this.activeDataSourceId = null
      this.isLoadingDataSources = false
      this.dataSourceError = null
      this.dataSourceCache = null
      this.preloadStatus.dataSources = false
    },
    
    // 检查缓存是否有效 - 增强版本
    isDataSourceCacheValid(): boolean {
      if (!this.dataSourceCache) return false
      
      const cacheAge = Date.now() - this.dataSourceCache.timestamp.getTime()
      const maxAge = 5 * 60 * 1000 // 5分钟有效期
      
      return cacheAge < maxAge
    },
    
    // 获取缓存统计信息
    getCacheStats() {
      const dataSourceCacheSize = this.dataSourceCache?.data.length || 0
      const dataTableCacheSize = Array.from(this.dataTableCache.values())
        .reduce((total, cache) => total + cache.data.length, 0)
      const dictionaryCacheSize = this.dictionaryCache?.data.length || 0
      
      return {
        dataSources: {
          cached: !!this.dataSourceCache,
          size: dataSourceCacheSize,
          age: this.dataSourceCache ? Date.now() - this.dataSourceCache.timestamp.getTime() : 0
        },
        dataTables: {
          cacheCount: this.dataTableCache.size,
          totalSize: dataTableCacheSize
        },
        dictionaries: {
          cached: !!this.dictionaryCache,
          size: dictionaryCacheSize,
          indexedTables: this.dictionaryCache?.byTable.size || 0
        },
        performance: { ...this.performanceMetrics }
      }
    },
    
    // ========== 表关联管理 ==========
    
    async fetchTableRelations(
      sourceTableId?: string,
      targetTableId?: string,
      isActive?: boolean,
      page: number = 1,
      pageSize: number = 10
    ) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在加载表关联数据...')
      
      try {
        const relations = await tableRelationApi.getAll(
          sourceTableId,
          targetTableId,
          isActive,
          page,
          pageSize
        )
        this.tableRelations = relations
      } catch (error: any) {
        uiStore.showToast('获取表关联数据失败，请稍后重试', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    async createTableRelation(data: CreateTableRelationRequest) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在创建表关联...')
      
      try {
        const relation = await tableRelationApi.create(data)
        this.tableRelations.push(relation)
        
        uiStore.showToast('表关联创建成功', 'success')
        return relation
      } catch (error: any) {
        uiStore.showToast('创建表关联失败，请稍后重试', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    async updateTableRelation(id: number, data: UpdateTableRelationRequest) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在更新表关联...')
      
      try {
        const updatedRelation = await tableRelationApi.update(id, data)
        const index = this.tableRelations.findIndex(r => r.id === id)
        if (index !== -1) {
          this.tableRelations[index] = updatedRelation
        }
        
        uiStore.showToast('表关联更新成功', 'success')
        return updatedRelation
      } catch (error: any) {
        uiStore.showToast('更新表关联失败，请稍后重试', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    async deleteTableRelation(id: number) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在删除表关联...')
      
      try {
        await tableRelationApi.delete(id)
        this.tableRelations = this.tableRelations.filter(r => r.id !== id)
        
        uiStore.showToast('表关联已删除', 'success')
      } catch (error: any) {
        uiStore.showToast('删除表关联失败，请稍后重试', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    },
    
    async deleteTableRelations(ids: number[]) {
      const uiStore = useUIStore()
      uiStore.setLoading(true, '正在批量删除表关联...')
      
      try {
        await tableRelationApi.deleteMultiple(ids)
        this.tableRelations = this.tableRelations.filter(r => !ids.includes(r.id))
        
        uiStore.showToast(`成功删除 ${ids.length} 个表关联`, 'success')
      } catch (error: any) {
        uiStore.showToast('批量删除表关联失败，请稍后重试', 'error')
        throw error
      } finally {
        uiStore.setLoading(false)
      }
    }
  }
})
