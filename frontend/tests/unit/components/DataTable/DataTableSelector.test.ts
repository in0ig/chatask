import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import DataTableSelector from '@/components/DataTable/DataTableSelector.vue'

// Mock Element Plus
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn()
    }
  }
})

const mockDataTables = [
  {
    id: '1',
    name: 'users',
    dataSourceId: '1',
    dataSourceName: 'MySQL数据源',
    dataSourceType: 'mysql',
    fieldCount: 5,
    comment: '用户表',
    selected: false,
    pinned: false,
    isActive: true
  },
  {
    id: '2',
    name: 'orders',
    dataSourceId: '1',
    dataSourceName: 'MySQL数据源',
    dataSourceType: 'mysql',
    fieldCount: 8,
    comment: '订单表',
    selected: false,
    pinned: true,
    isActive: true
  },
  {
    id: '3',
    name: 'products',
    dataSourceId: '2',
    dataSourceName: 'PostgreSQL数据源',
    dataSourceType: 'postgresql',
    fieldCount: 12,
    comment: '产品表',
    selected: true,
    pinned: false,
    isActive: true
  }
]

describe('DataTableSelector', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()
    
    wrapper = mount(DataTableSelector, {
      props: {
        modelValue: true,
        dataTables: mockDataTables,
        isLoading: false,
        error: null
      },
      global: {
        stubs: {
          'el-dialog': true,
          'el-input': true,
          'el-button': true,
          'el-button-group': true,
          'el-select': true,
          'el-option': true,
          'el-alert': true,
          'el-skeleton': true,
          'el-progress': true,
          'el-result': true,
          'el-checkbox': true,
          'el-tag': true,
          'el-dropdown': true,
          'el-dropdown-menu': true,
          'el-dropdown-item': true,
          'el-tooltip': true,
          'el-icon': true
        }
      }
    })
  })

  describe('Component Initialization', () => {
    it('should render correctly with data tables', () => {
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm.visible).toBe(true)
    })

    it('should display correct total count', () => {
      expect(wrapper.vm.totalCount).toBe(3)
    })

    it('should display correct selected count', () => {
      expect(wrapper.vm.selectedCount).toBe(1)
    })

    it('should display correct pinned count', () => {
      expect(wrapper.vm.pinnedCount).toBe(1)
    })
  })

  describe('Data Source Filtering', () => {
    it('should compute available data sources correctly', () => {
      const availableSources = wrapper.vm.availableDataSources
      expect(availableSources).toHaveLength(2)
      expect(availableSources[0].label).toBe('MySQL数据源')
      expect(availableSources[1].label).toBe('PostgreSQL数据源')
    })

    it('should filter tables by data source', async () => {
      wrapper.vm.selectedDataSources = ['1']
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(2)
      expect(filtered.every(t => t.dataSourceId === '1')).toBe(true)
    })

    it('should filter tables by multiple data sources', async () => {
      wrapper.vm.selectedDataSources = ['1', '2']
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(3)
    })
  })

  describe('Search Functionality', () => {
    it('should filter tables by name', async () => {
      wrapper.vm.searchKeyword = 'user'
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(1)
      expect(filtered[0].name).toBe('users')
    })

    it('should filter tables by data source name', async () => {
      wrapper.vm.searchKeyword = 'MySQL'
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(2)
      expect(filtered.every(t => t.dataSourceName.includes('MySQL'))).toBe(true)
    })

    it('should filter tables by comment', async () => {
      wrapper.vm.searchKeyword = '用户'
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(1)
      expect(filtered[0].comment).toBe('用户表')
    })

    it('should clear search results', async () => {
      wrapper.vm.searchKeyword = 'nonexistent'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.filteredTables).toHaveLength(0)

      wrapper.vm.clearSearch()
      expect(wrapper.vm.searchKeyword).toBe('')
      expect(wrapper.vm.filteredTables).toHaveLength(3)
    })
  })

  describe('Filter Types', () => {
    it('should filter selected tables', async () => {
      wrapper.vm.setFilter('selected')
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(1)
      expect(filtered[0].selected).toBe(true)
    })

    it('should filter pinned tables', async () => {
      wrapper.vm.setFilter('pinned')
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(1)
      expect(filtered[0].pinned).toBe(true)
    })

    it('should show all tables', async () => {
      wrapper.vm.setFilter('all')
      await wrapper.vm.$nextTick()

      const filtered = wrapper.vm.filteredTables
      expect(filtered).toHaveLength(3)
    })
  })

  describe('Sorting', () => {
    it('should sort by name', async () => {
      wrapper.vm.handleSort('name')
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedTables
      expect(sorted[0].name).toBe('orders') // pinned first, then alphabetical
      expect(sorted[1].name).toBe('products')
      expect(sorted[2].name).toBe('users')
    })

    it('should sort by field count', async () => {
      wrapper.vm.handleSort('fieldCount')
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedTables
      // Pinned first, then by field count descending
      expect(sorted[0].name).toBe('orders') // pinned
      expect(sorted[1].fieldCount).toBe(12) // products - highest field count
      expect(sorted[2].fieldCount).toBe(5)  // users - lowest field count
    })

    it('should sort by data source', async () => {
      wrapper.vm.handleSort('dataSource')
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedTables
      // Pinned first, then by data source name
      expect(sorted[0].name).toBe('orders') // pinned
    })

    it('should sort by selected status', async () => {
      wrapper.vm.handleSort('selected')
      await wrapper.vm.$nextTick()

      const sorted = wrapper.vm.sortedTables
      // Pinned first, then selected, then unselected
      expect(sorted[0].name).toBe('orders') // pinned
    })
  })

  describe('Table Selection', () => {
    it('should handle single table selection', async () => {
      const table = mockDataTables[0]
      wrapper.vm.handleTableSelectionChange(table, true)

      expect(table.selected).toBe(true)
      expect(ElMessage.success).toHaveBeenCalledWith('已选择 users')
    })

    it('should handle table click selection', async () => {
      const table = mockDataTables[0]
      wrapper.vm.handleTableClick(table)

      expect(table.selected).toBe(true)
    })

    it('should select all filtered tables', async () => {
      wrapper.vm.selectAll()

      expect(mockDataTables.every(t => t.selected)).toBe(true)
      expect(ElMessage.success).toHaveBeenCalledWith('已选择 3 张数据表')
    })

    it('should clear all selections', async () => {
      // First select some tables
      mockDataTables.forEach(t => t.selected = true)
      
      wrapper.vm.selectNone()

      expect(mockDataTables.every(t => !t.selected)).toBe(true)
      expect(ElMessage.info).toHaveBeenCalledWith('已清空选择')
    })

    it('should invert selection', async () => {
      const originalSelections = mockDataTables.map(t => t.selected)
      
      wrapper.vm.invertSelection()

      mockDataTables.forEach((table, index) => {
        expect(table.selected).toBe(!originalSelections[index])
      })
      expect(ElMessage.info).toHaveBeenCalledWith('已反选当前筛选结果')
    })
  })

  describe('Pin Functionality', () => {
    it('should toggle pin status', async () => {
      const table = mockDataTables[0]
      const originalPinned = table.pinned
      
      wrapper.vm.togglePin(table)

      expect(table.pinned).toBe(!originalPinned)
      expect(ElMessage.success).toHaveBeenCalledWith(
        table.pinned ? 'users 已置顶' : 'users 已取消置顶'
      )
    })

    it('should pin selected tables', async () => {
      // Select some tables first
      mockDataTables[0].selected = true
      mockDataTables[2].selected = true
      
      wrapper.vm.pinSelected()

      expect(mockDataTables[0].pinned).toBe(true)
      expect(mockDataTables[2].pinned).toBe(true)
      expect(ElMessage.success).toHaveBeenCalledWith('已置顶 2 张数据表')
    })
  })

  describe('Table Actions', () => {
    it('should handle info action', async () => {
      const table = mockDataTables[0]
      wrapper.vm.handleTableAction(table, 'info')

      expect(wrapper.emitted('info')).toBeTruthy()
      expect(wrapper.emitted('info')[0]).toEqual([table])
    })

    it('should handle copy action', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined)
        }
      })

      const table = mockDataTables[0]
      await wrapper.vm.handleTableAction(table, 'copy')

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('1')
      expect(ElMessage.success).toHaveBeenCalledWith('ID 已复制到剪贴板')
    })

    it('should handle export action', async () => {
      // Mock URL and createElement
      const mockCreateElement = vi.fn().mockReturnValue({
        href: '',
        download: '',
        click: vi.fn()
      })
      const mockCreateObjectURL = vi.fn().mockReturnValue('blob:url')
      const mockRevokeObjectURL = vi.fn()

      global.document.createElement = mockCreateElement
      global.URL.createObjectURL = mockCreateObjectURL
      global.URL.revokeObjectURL = mockRevokeObjectURL

      const table = mockDataTables[0]
      wrapper.vm.handleTableAction(table, 'export')

      expect(mockCreateElement).toHaveBeenCalledWith('a')
      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(ElMessage.success).toHaveBeenCalledWith('配置已导出')
    })
  })

  describe('Preview and Confirmation', () => {
    it('should emit preview event', async () => {
      const table = mockDataTables[0]
      wrapper.vm.previewTable(table)

      expect(wrapper.emitted('preview')).toBeTruthy()
      expect(wrapper.emitted('preview')[0]).toEqual([table])
    })

    it('should confirm selection', async () => {
      // Select some tables
      mockDataTables[0].selected = true
      mockDataTables[2].selected = true

      await wrapper.vm.confirmSelection()

      expect(wrapper.emitted('confirm')).toBeTruthy()
      const confirmedTables = wrapper.emitted('confirm')[0][0]
      expect(confirmedTables).toHaveLength(2)
      expect(ElMessage.success).toHaveBeenCalledWith('已确认选择 2 张数据表')
    })

    it('should handle retry', async () => {
      wrapper.vm.handleRetry()

      expect(wrapper.emitted('retry')).toBeTruthy()
    })
  })

  describe('Dialog Management', () => {
    it('should close dialog', async () => {
      wrapper.vm.handleClose()

      expect(wrapper.vm.visible).toBe(false)
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
    })

    it('should reset filters when dialog opens', async () => {
      wrapper.vm.searchKeyword = 'test'
      wrapper.vm.filterType = 'selected'
      wrapper.vm.selectedDataSources = ['1']

      await wrapper.setProps({ modelValue: true })

      expect(wrapper.vm.searchKeyword).toBe('')
      expect(wrapper.vm.filterType).toBe('all')
      expect(wrapper.vm.selectedDataSources).toEqual([])
    })
  })

  describe('Loading and Error States', () => {
    it('should show loading state', async () => {
      await wrapper.setProps({ isLoading: true })
      expect(wrapper.vm.loadingProgress).toBeGreaterThan(0)
    })

    it('should show error state', async () => {
      const errorMessage = 'Failed to load tables'
      await wrapper.setProps({ error: errorMessage })
      
      // Component should display error
      expect(wrapper.props('error')).toBe(errorMessage)
    })

    it('should simulate loading progress', async () => {
      wrapper.vm.simulateLoadingProgress()
      
      // Wait for progress to update
      await new Promise(resolve => setTimeout(resolve, 300))
      
      expect(wrapper.vm.loadingProgress).toBeGreaterThan(0)
    })
  })

  describe('Empty States', () => {
    it('should show correct empty state title for search', async () => {
      wrapper.vm.searchKeyword = 'nonexistent'
      
      const title = wrapper.vm.getEmptyStateTitle()
      expect(title).toBe('未找到匹配的数据表')
    })

    it('should show correct empty state title for selected filter', async () => {
      wrapper.vm.filterType = 'selected'
      
      const title = wrapper.vm.getEmptyStateTitle()
      expect(title).toBe('暂无已选择的数据表')
    })

    it('should show correct empty state title for pinned filter', async () => {
      wrapper.vm.filterType = 'pinned'
      
      const title = wrapper.vm.getEmptyStateTitle()
      expect(title).toBe('暂无置顶的数据表')
    })

    it('should show correct empty state subtitle', async () => {
      wrapper.vm.searchKeyword = 'test'
      
      const subtitle = wrapper.vm.getEmptyStateSubtitle()
      expect(subtitle).toContain('搜索 "test" 没有找到相关结果')
    })
  })

  describe('Utility Functions', () => {
    it('should get correct data source type color', () => {
      expect(wrapper.vm.getDataSourceTypeColor('mysql')).toBe('primary')
      expect(wrapper.vm.getDataSourceTypeColor('postgresql')).toBe('primary')
      expect(wrapper.vm.getDataSourceTypeColor('excel')).toBe('success')
      expect(wrapper.vm.getDataSourceTypeColor('unknown')).toBe('default')
    })

    it('should handle table hover events', async () => {
      const table = mockDataTables[0]
      
      wrapper.vm.handleTableHover(table)
      expect(wrapper.vm.highlightedId).toBe('1')
      
      wrapper.vm.handleTableLeave()
      expect(wrapper.vm.highlightedId).toBeNull()
    })

    it('should handle search with scroll to top', async () => {
      // Mock querySelector
      const mockScrollElement = { scrollTop: 100 }
      global.document.querySelector = vi.fn().mockReturnValue(mockScrollElement)

      wrapper.vm.handleSearch()
      await wrapper.vm.$nextTick()

      expect(mockScrollElement.scrollTop).toBe(0)
    })
  })
})