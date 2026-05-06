import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElButton, ElIcon, ElEmpty, ElSkeleton, ElDialog, ElCard } from 'element-plus'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Plus: { name: 'Plus' },
  Refresh: { name: 'Refresh' },
  Database: { name: 'Database' }
}))

// Mock ElMessage
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn()
    }
  }
})

describe('DataTableManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该正确渲染页面结构', () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: {
          ElButton,
          ElIcon,
          ElEmpty,
          ElSkeleton,
          ElDialog,
          ElCard
        },
        stubs: {
          'el-icon': true,
          'el-button': true,
          'el-empty': true,
          'el-skeleton': true,
          'el-dialog': true,
          'el-card': true
        }
      }
    })

    // 检查页面标题
    expect(wrapper.find('.page-title').text()).toBe('数据表管理')
    expect(wrapper.find('.page-description').text()).toBe('管理数据源中的表结构和字段配置')
  })

  it('应该显示添加数据表按钮', () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: {
          ElButton,
          ElIcon,
          ElEmpty,
          ElSkeleton,
          ElDialog,
          ElCard
        },
        stubs: {
          'el-icon': true,
          'el-button': true,
          'el-empty': true,
          'el-skeleton': true,
          'el-dialog': true,
          'el-card': true
        }
      }
    })

    const addDialog = wrapper.find('[data-testid="add-table-dialog"]')
    expect(addDialog.exists()).toBe(true)
  })

  it('应该显示刷新按钮', () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: {
          ElButton,
          ElIcon,
          ElEmpty,
          ElSkeleton,
          ElDialog,
          ElCard
        },
        stubs: {
          'el-icon': true,
          'el-button': true,
          'el-empty': true,
          'el-skeleton': true,
          'el-dialog': true,
          'el-card': true
        }
      }
    })

    const refreshButton = wrapper.find('[data-testid="refresh-button"]')
    expect(refreshButton.exists()).toBe(true)
  })

  it('应该显示空状态当没有选中表时', () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: {
          ElButton,
          ElIcon,
          ElEmpty,
          ElSkeleton,
          ElDialog,
          ElCard
        },
        stubs: {
          'el-icon': true,
          'el-button': true,
          'el-empty': true,
          'el-skeleton': true,
          'el-dialog': true,
          'el-card': true
        }
      }
    })

    const emptyState = wrapper.find('[data-testid="empty-state"]')
    expect(emptyState.exists()).toBe(true)
  })
})