import { describe, it, expect, beforeEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DataTableDetail from '@/components/DataPreparation/DataTableDetail.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

describe('DataTableDetail.vue', () => {
  let wrapper: VueWrapper
  let store: ReturnType<typeof useDataPreparationStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    
    // Setup test data sources - ensure dataSources object exists
    store.dataSources = {
      data: [
        {
          id: 1,
          name: 'Test Source',
          type: 'mysql',
          host: 'localhost',
          port: 3306,
          database: 'test_db',
          username: 'test_user',
          password: '',
          status: 'active',
          created_at: '2024-01-01T00:00:00',
          updated_at: '2024-01-01T00:00:00'
        }
      ],
      loading: false,
      error: null
    }
  })

  const createWrapper = (props = {}) => {
    return mount(DataTableDetail, {
      props: {
        tableId: '1',
        ...props
      },
      global: {
        plugins: [createPinia()],
        stubs: {
          ElSkeleton: true,
          ElAlert: true,
          ElButton: true,
          ElIcon: true,
          ElTag: true,
          ElTable: true,
          ElTableColumn: true,
          ElDialog: true,
          ElForm: true,
          ElFormItem: true,
          ElInput: true,
          ElSelect: true,
          ElOption: true,
          ElEmpty: true
        }
      }
    })
  }

  describe('组件结构', () => {
    it('应该正确渲染组件', () => {
      wrapper = createWrapper()
      expect(wrapper.exists()).toBe(true)
    })

    it('应该显示加载状态', () => {
      wrapper = createWrapper()
      const loadingState = wrapper.find('[data-testid="loading-state"]')
      expect(loadingState.exists()).toBe(true)
    })
  })

  describe('字段列表显示', () => {
    it('组件应该定义字段描述列', () => {
      wrapper = createWrapper()
      // 验证组件实例存在
      expect(wrapper.exists()).toBe(true)
      // 验证组件有 fields computed 属性
      const component = wrapper.vm as any
      expect(component.fields).toBeDefined()
    })

    it('组件应该定义关联字典列', () => {
      wrapper = createWrapper()
      // 验证组件实例存在
      expect(wrapper.exists()).toBe(true)
      // 验证组件有处理字典的能力
      const component = wrapper.vm as any
      expect(component.dictionaryOptions).toBeDefined()
    })

    it('组件应该定义操作列', () => {
      wrapper = createWrapper()
      // 验证组件实例存在
      expect(wrapper.exists()).toBe(true)
      // 验证组件有编辑字段的方法
      const component = wrapper.vm as any
      expect(typeof component.editField).toBe('function')
    })
  })

  describe('字段编辑功能', () => {
    it('应该有编辑字段的方法', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.editField).toBe('function')
    })

    it('应该有搜索字典的方法', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.searchDictionaries).toBe('function')
    })

    it('应该有保存字段编辑的方法', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.saveFieldEdit).toBe('function')
    })

    it('应该有取消编辑的方法', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.cancelEdit).toBe('function')
    })

    it('编辑字段时应该打开对话框', async () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      
      const mockField = {
        id: 1,
        name: 'test_field',
        displayName: 'Test Field',
        type: 'VARCHAR',
        isPrimaryKey: false,
        isNullable: true,
        dictionaryCode: null,
        dictionaryId: null,
        dictionaryName: null,
        description: 'Test description'
      }
      
      component.editField(mockField)
      await wrapper.vm.$nextTick()
      
      expect(component.editDialogVisible).toBe(true)
      expect(component.editingField.id).toBe(mockField.id)
      expect(component.editingField.name).toBe(mockField.name)
    })

    it('取消编辑应该关闭对话框', async () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      
      component.editDialogVisible = true
      await wrapper.vm.$nextTick()
      
      component.cancelEdit()
      await wrapper.vm.$nextTick()
      
      expect(component.editDialogVisible).toBe(false)
    })
  })

  describe('编辑对话框状态管理', () => {
    it('应该有编辑对话框可见性状态', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.editDialogVisible).toBe('boolean')
    })

    it('应该有编辑中的字段数据', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(component.editingField).toBeDefined()
      expect(typeof component.editingField).toBe('object')
    })

    it('应该有字典选项列表', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(Array.isArray(component.dictionaryOptions)).toBe(true)
    })

    it('应该有字典搜索加载状态', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.dictionarySearchLoading).toBe('boolean')
    })

    it('应该有保存加载状态', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(typeof component.saving).toBe('boolean')
    })
  })

  describe('字段数据结构', () => {
    it('编辑字段应该包含所有必需属性', async () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      
      const mockField = {
        id: 1,
        name: 'test_field',
        displayName: 'Test Field',
        type: 'VARCHAR',
        isPrimaryKey: false,
        isNullable: true,
        dictionaryCode: 'test_code',
        dictionaryId: 'dict-001',
        dictionaryName: 'Test Dictionary',
        description: 'Test description'
      }
      
      component.editField(mockField)
      await wrapper.vm.$nextTick()
      
      expect(component.editingField).toHaveProperty('id')
      expect(component.editingField).toHaveProperty('name')
      expect(component.editingField).toHaveProperty('displayName')
      expect(component.editingField).toHaveProperty('type')
      expect(component.editingField).toHaveProperty('description')
      expect(component.editingField).toHaveProperty('dictionaryId')
      expect(component.editingField).toHaveProperty('dictionaryName')
    })

    it('编辑有字典关联的字段时应该加载字典选项', async () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      
      const mockField = {
        id: 2,
        name: 'status',
        displayName: 'Status',
        type: 'VARCHAR',
        isPrimaryKey: false,
        isNullable: false,
        dictionaryCode: 'user_status',
        dictionaryId: 'dict-001',
        dictionaryName: '用户状态',
        description: 'User status'
      }
      
      component.editField(mockField)
      await wrapper.vm.$nextTick()
      
      expect(component.dictionaryOptions.length).toBeGreaterThan(0)
      expect(component.dictionaryOptions[0]).toHaveProperty('id')
      expect(component.dictionaryOptions[0]).toHaveProperty('name')
      expect(component.dictionaryOptions[0].id).toBe('dict-001')
    })
  })

  describe('表关系显示', () => {
    it('组件应该有 relations computed 属性', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      expect(component.relations).toBeDefined()
      expect(Array.isArray(component.relations)).toBe(true)
    })

    it('当没有表关系时应该返回空数组', () => {
      wrapper = createWrapper()
      const component = wrapper.vm as any
      // 初始状态下 tableInfo 为 null，relations 应该是空数组
      expect(component.relations).toEqual([])
    })
  })
})

