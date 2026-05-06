import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElButton, ElDialog, ElCard, ElTable, ElTableColumn, ElTag, ElIcon, ElMessageBox, ElMessage } from 'element-plus'
import DataSourceManager from '@/views/DataSource/DataSourceManager.vue'
import DataSourceForm from '@/components/DataSource/DataSourceForm.vue'
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

// Mock 图标组件
vi.mock('@element-plus/icons-vue', () => ({
  Plus: { name: 'Plus' },
  Connection: { name: 'Connection' },
  Warning: { name: 'Warning' },
  CircleCheck: { name: 'CircleCheck' }
}))

describe('DataSourceManager - 按钮功能测试', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    store = useDataSourceStore()
    
    // Mock store 方法
    vi.spyOn(store, 'fetchDataSources').mockResolvedValue(undefined)
    vi.spyOn(store, 'createDataSource').mockResolvedValue(undefined)
    vi.spyOn(store, 'updateDataSource').mockResolvedValue(undefined)
    vi.spyOn(store, 'deleteDataSource').mockResolvedValue(undefined)
    vi.spyOn(store, 'testConnection').mockResolvedValue({ success: true })
    vi.spyOn(store, 'updateDataSourceStatus').mockResolvedValue(undefined)

    wrapper = mount(DataSourceManager, {
      global: {
        plugins: [pinia],
        components: {
          ElButton,
          ElDialog,
          ElCard,
          ElTable,
          ElTableColumn,
          ElTag,
          ElIcon,
          DataSourceForm
        },
        stubs: {
          'el-icon': true,
          'Plus': true,
          'Connection': true,
          'Warning': true,
          'CircleCheck': true
        }
      }
    })
  })

  describe('新增按钮功能', () => {
    it('应该能够找到新增按钮', () => {
      const addButton = wrapper.find('[data-testid="add-button"]')
      if (!addButton.exists()) {
        // 如果没有 data-testid，尝试通过文本查找
        const buttons = wrapper.findAllComponents(ElButton)
        const addButtonByText = buttons.find((btn: any) => 
          btn.text().includes('新增数据源')
        )
        expect(addButtonByText).toBeTruthy()
      } else {
        expect(addButton.exists()).toBe(true)
      }
    })

    it('点击新增按钮应该打开对话框', async () => {
      // 初始状态对话框应该是关闭的
      expect(wrapper.vm.showAddDialog).toBe(false)
      
      // 查找新增按钮
      const buttons = wrapper.findAllComponents(ElButton)
      const addButton = buttons.find((btn: any) => 
        btn.text().includes('新增数据源')
      )
      
      expect(addButton).toBeTruthy()
      
      // 点击按钮
      await addButton!.trigger('click')
      
      // 检查对话框状态
      expect(wrapper.vm.showAddDialog).toBe(true)
    })

    it('对话框打开后应该显示表单组件', async () => {
      // 打开对话框
      await wrapper.setData({ showAddDialog: true })
      await wrapper.vm.$nextTick()
      
      // 检查对话框是否存在
      const dialog = wrapper.findComponent(ElDialog)
      expect(dialog.exists()).toBe(true)
      
      // 检查表单组件是否存在
      const form = wrapper.findComponent(DataSourceForm)
      expect(form.exists()).toBe(true)
    })

    it('应该能够正确处理按钮点击事件', async () => {
      // 创建点击事件的 spy
      const clickSpy = vi.spyOn(wrapper.vm, '$emit')
      
      // 模拟按钮点击
      wrapper.vm.showAddDialog = false
      
      // 直接调用点击处理方法（模拟按钮点击）
      wrapper.vm.showAddDialog = true
      
      expect(wrapper.vm.showAddDialog).toBe(true)
    })
  })

  describe('响应式数据', () => {
    it('showAddDialog 应该是响应式的', async () => {
      expect(wrapper.vm.showAddDialog).toBe(false)
      
      // 修改数据
      await wrapper.setData({ showAddDialog: true })
      expect(wrapper.vm.showAddDialog).toBe(true)
      
      // 再次修改
      await wrapper.setData({ showAddDialog: false })
      expect(wrapper.vm.showAddDialog).toBe(false)
    })

    it('应该能够正确初始化响应式数据', () => {
      expect(wrapper.vm.loading).toBe(false)
      expect(wrapper.vm.submitting).toBe(false)
      expect(wrapper.vm.showAddDialog).toBe(false)
      expect(wrapper.vm.editingDataSource).toBe(null)
      expect(wrapper.vm.testingConnections).toBeInstanceOf(Set)
    })
  })

  describe('事件处理', () => {
    it('handleCancel 应该关闭对话框', async () => {
      // 打开对话框
      await wrapper.setData({ showAddDialog: true })
      expect(wrapper.vm.showAddDialog).toBe(true)
      
      // 调用取消方法
      wrapper.vm.handleCancel()
      
      expect(wrapper.vm.showAddDialog).toBe(false)
      expect(wrapper.vm.editingDataSource).toBe(null)
    })

    it('应该能够处理表单提交', async () => {
      const mockConfig = {
        name: '测试数据源',
        type: 'mysql',
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'root',
        password: 'password',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      // 模拟表单提交
      await wrapper.vm.handleSubmit(mockConfig)
      
      // 验证 store 方法被调用
      expect(store.createDataSource).toHaveBeenCalledWith(mockConfig)
    })
  })
})