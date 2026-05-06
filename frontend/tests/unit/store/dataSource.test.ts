import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataSourceStore } from '@/store/modules/dataSource'
import { dataSourceApi } from '@/api/chatbiDataSourceApi'
import type { DataSource, DataSourceConfig } from '@/types/dataSource'

// Mock API
vi.mock('@/api/chatbiDataSourceApi', () => ({
  dataSourceApi: {
    getDataSources: vi.fn(),
    createDataSource: vi.fn(),
    updateDataSource: vi.fn(),
    deleteDataSource: vi.fn(),
    testConnection: vi.fn(),
    getConnectionPoolStatus: vi.fn(),
    resetConnectionPool: vi.fn()
  }
}))

describe('DataSource Store', () => {
  let store: ReturnType<typeof useDataSourceStore>

  const mockDataSources: DataSource[] = [
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
    },
    {
      id: '2',
      name: 'SQL Server测试数据源',
      type: 'sqlserver',
      config: {
        host: '192.168.1.100',
        port: 1433,
        database: 'test_db',
        username: 'sa',
        password: 'password',
        connectionPool: {
          min: 3,
          max: 15,
          timeout: 60
        }
      },
      status: 'inactive',
      createdAt: new Date('2024-01-02'),
      updatedAt: new Date('2024-01-02')
    }
  ]

  const mockConfig: DataSourceConfig = {
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

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataSourceStore()
    vi.clearAllMocks()
  })

  describe('初始状态', () => {
    it('应该有正确的初始状态', () => {
      expect(store.dataSourceList).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('计算属性', () => {
    beforeEach(() => {
      store.dataSourceList = mockDataSources
    })

    it('应该正确计算活跃数据源', () => {
      expect(store.activeDataSources).toHaveLength(1)
      expect(store.activeDataSources[0].status).toBe('active')
    })

    it('应该正确计算数据源总数', () => {
      expect(store.dataSourceCount).toBe(2)
    })
  })

  describe('获取数据源列表', () => {
    it('应该成功获取数据源列表', async () => {
      vi.mocked(dataSourceApi.getDataSources).mockResolvedValue({
        data: mockDataSources,
        total: mockDataSources.length
      })

      await store.fetchDataSources()

      expect(dataSourceApi.getDataSources).toHaveBeenCalled()
      expect(store.dataSourceList).toEqual(mockDataSources)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('应该处理获取数据源列表失败', async () => {
      const error = new Error('网络错误')
      vi.mocked(dataSourceApi.getDataSources).mockRejectedValue(error)

      await expect(store.fetchDataSources()).rejects.toThrow(error)
      expect(store.error).toBe('获取数据源列表失败')
      expect(store.loading).toBe(false)
    })
  })

  describe('创建数据源', () => {
    it('应该成功创建数据源', async () => {
      const newDataSource = { ...mockDataSources[0], id: '3', name: '新数据源' }
      vi.mocked(dataSourceApi.createDataSource).mockResolvedValue({
        data: newDataSource
      })

      const result = await store.createDataSource(mockConfig)

      expect(dataSourceApi.createDataSource).toHaveBeenCalledWith(mockConfig)
      expect(result).toEqual(newDataSource)
      expect(store.dataSourceList).toHaveLength(1)
      expect(store.dataSourceList[0]).toEqual(newDataSource)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('应该处理创建数据源失败', async () => {
      const error = new Error('创建失败')
      vi.mocked(dataSourceApi.createDataSource).mockRejectedValue(error)

      await expect(store.createDataSource(mockConfig)).rejects.toThrow(error)
      expect(store.error).toBe('创建数据源失败')
      expect(store.loading).toBe(false)
    })
  })

  describe('更新数据源', () => {
    beforeEach(() => {
      store.dataSourceList = [...mockDataSources]
    })

    it('应该成功更新数据源', async () => {
      const updatedDataSource = { ...mockDataSources[0], name: '更新后的数据源' }
      vi.mocked(dataSourceApi.updateDataSource).mockResolvedValue({
        data: updatedDataSource
      })

      const result = await store.updateDataSource('1', mockConfig)

      expect(dataSourceApi.updateDataSource).toHaveBeenCalledWith('1', mockConfig)
      expect(result).toEqual(updatedDataSource)
      expect(store.dataSourceList[0]).toEqual(updatedDataSource)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('应该处理更新数据源失败', async () => {
      const error = new Error('更新失败')
      vi.mocked(dataSourceApi.updateDataSource).mockRejectedValue(error)

      await expect(store.updateDataSource('1', mockConfig)).rejects.toThrow(error)
      expect(store.error).toBe('更新数据源失败')
      expect(store.loading).toBe(false)
    })
  })

  describe('删除数据源', () => {
    beforeEach(() => {
      store.dataSourceList = [...mockDataSources]
    })

    it('应该成功删除数据源', async () => {
      vi.mocked(dataSourceApi.deleteDataSource).mockResolvedValue(undefined)

      await store.deleteDataSource('1')

      expect(dataSourceApi.deleteDataSource).toHaveBeenCalledWith('1')
      expect(store.dataSourceList).toHaveLength(1)
      expect(store.dataSourceList.find(ds => ds.id === '1')).toBeUndefined()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('应该处理删除数据源失败', async () => {
      const error = new Error('删除失败')
      vi.mocked(dataSourceApi.deleteDataSource).mockRejectedValue(error)

      await expect(store.deleteDataSource('1')).rejects.toThrow(error)
      expect(store.error).toBe('删除数据源失败')
      expect(store.loading).toBe(false)
    })
  })

  describe('测试连接', () => {
    it('应该成功测试连接', async () => {
      const testResult = { success: true, message: '连接成功' }
      vi.mocked(dataSourceApi.testConnection).mockResolvedValue({
        data: testResult
      })

      const result = await store.testConnection(mockConfig)

      expect(dataSourceApi.testConnection).toHaveBeenCalledWith(mockConfig)
      expect(result).toEqual(testResult)
    })

    it('应该处理测试连接失败', async () => {
      const error = new Error('连接失败')
      vi.mocked(dataSourceApi.testConnection).mockRejectedValue(error)

      await expect(store.testConnection(mockConfig)).rejects.toThrow(error)
    })
  })

  describe('更新数据源状态', () => {
    beforeEach(() => {
      store.dataSourceList = [...mockDataSources]
    })

    it('应该成功更新数据源状态', async () => {
      await store.updateDataSourceStatus('1', 'error')

      const dataSource = store.dataSourceList.find(ds => ds.id === '1')
      expect(dataSource?.status).toBe('error')
      expect(dataSource?.updatedAt).toBeInstanceOf(Date)
    })

    it('应该处理不存在的数据源ID', async () => {
      await store.updateDataSourceStatus('999', 'active')
      
      // 不应该抛出错误，但也不应该有任何变化
      expect(store.dataSourceList).toEqual(mockDataSources)
    })
  })

  describe('查询方法', () => {
    beforeEach(() => {
      store.dataSourceList = [...mockDataSources]
    })

    it('应该根据ID获取数据源', () => {
      const dataSource = store.getDataSourceById('1')
      expect(dataSource).toEqual(mockDataSources[0])
    })

    it('应该处理不存在的数据源ID', () => {
      const dataSource = store.getDataSourceById('999')
      expect(dataSource).toBeUndefined()
    })

    it('应该根据类型获取数据源', () => {
      const mysqlSources = store.getDataSourcesByType('mysql')
      expect(mysqlSources).toHaveLength(1)
      expect(mysqlSources[0].type).toBe('mysql')

      const sqlServerSources = store.getDataSourcesByType('sqlserver')
      expect(sqlServerSources).toHaveLength(1)
      expect(sqlServerSources[0].type).toBe('sqlserver')
    })
  })

  describe('工具方法', () => {
    beforeEach(() => {
      store.dataSourceList = [...mockDataSources]
      store.error = '测试错误'
    })

    it('应该能够清除错误', () => {
      store.clearError()
      expect(store.error).toBeNull()
    })

    it('应该能够重置状态', () => {
      store.resetState()
      expect(store.dataSourceList).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })
})