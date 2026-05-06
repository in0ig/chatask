import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataSourceApi } from '@/api/chatbiDataSourceApi'
import type { DataSource, DataSourceConfig, ConnectionTestResult } from '@/types/dataSource'

export const useDataSourceStore = defineStore('dataSource', () => {
  // 状态
  const dataSourceList = ref<DataSource[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const activeDataSources = computed(() => 
    dataSourceList.value.filter(ds => ds.status === 'active')
  )

  const dataSourceCount = computed(() => dataSourceList.value.length)

  // 获取数据源列表
  const fetchDataSources = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await dataSourceApi.getDataSources()
      dataSourceList.value = response.data
    } catch (err) {
      error.value = '获取数据源列表失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 创建数据源
  const createDataSource = async (config: DataSourceConfig): Promise<any> => {
    loading.value = true
    error.value = null
    
    try {
      const newDataSource = await dataSourceApi.createDataSource(config)
      dataSourceList.value.push(newDataSource)
      return newDataSource
    } catch (err) {
      error.value = '创建数据源失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 更新数据源
  const updateDataSource = async (id: string, config: DataSourceConfig): Promise<DataSource> => {
    loading.value = true
    error.value = null
    
    try {
      const response = await dataSourceApi.updateDataSource(id, config)
      const updatedDataSource = response.data
      
      const index = dataSourceList.value.findIndex(ds => ds.id === id)
      if (index !== -1) {
        dataSourceList.value[index] = updatedDataSource
      }
      
      return updatedDataSource
    } catch (err) {
      error.value = '更新数据源失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 删除数据源
  const deleteDataSource = async (id: string): Promise<void> => {
    loading.value = true
    error.value = null
    
    try {
      await dataSourceApi.deleteDataSource(id)
      const index = dataSourceList.value.findIndex(ds => ds.id === id)
      if (index !== -1) {
        dataSourceList.value.splice(index, 1)
      }
    } catch (err) {
      error.value = '删除数据源失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 测试连接
  const testConnection = async (config: DataSourceConfig): Promise<ConnectionTestResult> => {
    try {
      const response = await dataSourceApi.testConnection(config)
      return response
    } catch (err) {
      throw err
    }
  }

  // 更新数据源状态
  const updateDataSourceStatus = async (id: string, status: 'active' | 'inactive' | 'error'): Promise<void> => {
    const dataSource = dataSourceList.value.find(ds => ds.id === id)
    if (dataSource) {
      dataSource.status = status
      dataSource.updatedAt = new Date()
    } else {
      console.warn(`Data source with id ${id} not found in store. Available IDs:`, dataSourceList.value.map(ds => ds.id))
      // 如果找不到数据源，重新加载数据源列表
      await fetchDataSources()
      // 再次尝试更新状态
      const retryDataSource = dataSourceList.value.find(ds => ds.id === id)
      if (retryDataSource) {
        retryDataSource.status = status
        retryDataSource.updatedAt = new Date()
      } else {
        console.error(`Data source with id ${id} still not found after refresh`)
      }
    }
  }

  // 根据ID获取数据源
  const getDataSourceById = (id: string): DataSource | undefined => {
    return dataSourceList.value.find(ds => ds.id === id)
  }

  // 根据类型获取数据源
  const getDataSourcesByType = (type: 'mysql' | 'sqlserver'): DataSource[] => {
    return dataSourceList.value.filter(ds => ds.type === type)
  }

  // 清除错误
  const clearError = () => {
    error.value = null
  }

  // 重置状态
  const resetState = () => {
    dataSourceList.value = []
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    dataSourceList,
    loading,
    error,
    
    // 计算属性
    activeDataSources,
    dataSourceCount,
    
    // 方法
    fetchDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    testConnection,
    updateDataSourceStatus,
    getDataSourceById,
    getDataSourcesByType,
    clearError,
    resetState
  }
})