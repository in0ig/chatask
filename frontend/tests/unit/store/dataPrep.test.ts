import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { dataSourceApi } from '@/services/dataSourceApi'

// Mock the dataSourceApi
vi.mock('@/services/dataSourceApi', () => ({
  dataSourceApi: {
    getAll: vi.fn()
  }
}))

// Mock the UI store
vi.mock('@/store/modules/ui', () => ({
  useUIStore: () => ({
    showToast: vi.fn()
  })
}))

describe('DataPrep Store - Enhanced Data Source Management', () => {
  let store: ReturnType<typeof useDataPrepStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPrepStore()
    vi.clearAllMocks()
  })

  describe('loadDataSources 缓存逻辑', () => {
    it('验证缓存有效时不发起网络请求', async () => {
      // 设置有效缓存
      const mockData = [
        { id: '1', name: '测试数据源1', type: 'mysql' as const, isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' }
      ]
      store.dataSourceCache = {
        data: mockData,
        timestamp: new Date(Date.now() - 2 * 60 * 1000), // 2分钟前，仍在5分钟有效期内
        version: 1
      }

      await store.loadDataSources()

      // 验证没有调用 API
      expect(dataSourceApi.getAll).not.toHaveBeenCalled()
      // 验证使用了缓存数据
      expect(store.dataSources).toEqual(mockData)
    })

    it('验证缓存过期时重新加载数据', async () => {
      // 设置过期缓存
      const oldData = [{ id: '1', name: '旧数据源', type: 'excel' as const, isActive: false, createdAt: '2024-01-01', updatedAt: '2024-01-01' }]
      const newData = [{ id: '2', name: '新数据源', type: 'mysql' as const, isActive: true, createdAt: '2024-01-02', updatedAt: '2024-01-02' }]
      
      store.dataSourceCache = {
        data: oldData,
        timestamp: new Date(Date.now() - 6 * 60 * 1000), // 6分钟前，已过期
        version: 1
      }

      // Mock API 返回新数据
      vi.mocked(dataSourceApi.getAll).mockResolvedValue(newData)

      await store.loadDataSources()

      // 验证调用了 API
      expect(dataSourceApi.getAll).toHaveBeenCalledTimes(1)
      // 验证使用了新数据
      expect(store.dataSources).toEqual(newData.map(ds => ({
        ...ds,
        createdAt: new Date(ds.createdAt),
        updatedAt: new Date(ds.updatedAt)
      })))
    })
  })

  describe('loadDataSources 错误处理', () => {
    it('验证网络错误时设置 dataSourceError', async () => {
      const errorMessage = '网络连接失败'
      vi.mocked(dataSourceApi.getAll).mockRejectedValue(new Error(errorMessage))

      await store.loadDataSources()

      expect(store.dataSourceError).toBe(errorMessage)
      expect(store.isLoadingDataSources).toBe(false)
    })

    it('验证 API 响应错误时设置详细错误信息', async () => {
      const apiError = {
        response: {
          data: { detail: 'API 服务器错误' },
          status: 500,
          statusText: 'Internal Server Error'
        },
        config: { url: '/api/data-sources' }
      }
      vi.mocked(dataSourceApi.getAll).mockRejectedValue(apiError)

      await store.loadDataSources()

      expect(store.dataSourceError).toBe('API 服务器错误')
      expect(store.isLoadingDataSources).toBe(false)
    })
  })

  describe('resetDataSourceState 方法', () => {
    it('验证 resetDataSourceState 清空所有状态', () => {
      // 设置一些初始状态
      store.dataSources = [{ id: '1', name: '测试', type: 'api' as const, isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' }]
      store.activeDataSourceId = '1'
      store.isLoadingDataSources = true
      store.dataSourceError = '测试错误'
      store.dataSourceCache = {
        data: [],
        timestamp: new Date(),
        version: 1
      }

      store.resetDataSourceState()

      expect(store.dataSources).toEqual([])
      expect(store.activeDataSourceId).toBeNull()
      expect(store.isLoadingDataSources).toBe(false)
      expect(store.dataSourceError).toBeNull()
      expect(store.dataSourceCache).toBeNull()
    })
  })

  describe('isLoadingDataSources 状态管理', () => {
    it('验证 isLoadingDataSources 状态正确切换', async () => {
      const mockData = [{ id: '1', name: '测试', type: 'mysql' as const, isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' }]
      vi.mocked(dataSourceApi.getAll).mockResolvedValue(mockData)

      // 初始状态
      expect(store.isLoadingDataSources).toBe(false)

      // 开始加载
      const loadPromise = store.loadDataSources()
      expect(store.isLoadingDataSources).toBe(true)

      // 加载完成
      await loadPromise
      expect(store.isLoadingDataSources).toBe(false)
    })

    it('验证错误时 isLoadingDataSources 状态正确重置', async () => {
      vi.mocked(dataSourceApi.getAll).mockRejectedValue(new Error('测试错误'))

      const loadPromise = store.loadDataSources()
      expect(store.isLoadingDataSources).toBe(true)

      await loadPromise
      expect(store.isLoadingDataSources).toBe(false)
    })
  })

  describe('isDataSourceCacheValid 缓存检查', () => {
    it('验证缓存有效性检查 - 有效缓存', () => {
      store.dataSourceCache = {
        data: [],
        timestamp: new Date(Date.now() - 2 * 60 * 1000), // 2分钟前
        version: 1
      }

      expect(store.isDataSourceCacheValid()).toBe(true)
    })

    it('验证缓存有效性检查 - 过期缓存', () => {
      store.dataSourceCache = {
        data: [],
        timestamp: new Date(Date.now() - 6 * 60 * 1000), // 6分钟前
        version: 1
      }

      expect(store.isDataSourceCacheValid()).toBe(false)
    })

    it('验证缓存有效性检查 - 无缓存', () => {
      store.dataSourceCache = null

      expect(store.isDataSourceCacheValid()).toBe(false)
    })
  })

  describe('数据源状态同步', () => {
    it('验证活跃数据源设置', async () => {
      const mockData = [
        { id: '1', name: '数据源1', type: 'excel' as const, isActive: false, createdAt: '2024-01-01', updatedAt: '2024-01-01' },
        { id: '2', name: '数据源2', type: 'mysql' as const, isActive: true, createdAt: '2024-01-02', updatedAt: '2024-01-02' }
      ]
      vi.mocked(dataSourceApi.getAll).mockResolvedValue(mockData)

      await store.loadDataSources()

      expect(store.activeDataSourceId).toBe('2')
    })

    it('验证缓存更新', async () => {
      const mockData = [{ id: '1', name: '测试', type: 'api' as const, isActive: true, createdAt: '2024-01-01', updatedAt: '2024-01-01' }]
      vi.mocked(dataSourceApi.getAll).mockResolvedValue(mockData)

      await store.loadDataSources()

      expect(store.dataSourceCache).not.toBeNull()
      expect(store.dataSourceCache?.data).toEqual(mockData.map(ds => ({
        ...ds,
        createdAt: new Date(ds.createdAt),
        updatedAt: new Date(ds.updatedAt)
      })))
      expect(store.dataSourceCache?.timestamp).toBeInstanceOf(Date)
    })
  })
})