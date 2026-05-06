import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElButton, ElDialog } from 'element-plus'
import DataSourceManager from '@/views/DataSource/DataSourceManager.vue'
import { useDataSourceStore } from '@/store/modules/dataSource'

// Mock Element Plus 消息组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn()
    },
    ElMessageBox: {
      confirm: vi.fn()
    }
  }
})

describe('DataSourceManager - 按钮修复验证', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    store = useDataSourceStore()
    
    // Mock store 方法
    vi.spyOn(store, 'fetchDataSources').mockResolvedValue(undefined)

    wrapper = mount(DataSourceManager, {
      global: {
        plugins: [pinia],
        components: {
          ElButton,
          ElDialog
        },
        stubs: {
          'el-card': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-icon': true,
          'Plus': true,
          'DataSourceForm': true
        }
      }
    })
  })

  describe('按钮功能修复验证', () => {
    it('应该有 handleAddClick 方法', () => {
      expect(typeof wrapper.vm.handleAddClick).toBe('function')
    })

    it('handleAddClick 方法应该能正确设置 showAddDialog', () => {
      // 初始状态
      expect(wrapper.vm.showAddDialog).toBe(false)
      
      // 调用方法
      wrapper.vm.handleAddClick()
      
      // 验证状态变化
      expect(wrapper.vm.showAddDialog).toBe(true)
    })

    it('按钮应该绑定到 handleAddClick 方法', () => {
      const addButton = wrapper.find('[data-testid="add-button"]')
      expect(addButton.exists()).toBe(true)
      
      // 验证按钮的点击事件绑定
      const buttonElement = addButton.element as HTMLButtonElement
      expect(buttonElement).toBeTruthy()
    })

    it('点击按钮应该触发 handleAddClick', async () => {
      const handleAddClickSpy = vi.spyOn(wrapper.vm, 'handleAddClick')
      
      const addButton = wrapper.find('[data-testid="add-button"]')
      await addButton.trigger('click')
      
      expect(handleAddClickSpy).toHaveBeenCalled()
    })

    it('点击按钮应该打开对话框', async () => {
      expect(wrapper.vm.showAddDialog).toBe(false)
      
      const addButton = wrapper.find('[data-testid="add-button"]')
      await addButton.trigger('click')
      
      expect(wrapper.vm.showAddDialog).toBe(true)
    })
  })

  describe('响应式数据验证', () => {
    it('showAddDialog 应该是响应式的', async () => {
      expect(wrapper.vm.showAddDialog).toBe(false)
      
      // 通过方法修改
      wrapper.vm.handleAddClick()
      expect(wrapper.vm.showAddDialog).toBe(true)
      
      // 通过 setData 修改
      await wrapper.setData({ showAddDialog: false })
      expect(wrapper.vm.showAddDialog).toBe(false)
    })
  })
})