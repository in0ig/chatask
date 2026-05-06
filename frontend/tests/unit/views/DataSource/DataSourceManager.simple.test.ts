import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDataSourceStore } from '@/store/modules/dataSource'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn()
  }
}))

describe('DataSourceManager - 逻辑测试', () => {
  let store: any

  const mockDataSources = [
    {
      id: '1',
      name: 'MySQL测试数据源',
      type: 'mysql',
      config: {
        host: 'localhost',
        port: 3306,
        database: 'test_db',
        username: 'root',
        password: 'password',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      },
      status: 'active',
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-01')
    }
  ]

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataSourceStore()
    
    // Mock store methods
    store.fetchDataSources = vi.fn().mockResolvedValue(undefined)
    store.createDataSource = vi.fn().mockResolvedValue(mockDataSources[0])
    store.updateDataSource = vi.fn().mockResolvedValue(mockDataSources[0])
    store.deleteDataSource = vi.fn().mockResolvedValue(undefined)
    store.testConnection = vi.fn().mockResolvedValue({ success: true })
    store.updateDataSourceStatus = vi.fn().mockResolvedValue(undefined)
    
    // Set initial data
    store.dataSourceList = mockDataSources
  })

  describe('Store 集成', () => {
    it('应该能够获取数据源列表', async () => {
      await store.fetchDataSources()
      expect(store.fetchDataSources).toHaveBeenCalled()
    })

    it('应该能够创建数据源', async () => {
      const config = {
        name: '新数据源',
        type: 'mysql',
        host: 'localhost',
        port: 3306,
        database: 'new_db',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }
      
      const result = await store.createDataSource(config)
      expect(store.createDataSource).toHaveBeenCalledWith(config)
      expect(result).toEqual(mockDataSources[0])
    })

    it('应该能够测试连接', async () => {
      const config = mockDataSources[0].config
      const result = await store.testConnection(config)
      
      expect(store.testConnection).toHaveBeenCalledWith(config)
      expect(result.success).toBe(true)
    })
  })

  describe('状态管理', () => {
    it('应该正确管理数据源状态', () => {
      expect(store.dataSourceList).toEqual(mockDataSources)
      expect(store.dataSourceCount).toBe(1)
      expect(store.activeDataSources).toHaveLength(1)
    })

    it('应该能够根据ID获取数据源', () => {
      const dataSource = store.getDataSourceById('1')
      expect(dataSource).toEqual(mockDataSources[0])
    })

    it('应该能够根据类型获取数据源', () => {
      const mysqlSources = store.getDataSourcesByType('mysql')
      expect(mysqlSources).toHaveLength(1)
      expect(mysqlSources[0].type).toBe('mysql')
    })
  })
})