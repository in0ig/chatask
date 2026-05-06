import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  }
}))

// Mock API services
vi.mock('@/services/dataTableApi', () => ({
  dataTableApi: {
    discoverTables: vi.fn(),
    getTableStructure: vi.fn(),
    syncStructure: vi.fn(),
    testConnection: vi.fn()
  }
}))

vi.mock('@/services/dataSourceApi', () => ({
  dataSourceApi: {
    getAll: vi.fn()
  }
}))

describe('DataTableManager - Core Functionality', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该正确渲染页面结构', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    // 检查页面标题
    expect(wrapper.find('.page-title').text()).toBe('数据表管理')
    expect(wrapper.find('.page-description').text()).toBe('管理数据源中的表结构和字段配置')

    // 检查左右面板
    expect(wrapper.find('.left-panel').exists()).toBe(true)
    expect(wrapper.find('.right-panel').exists()).toBe(true)
  })

  it('应该显示数据源选择器', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const sourceSelector = wrapper.find('[data-testid="source-selector"]')
    expect(sourceSelector.exists()).toBe(true)
  })

  it('应该显示发现表按钮', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const discoverButton = wrapper.find('button')
    expect(discoverButton.text()).toContain('发现表')
  })

  it('应该显示刷新按钮', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const refreshButton = wrapper.find('[data-testid="refresh-button"]')
    expect(refreshButton.exists()).toBe(true)
  })

  it('应该显示空状态当没有选中表时', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const emptyState = wrapper.find('[data-testid="empty-state"]')
    expect(emptyState.exists()).toBe(true)
  })

  it('应该有正确的组件结构', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    // 检查主要区域
    expect(wrapper.find('.page-header').exists()).toBe(true)
    expect(wrapper.find('.main-content').exists()).toBe(true)
    expect(wrapper.find('.left-panel').exists()).toBe(true)
    expect(wrapper.find('.right-panel').exists()).toBe(true)
  })

  it('应该有响应式数据属性', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const vm = wrapper.vm as any
    
    // 检查响应式数据是否存在
    expect(vm.loading).toBeDefined()
    expect(vm.selectedSourceId).toBeDefined()
    expect(vm.selectedTableName).toBeDefined()
    expect(vm.dataSources).toBeDefined()
    expect(vm.discoveredTables).toBeDefined()
  })

  it('应该有正确的方法', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-icon': true,
          'el-skeleton': true,
          'el-empty': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-progress': true
        }
      }
    })

    const vm = wrapper.vm as any
    
    // 检查方法是否存在
    expect(typeof vm.handleSourceChange).toBe('function')
    expect(typeof vm.handleDiscoverTables).toBe('function')
    expect(typeof vm.handleTableSelect).toBe('function')
    expect(typeof vm.handleSyncTable).toBe('function')
    expect(typeof vm.refreshTables).toBe('function')
  })
})