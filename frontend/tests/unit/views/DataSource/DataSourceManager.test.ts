import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataSourceManager from '@/views/DataSource/DataSourceManager.vue'
import { useDataSourceStore } from '@/store/modules/dataSource'
import type { DataSource } from '@/types/dataSource'

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

// Mock 数据源 API
vi.mock('@/api/chatbiDataSourceApi', () => ({
  dataSourceApi: {
    getDataSources: vi.fn(),
    createDataSource: vi.fn(),
    updateDataSource: vi.fn(),
    deleteDataSource: vi.fn(),
    testConnection: vi.fn()
  }
}))

describe('DataSourceManager', () => {
  let wrapper: any
  let store: any

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
      status: 'error',
      createdAt: new Date('2024-01-02'),
      updatedAt: new Date('2024-01-02')
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

    wrapper = mount(DataSourceManager, {
      global: {
        stubs: {
          'el-card': true,
          'el-button': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-icon': true,
          'DataSourceForm': true
        }
      }
    })
  })

  describe('组件渲染', () => {
    it('应该正确渲染数据源管理页面', () => {
      expect(wrapper.find('.data-source-manager').exists()).toBe(true)
      expect(wrapper.text()).toContain('数据源管理')
      expect(wrapper.text()).toContain('新增数据源')
    })

    it('应该显示数据源列表', () => {
      expect(wrapper.vm.dataSourceList).toEqual(mockDataSources)
    })

    it('应该显示正确的数据源数量', () => {
      expect(wrapper.vm.dataSourceList.length).toBe(2)
    })
  })

  describe('状态显示', () => {
    it('应该正确显示数据源状态', () => {
      expect(wrapper.vm.getStatusType('active')).toBe('success')
      expect(wrapper.vm.getStatusType('inactive')).toBe('info')
      expect(wrapper.vm.getStatusType('error')).toBe('danger')
    })

    it('应该正确显示状态文本', () => {
      expect(wrapper.vm.getStatusText('active')).toBe('正常')
      expect(wrapper.vm.getStatusText('inactive')).toBe('未连接')
      expect(wrapper.vm.getStatusText('error')).toBe('错误')
    })
  })

  describe('数据源操作', () => {
    it('应该能够加载数据源列表', async () => {
      await wrapper.vm.loadDataSources()
      expect(store.fetchDataSources).toHaveBeenCalled()
    })

    it('应该能够测试连接', async () => {
      const dataSource = mockDataSources[0]
      await wrapper.vm.testConnection(dataSource)
      
      expect(store.testConnection).toHaveBeenCalledWith(dataSource.config)
      expect(store.updateDataSourceStatus).toHaveBeenCalledWith(dataSource.id, 'active')
      expect(ElMessage.success).toHaveBeenCalledWith('连接测试成功')
    })

    it('应该处理连接测试失败', async () => {
      store.testConnection.mockResolvedValue({ success: false, error: '连接超时' })
      
      const dataSource = mockDataSources[0]
      await wrapper.vm.testConnection(dataSource)
      
      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败: 连接超时')
      expect(store.updateDataSourceStatus).toHaveBeenCalledWith(dataSource.id, 'error')
    })

    it('应该能够编辑数据源', () => {
      const dataSource = mockDataSources[0]
      wrapper.vm.editDataSource(dataSource)
      
      expect(wrapper.vm.editingDataSource).toEqual(dataSource)
      expect(wrapper.vm.showAddDialog).toBe(true)
    })

    it('应该能够删除数据源', async () => {
      // Mock 确认对话框
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      
      const dataSource = mockDataSources[0]
      await wrapper.vm.deleteDataSource(dataSource)
      
      expect(ElMessageBox.confirm).toHaveBeenCalledWith(
        `确定要删除数据源 "${dataSource.name}" 吗？`,
        '确认删除',
        expect.any(Object)
      )
      expect(store.deleteDataSource).toHaveBeenCalledWith(dataSource.id)
      expect(ElMessage.success).toHaveBeenCalledWith('删除成功')
    })

    it('应该处理删除取消', async () => {
      // Mock 取消删除
      vi.mocked(ElMessageBox.confirm).mockRejectedValue('cancel')
      
      const dataSource = mockDataSources[0]
      await wrapper.vm.deleteDataSource(dataSource)
      
      expect(store.deleteDataSource).not.toHaveBeenCalled()
      expect(ElMessage.error).not.toHaveBeenCalled()
    })
  })

  describe('表单处理', () => {
    it('应该能够提交新增表单', async () => {
      const config = {
        name: '新数据源',
        type: 'mysql' as const,
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
      
      await wrapper.vm.handleSubmit(config)
      
      expect(store.createDataSource).toHaveBeenCalledWith(config)
      expect(ElMessage.success).toHaveBeenCalledWith('创建成功')
      expect(wrapper.vm.showAddDialog).toBe(false)
      expect(wrapper.vm.editingDataSource).toBeNull()
    })

    it('应该能够提交编辑表单', async () => {
      const dataSource = mockDataSources[0]
      const config = { ...dataSource.config, name: dataSource.name, type: dataSource.type }
      
      wrapper.vm.editingDataSource = dataSource
      await wrapper.vm.handleSubmit(config)
      
      expect(store.updateDataSource).toHaveBeenCalledWith(dataSource.id, config)
      expect(ElMessage.success).toHaveBeenCalledWith('更新成功')
      expect(wrapper.vm.showAddDialog).toBe(false)
      expect(wrapper.vm.editingDataSource).toBeNull()
    })

    it('应该能够取消表单', () => {
      wrapper.vm.editingDataSource = mockDataSources[0]
      wrapper.vm.showAddDialog = true
      
      wrapper.vm.handleCancel()
      
      expect(wrapper.vm.showAddDialog).toBe(false)
      expect(wrapper.vm.editingDataSource).toBeNull()
    })
  })

  describe('错误处理', () => {
    it('应该处理加载数据源失败', async () => {
      store.fetchDataSources.mockRejectedValue(new Error('网络错误'))
      
      await wrapper.vm.loadDataSources()
      
      expect(ElMessage.error).toHaveBeenCalledWith('加载数据源列表失败')
    })

    it('应该处理创建数据源失败', async () => {
      store.createDataSource.mockRejectedValue(new Error('创建失败'))
      
      const config = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: { min: 5, max: 20, timeout: 30 }
      }
      
      await wrapper.vm.handleSubmit(config)
      
      expect(ElMessage.error).toHaveBeenCalledWith('创建失败')
    })

    it('应该处理连接测试异常', async () => {
      store.testConnection.mockRejectedValue(new Error('网络错误'))
      
      const dataSource = mockDataSources[0]
      await wrapper.vm.testConnection(dataSource)
      
      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败')
      expect(store.updateDataSourceStatus).toHaveBeenCalledWith(dataSource.id, 'error')
    })
  })

  describe('生命周期', () => {
    it('应该在组件挂载时加载数据源', () => {
      expect(store.fetchDataSources).toHaveBeenCalled()
    })
  })
})