import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import DatabaseTableSelector from '@/components/DataPreparation/DatabaseTableSelector.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import api from '@/services/api'

// Mock Element Plus 组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    },
    ElMessageBox: {
      confirm: vi.fn()
    }
  }
})

// Mock API
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn()
  }
}))

// Mock 数据
const mockDataSources = [
  {
    id: 'ds1',
    name: '测试数据库1',
    sourceType: 'DATABASE' as const,
    dbType: 'MYSQL' as const,
    connectionStatus: 'CONNECTED' as const,
    isActive: true,
    host: 'localhost',
    port: 3306,
    databaseName: 'test_db',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z'
  },
  {
    id: 'ds2',
    name: '测试数据库2',
    sourceType: 'DATABASE' as const,
    dbType: 'POSTGRESQL' as const,
    connectionStatus: 'DISCONNECTED' as const,
    isActive: true,
    host: 'localhost',
    port: 5432,
    databaseName: 'test_db2',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z'
  },
  {
    id: 'ds3',
    name: 'Excel文件',
    sourceType: 'FILE' as const,
    connectionStatus: 'CONNECTED' as const,
    isActive: true,
    filePath: '/path/to/file.xlsx',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z'
  }
]

const mockTables = [
  {
    name: 'users',
    type: 'TABLE',
    comment: '用户表'
  },
  {
    name: 'orders',
    type: 'TABLE',
    comment: '订单表'
  },
  {
    name: 'products',
    type: 'TABLE',
    comment: '产品表'
  },
  {
    name: 'user_view',
    type: 'VIEW',
    comment: '用户视图'
  }
]

describe('DatabaseTableSelector', () => {
  let wrapper: VueWrapper<any>
  let store: ReturnType<typeof useDataPreparationStore>
  let pinia: any

  beforeEach(() => {
    // 创建新的 Pinia 实例
    pinia = createPinia()
    setActivePinia(pinia)
    
    // 获取 store 实例
    store = useDataPreparationStore()
    
    // Mock API 响应
    vi.mocked(api.get).mockResolvedValue({
      data: { tables: mockTables }
    })
    
    // Mock store 方法 - 确保返回正确的数据格式
    vi.spyOn(store, 'fetchDataSources').mockImplementation(async () => {
      // 直接设置 store 数据
      store.dataSources.data = mockDataSources
      return { success: true, data: mockDataSources }
    })
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.clearAllMocks()
  })

  const createWrapper = (props = {}) => {
    // Ensure store data is set before creating wrapper
    store.dataSources.data = mockDataSources
    
    return mount(DatabaseTableSelector, {
      props: {
        visible: true,
        ...props
      },
      global: {
        plugins: [pinia], // Use the same pinia instance
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-input': true,
          'el-table': {
            template: '<div class="el-table-mock"><slot /></div>',
            methods: {
              clearSelection: vi.fn(),
              toggleRowSelection: vi.fn()
            }
          },
          'el-table-column': true,
          'el-tag': true,
          'el-empty': true
        }
      }
    })
  }

  describe('组件渲染', () => {
    it('应该正确渲染组件', () => {
      wrapper = createWrapper()
      expect(wrapper.find('.database-table-selector').exists()).toBe(true)
    })

    it('应该显示数据源选择下拉框', () => {
      wrapper = createWrapper()
      expect(wrapper.find('.data-source-selection').exists()).toBe(true)
    })

    it('未选择数据源时应该显示空状态', () => {
      wrapper = createWrapper()
      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })
  })

  describe('数据源管理', () => {
    it('应该在组件挂载时加载数据源列表', async () => {
      // Create a fresh spy for this test
      const fetchSpy = vi.spyOn(store, 'fetchDataSources').mockImplementation(async () => {
        store.dataSources.data = mockDataSources
        return { success: true, data: mockDataSources }
      })
      
      wrapper = createWrapper()
      
      // Wait for component to mount and initialize
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 50))
      
      expect(fetchSpy).toHaveBeenCalled()
    })

    it('应该过滤出数据库类型的数据源', async () => {
      // Ensure store data is set up before creating wrapper
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper()
      
      // Wait for component to initialize and computed properties to update
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 50))
      
      const availableDataSources = wrapper.vm.availableDataSources
      
      expect(availableDataSources).toHaveLength(2)
      expect(availableDataSources.every((ds: any) => ds.sourceType === 'DATABASE')).toBe(true)
    })

    it('应该正确显示数据源状态', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getStatusText('CONNECTED')).toBe('已连接')
      expect(wrapper.vm.getStatusText('DISCONNECTED')).toBe('未连接')
      expect(wrapper.vm.getStatusText('FAILED')).toBe('连接失败')
      expect(wrapper.vm.getStatusText('TESTING')).toBe('测试中')
    })

    it('应该正确设置状态样式类', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getStatusClass('CONNECTED')).toBe('status-connected')
      expect(wrapper.vm.getStatusClass('DISCONNECTED')).toBe('status-disconnected')
      expect(wrapper.vm.getStatusClass('FAILED')).toBe('status-failed')
      expect(wrapper.vm.getStatusClass('TESTING')).toBe('status-testing')
    })
  })

  describe('表列表管理', () => {
    beforeEach(async () => {
      // Set up store data
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // 选择数据源
      wrapper.vm.selectedDataSourceId = 'ds1'
      await wrapper.vm.handleDataSourceChange('ds1')
      await wrapper.vm.$nextTick()
    })

    it('选择数据源后应该加载表列表', async () => {
      expect(api.get).toHaveBeenCalledWith('/data-sources/ds1/tables')
      expect(wrapper.vm.availableTables).toHaveLength(4)
    })

    it('应该显示表列表容器', async () => {
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.table-list-container').exists()).toBe(true)
    })

    it('应该显示正确的表数量', async () => {
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.availableTables).toHaveLength(4)
    })

    it('应该支持表名搜索过滤', async () => {
      wrapper.vm.searchKeyword = 'user'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(2) // users 和 user_view
      expect(filtered.every((table: any) => table.name.includes('user'))).toBe(true)
    })

    it('应该支持备注搜索过滤', async () => {
      wrapper.vm.searchKeyword = '用户'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(2) // 用户表 和 用户视图
    })

    it('应该支持刷新表列表', async () => {
      vi.clearAllMocks()
      await wrapper.vm.refreshTables()
      
      expect(api.get).toHaveBeenCalledWith('/data-sources/ds1/tables')
    })
  })

  describe('表选择功能', () => {
    beforeEach(async () => {
      // Set up store data
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.selectedDataSourceId = 'ds1'
      await wrapper.vm.handleDataSourceChange('ds1')
      await wrapper.vm.$nextTick()
    })

    it('应该支持多选表', () => {
      const selectedTables = [mockTables[0], mockTables[1]]
      wrapper.vm.handleSelectionChange(selectedTables)
      
      expect(wrapper.vm.selectedTables).toHaveLength(2)
      expect(wrapper.vm.selectedTables).toEqual(selectedTables)
    })

    it('应该支持全选功能', () => {
      // Mock tableRef with proper methods
      wrapper.vm.tableRef = {
        toggleRowSelection: vi.fn(),
        clearSelection: vi.fn()
      }
      
      wrapper.vm.selectAll()
      
      expect(wrapper.vm.tableRef.toggleRowSelection).toHaveBeenCalledTimes(4)
    })

    it('应该支持清空选择', () => {
      // Mock tableRef with proper methods
      wrapper.vm.tableRef = {
        clearSelection: vi.fn(),
        toggleRowSelection: vi.fn()
      }
      
      wrapper.vm.clearSelection()
      
      expect(wrapper.vm.tableRef.clearSelection).toHaveBeenCalled()
    })
  })

  describe('同步功能', () => {
    beforeEach(async () => {
      // Set up store data
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.selectedDataSourceId = 'ds1'
      await wrapper.vm.handleDataSourceChange('ds1')
      wrapper.vm.selectedTables = [mockTables[0], mockTables[1]]
      await wrapper.vm.$nextTick()
    })

    it('应该在确认时显示确认对话框', async () => {
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
      
      await wrapper.vm.handleConfirm()
      
      expect(ElMessageBox.confirm).toHaveBeenCalledWith(
        expect.stringContaining('确定要导入选中的 2 个表吗'),
        '确认导入',
        expect.any(Object)
      )
    })

    it('应该在同步完成后发送确认事件', async () => {
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
      
      await wrapper.vm.handleConfirm()
      
      expect(wrapper.emitted('confirm')).toBeTruthy()
      expect(wrapper.emitted('confirm')?.[0]).toEqual([{
        sourceId: 'ds1',
        tables: [mockTables[0], mockTables[1]]
      }])
    })
  })

  describe('错误处理', () => {
    it('应该处理加载表列表失败的情况', async () => {
      const error = new Error('网络错误')
      vi.mocked(api.get).mockRejectedValue(error)
      
      // Set up store data
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.handleDataSourceChange('ds1')
      
      expect(ElMessage.error).toHaveBeenCalled()
      expect(wrapper.vm.availableTables).toHaveLength(0)
    })

    it('没有选择表时应该显示警告', async () => {
      wrapper = createWrapper()
      wrapper.vm.selectedTables = []
      
      await wrapper.vm.handleConfirm()
      
      expect(ElMessage.warning).toHaveBeenCalledWith('请至少选择一个表')
    })
  })

  describe('事件处理', () => {
    it('应该发送取消事件', () => {
      wrapper = createWrapper()
      wrapper.vm.handleCancel()
      
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('应该在可见性变化时重置状态', async () => {
      wrapper = createWrapper({ visible: true })
      
      // 设置一些状态
      wrapper.vm.selectedDataSourceId = 'ds1'
      wrapper.vm.availableTables = mockTables
      wrapper.vm.selectedTables = [mockTables[0]]
      wrapper.vm.searchKeyword = 'test'
      
      // 改变可见性
      await wrapper.setProps({ visible: false })
      
      expect(wrapper.vm.selectedDataSourceId).toBe('')
      expect(wrapper.vm.availableTables).toHaveLength(0)
      expect(wrapper.vm.selectedTables).toHaveLength(0)
      expect(wrapper.vm.searchKeyword).toBe('')
    })
  })

  describe('预选数据源', () => {
    it('应该支持预选数据源', async () => {
      // Set up store data first
      store.dataSources.data = mockDataSources
      
      wrapper = createWrapper({ preSelectedSourceId: 'ds1' })
      
      // Wait for component to initialize
      await new Promise(resolve => setTimeout(resolve, 100))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.selectedDataSourceId).toBe('ds1')
      expect(api.get).toHaveBeenCalledWith('/data-sources/ds1/tables')
    })
  })

  describe('响应式设计', () => {
    it('应该在移动端正确显示', () => {
      wrapper = createWrapper()
      
      // 检查响应式样式类是否存在
      expect(wrapper.find('.database-table-selector').exists()).toBe(true)
    })
  })

  describe('性能优化', () => {
    it('应该正确计算过滤后的表列表', () => {
      wrapper = createWrapper()
      wrapper.vm.availableTables = mockTables
      wrapper.vm.searchKeyword = 'user'
      
      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(2)
    })

    it('应该在没有搜索关键词时返回完整列表', () => {
      wrapper = createWrapper()
      wrapper.vm.availableTables = mockTables
      wrapper.vm.searchKeyword = ''
      
      const filtered = wrapper.vm.filteredTables
      expect(filtered).toEqual(mockTables)
    })
  })
})