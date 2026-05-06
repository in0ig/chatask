/**
 * 数据准备状态管理 - 简化版本
 * 
 * 专注于任务 3.6 - 字典 Mock 数据迁移到真实数据库
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { 
  DataSource, 
  DataTable, 
  Dictionary, 
  DictionaryItem, 
  TableRelation,
  TableField,
  FieldMapping
} from '@/types/dataPreparation'
import { dictionaryApi } from '@/api/dictionaryApi'
import { dataSourceApi } from '@/api/dataSourceApi'
import { dataTableApi } from '@/api/dataTableApi'
import { relationApi } from '@/api/relationApi'
import { fieldMappingApi } from '@/api/fieldMappingApi'

export const useDataPreparationStore = defineStore('dataPreparation', () => {
  // State
  const dataSources = ref<DataSource[]>([])
  const dataTables = ref<DataTable[]>([])
  const dictionaries = ref<Dictionary[]>([])
  const dictionaryItems = ref<DictionaryItem[]>([])
  const relations = ref<TableRelation[]>([])
  const tableFields = ref<TableField[]>([])
  const fieldMappings = ref<FieldMapping[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const getDictionaryById = computed(() => {
    return (id: string) => dictionaries.value.find(dict => dict.id === id)
  })

  const getDictionaryItemsByDictionaryId = computed(() => {
    return (dictionaryId: string) => 
      dictionaryItems.value.filter(item => item.dictionary_id === dictionaryId)
  })

  const getDataSourceById = computed(() => {
    return (id: number) => dataSources.value.find(ds => ds.id === id)
  })

  const getDataTableById = computed(() => {
    return (id: number) => dataTables.value.find(dt => dt.id === id)
  })

  const getRelationsByTableId = computed(() => {
    return (tableId: number) => 
      relations.value.filter(rel => rel.source_table_id === tableId || rel.target_table_id === tableId)
  })

  const getFieldsByTableId = computed(() => {
    return (tableId: number) => 
      tableFields.value.filter(field => field.table_id === tableId)
  })

  const getFieldMappingsByTableId = computed(() => {
    return (tableId: number) => 
      fieldMappings.value.filter(mapping => mapping.table_id === tableId)
  })

  // Dictionary Actions - 使用真实API而非mock数据
  const fetchDictionaries = async (): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.getDictionaries()
      dictionaries.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch dictionaries'
      console.error('Error fetching dictionaries:', err)
    } finally {
      loading.value = false
    }
  }

  const createDictionary = async (dictionary: Omit<Dictionary, 'id' | 'created_at' | 'updated_at'>): Promise<Dictionary | null> => {
    try {
      loading.value = true
      error.value = null
      console.log('🏪 Store - createDictionary: starting, dictionary:', dictionary)
      console.log('🏪 Store - createDictionary: dictionaries count before:', dictionaries.value.length)
      
      const response = await dictionaryApi.createDictionary(dictionary)
      console.log('🏪 Store - createDictionary: API response:', response)
      
      if (response.data) {
        console.log('🏪 Store - createDictionary: pushing to dictionaries array:', response.data)
        dictionaries.value.push(response.data)
        console.log('🏪 Store - createDictionary: dictionaries count after push:', dictionaries.value.length)
        console.log('🏪 Store - createDictionary: dictionaries array:', dictionaries.value)
        return response.data
      }
      console.log('🏪 Store - createDictionary: no data in response')
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create dictionary'
      console.error('❌ Store - createDictionary: error:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateDictionary = async (id: string, dictionary: Partial<Dictionary>): Promise<Dictionary | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.updateDictionary(id, dictionary)
      if (response.data) {
        const index = dictionaries.value.findIndex(d => d.id === id)
        if (index !== -1) {
          dictionaries.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update dictionary'
      console.error('Error updating dictionary:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteDictionary = async (id: string): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await dictionaryApi.deleteDictionary(id)
      dictionaries.value = dictionaries.value.filter(d => d.id !== id)
      // 同时删除相关的字典项
      dictionaryItems.value = dictionaryItems.value.filter(item => item.dictionary_id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete dictionary'
      console.error('Error deleting dictionary:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Dictionary Items Actions - 使用真实API而非mock数据
  const fetchDictionaryItems = async (dictionaryId?: string): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      console.log('🔄 Store - fetchDictionaryItems: starting for dictionaryId:', dictionaryId)
      
      const response = dictionaryId 
        ? await dictionaryApi.getDictionaryItems(dictionaryId)
        : await dictionaryApi.getAllDictionaryItems()
      
      console.log('📡 Store - fetchDictionaryItems: API response:', response)
      dictionaryItems.value = response.data || []
      console.log('✅ Store - fetchDictionaryItems: updated dictionaryItems, count:', dictionaryItems.value.length)
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch dictionary items'
      console.error('❌ Store - fetchDictionaryItems: error:', err)
    } finally {
      loading.value = false
    }
  }

  const createDictionaryItem = async (item: Omit<DictionaryItem, 'id' | 'created_at' | 'updated_at'>): Promise<DictionaryItem | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.createDictionaryItem(item)
      if (response.data) {
        dictionaryItems.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create dictionary item'
      console.error('Error creating dictionary item:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateDictionaryItem = async (id: string, item: Partial<DictionaryItem>): Promise<DictionaryItem | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.updateDictionaryItem(id, item)
      if (response.data) {
        const index = dictionaryItems.value.findIndex(i => i.id === id)
        if (index !== -1) {
          dictionaryItems.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update dictionary item'
      console.error('Error updating dictionary item:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteDictionaryItem = async (id: string, dictionaryId: string): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await dictionaryApi.deleteDictionaryItem(id, dictionaryId)
      dictionaryItems.value = dictionaryItems.value.filter(i => i.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete dictionary item'
      console.error('Error deleting dictionary item:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Dictionary Import/Export Actions - 使用真实API
  const importDictionary = async (file: File): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.importDictionary(file)
      if (response.success) {
        // 重新获取字典数据
        await fetchDictionaries()
        await fetchDictionaryItems()
        return true
      }
      return false
    } catch (err: any) {
      error.value = err.message || 'Failed to import dictionary'
      console.error('Error importing dictionary:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  const exportDictionary = async (dictionaryId: string): Promise<Blob | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dictionaryApi.exportDictionary(dictionaryId)
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to export dictionary'
      console.error('Error exporting dictionary:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  // Data Source Actions
  const fetchDataSources = async (): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataSourceApi.getDataSources()
      dataSources.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch data sources'
      console.error('Error fetching data sources:', err)
    } finally {
      loading.value = false
    }
  }

  const createDataSource = async (dataSource: Omit<DataSource, 'id' | 'created_at' | 'updated_at'>): Promise<DataSource | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataSourceApi.createDataSource(dataSource)
      if (response.data) {
        dataSources.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create data source'
      console.error('Error creating data source:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateDataSource = async (id: number, dataSource: Partial<DataSource>): Promise<DataSource | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataSourceApi.updateDataSource(id, dataSource)
      if (response.data) {
        const index = dataSources.value.findIndex(ds => ds.id === id)
        if (index !== -1) {
          dataSources.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update data source'
      console.error('Error updating data source:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteDataSource = async (id: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await dataSourceApi.deleteDataSource(id)
      dataSources.value = dataSources.value.filter(ds => ds.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete data source'
      console.error('Error deleting data source:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  const testDataSourceConnection = async (dataSource: Partial<DataSource>): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataSourceApi.testConnection(dataSource)
      return response.success || false
    } catch (err: any) {
      error.value = err.message || 'Failed to test connection'
      console.error('Error testing connection:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Data Table Actions
  const fetchDataTables = async (dataSourceId?: number): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = dataSourceId 
        ? await dataTableApi.getDataTablesByDataSource(dataSourceId)
        : await dataTableApi.getDataTables()
      dataTables.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch data tables'
      console.error('Error fetching data tables:', err)
    } finally {
      loading.value = false
    }
  }

  const createDataTable = async (dataTable: Omit<DataTable, 'id' | 'created_at' | 'updated_at'>): Promise<DataTable | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataTableApi.createDataTable(dataTable)
      if (response.data) {
        dataTables.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create data table'
      console.error('Error creating data table:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateDataTable = async (id: number, dataTable: Partial<DataTable>): Promise<DataTable | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataTableApi.updateDataTable(id, dataTable)
      if (response.data) {
        const index = dataTables.value.findIndex(dt => dt.id === id)
        if (index !== -1) {
          dataTables.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update data table'
      console.error('Error updating data table:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteDataTable = async (id: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await dataTableApi.deleteDataTable(id)
      dataTables.value = dataTables.value.filter(dt => dt.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete data table'
      console.error('Error deleting data table:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Table Relations Actions
  const fetchRelations = async (tableId?: number): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = tableId 
        ? await relationApi.getRelationsByTable(tableId)
        : await relationApi.getRelations()
      relations.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch relations'
      console.error('Error fetching relations:', err)
    } finally {
      loading.value = false
    }
  }

  const createRelation = async (relation: Omit<TableRelation, 'id' | 'created_at' | 'updated_at'>): Promise<TableRelation | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await relationApi.createRelation(relation)
      if (response.data) {
        relations.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create relation'
      console.error('Error creating relation:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateRelation = async (id: number, relation: Partial<TableRelation>): Promise<TableRelation | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await relationApi.updateRelation(id, relation)
      if (response.data) {
        const index = relations.value.findIndex(r => r.id === id)
        if (index !== -1) {
          relations.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update relation'
      console.error('Error updating relation:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteRelation = async (id: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await relationApi.deleteRelation(id)
      relations.value = relations.value.filter(r => r.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete relation'
      console.error('Error deleting relation:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Table Fields Actions
  const fetchTableFields = async (tableId?: number): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = tableId 
        ? await dataTableApi.getTableFields(tableId)
        : await dataTableApi.getAllTableFields()
      tableFields.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch table fields'
      console.error('Error fetching table fields:', err)
    } finally {
      loading.value = false
    }
  }

  const createTableField = async (field: Omit<TableField, 'id' | 'created_at' | 'updated_at'>): Promise<TableField | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataTableApi.createTableField(field)
      if (response.data) {
        tableFields.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create table field'
      console.error('Error creating table field:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateTableField = async (id: number, field: Partial<TableField>): Promise<TableField | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await dataTableApi.updateTableField(id, field)
      if (response.data) {
        const index = tableFields.value.findIndex(f => f.id === id)
        if (index !== -1) {
          tableFields.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update table field'
      console.error('Error updating table field:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteTableField = async (id: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await dataTableApi.deleteTableField(id)
      tableFields.value = tableFields.value.filter(f => f.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete table field'
      console.error('Error deleting table field:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Field Mappings Actions
  const fetchFieldMappings = async (tableId?: number): Promise<void> => {
    try {
      loading.value = true
      error.value = null
      const response = tableId 
        ? await fieldMappingApi.getFieldMappingsByTable(tableId)
        : await fieldMappingApi.getFieldMappings()
      fieldMappings.value = response.data || []
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch field mappings'
      console.error('Error fetching field mappings:', err)
    } finally {
      loading.value = false
    }
  }

  const createFieldMapping = async (mapping: Omit<FieldMapping, 'id' | 'created_at' | 'updated_at'>): Promise<FieldMapping | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.createFieldMapping(mapping)
      if (response.data) {
        fieldMappings.value.push(response.data)
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to create field mapping'
      console.error('Error creating field mapping:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const updateFieldMapping = async (id: number, mapping: Partial<FieldMapping>): Promise<FieldMapping | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.updateFieldMapping(id, mapping)
      if (response.data) {
        const index = fieldMappings.value.findIndex(m => m.id === id)
        if (index !== -1) {
          fieldMappings.value[index] = response.data
        }
        return response.data
      }
      return null
    } catch (err: any) {
      error.value = err.message || 'Failed to update field mapping'
      console.error('Error updating field mapping:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteFieldMapping = async (id: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await fieldMappingApi.deleteFieldMapping(id)
      fieldMappings.value = fieldMappings.value.filter(m => m.id !== id)
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to delete field mapping'
      console.error('Error deleting field mapping:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Batch Field Mapping Actions
  const batchCreateFieldMappings = async (mappings: Omit<FieldMapping, 'id' | 'created_at' | 'updated_at'>[]): Promise<FieldMapping[]> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.batchCreateFieldMappings(mappings)
      if (response.data) {
        fieldMappings.value.push(...response.data)
        return response.data
      }
      return []
    } catch (err: any) {
      error.value = err.message || 'Failed to batch create field mappings'
      console.error('Error batch creating field mappings:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const batchUpdateFieldMappings = async (updates: { id: number; data: Partial<FieldMapping> }[]): Promise<FieldMapping[]> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.batchUpdateFieldMappings(updates)
      if (response.data) {
        // 更新本地状态
        response.data.forEach((updatedMapping: FieldMapping) => {
          const index = fieldMappings.value.findIndex(m => m.id === updatedMapping.id)
          if (index !== -1) {
            fieldMappings.value[index] = updatedMapping
          }
        })
        return response.data
      }
      return []
    } catch (err: any) {
      error.value = err.message || 'Failed to batch update field mappings'
      console.error('Error batch updating field mappings:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const batchDeleteFieldMappings = async (ids: number[]): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      await fieldMappingApi.batchDeleteFieldMappings(ids)
      fieldMappings.value = fieldMappings.value.filter(m => !ids.includes(m.id!))
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to batch delete field mappings'
      console.error('Error batch deleting field mappings:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Field Mapping Import/Export Actions
  const importFieldMappings = async (file: File, tableId: number): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.importFieldMappings(file, tableId)
      if (response.success) {
        // 重新获取字段映射数据
        await fetchFieldMappings(tableId)
        return true
      }
      return false
    } catch (err: any) {
      error.value = err.message || 'Failed to import field mappings'
      console.error('Error importing field mappings:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  const exportFieldMappings = async (tableId: number): Promise<Blob | null> => {
    try {
      loading.value = true
      error.value = null
      const response = await fieldMappingApi.exportFieldMappings(tableId)
      return response
    } catch (err: any) {
      error.value = err.message || 'Failed to export field mappings'
      console.error('Error exporting field mappings:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  // Batch Dictionary Items Actions
  const batchCreateDictionaryItems = async (dictionaryId: string, items: Array<{ key: string, value: string, description?: string }>): Promise<DictionaryItem[]> => {
    try {
      loading.value = true
      error.value = null
      const itemsToCreate = items.map(item => ({
        dictionary_id: dictionaryId,
        item_key: item.key,
        item_value: item.value,
        description: item.description,
        sort_order: 0,
        status: true
      }))
      
      const results: DictionaryItem[] = []
      for (const item of itemsToCreate) {
        const response = await dictionaryApi.createDictionaryItem(item)
        if (response.data) {
          results.push(response.data)
          dictionaryItems.value.push(response.data)
        }
      }
      return results
    } catch (err: any) {
      error.value = err.message || 'Failed to batch create dictionary items'
      console.error('Error batch creating dictionary items:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const batchUpdateDictionaryItems = async (ids: string[], updates: Partial<DictionaryItem>): Promise<DictionaryItem[]> => {
    try {
      loading.value = true
      error.value = null
      const results: DictionaryItem[] = []
      
      for (const id of ids) {
        const response = await dictionaryApi.updateDictionaryItem(id, updates)
        if (response.data) {
          results.push(response.data)
          const index = dictionaryItems.value.findIndex(i => i.id === id)
          if (index !== -1) {
            dictionaryItems.value[index] = response.data
          }
        }
      }
      return results
    } catch (err: any) {
      error.value = err.message || 'Failed to batch update dictionary items'
      console.error('Error batch updating dictionary items:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const updateDictionaryItemsSort = async (dictionaryId: string, sortUpdates: Array<{ id: string, sortOrder: number }>): Promise<boolean> => {
    try {
      loading.value = true
      error.value = null
      
      for (const update of sortUpdates) {
        const response = await dictionaryApi.updateDictionaryItem(update.id, { sort_order: update.sortOrder })
        if (response.data) {
          const index = dictionaryItems.value.findIndex(i => i.id === update.id)
          if (index !== -1) {
            dictionaryItems.value[index] = response.data
          }
        }
      }
      return true
    } catch (err: any) {
      error.value = err.message || 'Failed to update dictionary items sort order'
      console.error('Error updating dictionary items sort order:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  // Utility Actions
  const clearError = (): void => {
    error.value = null
  }

  const resetState = (): void => {
    dataSources.value = []
    dataTables.value = []
    dictionaries.value = []
    dictionaryItems.value = []
    relations.value = []
    tableFields.value = []
    fieldMappings.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    dataSources,
    dataTables,
    dictionaries,
    dictionaryItems,
    relations,
    tableFields,
    fieldMappings,
    loading,
    error,
    
    // Computed
    getDictionaryById,
    getDictionaryItemsByDictionaryId,
    getDataSourceById,
    getDataTableById,
    getRelationsByTableId,
    getFieldsByTableId,
    getFieldMappingsByTableId,
    
    // Dictionary Actions
    fetchDictionaries,
    createDictionary,
    updateDictionary,
    deleteDictionary,
    
    // Dictionary Items Actions
    fetchDictionaryItems,
    createDictionaryItem,
    updateDictionaryItem,
    deleteDictionaryItem,
    
    // Dictionary Import/Export Actions
    importDictionary,
    exportDictionary,
    
    // Data Source Actions
    fetchDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    testDataSourceConnection,
    
    // Data Table Actions
    fetchDataTables,
    createDataTable,
    updateDataTable,
    deleteDataTable,
    
    // Table Relations Actions
    fetchRelations,
    createRelation,
    updateRelation,
    deleteRelation,
    
    // Table Fields Actions
    fetchTableFields,
    createTableField,
    updateTableField,
    deleteTableField,
    
    // Field Mappings Actions
    fetchFieldMappings,
    createFieldMapping,
    updateFieldMapping,
    deleteFieldMapping,
    
    // Batch Field Mapping Actions
    batchCreateFieldMappings,
    batchUpdateFieldMappings,
    batchDeleteFieldMappings,
    
    // Field Mapping Import/Export Actions
    importFieldMappings,
    exportFieldMappings,
    
    // Batch Dictionary Items Actions
    batchCreateDictionaryItems,
    batchUpdateDictionaryItems,
    updateDictionaryItemsSort,
    
    // Utility Actions
    clearError,
    resetState
  }
})