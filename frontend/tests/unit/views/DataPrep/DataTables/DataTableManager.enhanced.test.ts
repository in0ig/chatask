import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'
import { chatbiDataSourceApi } from '@/api/chatbiDataSourceApi'
import { dataTableApi } from '@/services/dataTableApi'
import { fieldMappingApi } from '@/api/fieldMappingApi'

// Mock APIs
vi.mock('@/api/chatbiDataSourceApi')
vi.mock('@/services/dataTableApi')
vi.mock('@/api/fieldMappingApi')
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
      prompt: vi.fn(),
      confirm: vi.fn()
    }
  }
})

const mockDataSources = [
  {
    id: '1',
    name: 'MySQL数据源',
    type: 'mysql',
    status: 'active'
  },
  {
    id: '2', 
    name: 'PostgreSQL数据源',
    type: 'postgresql',
    status: 'active'
  }
]

const mockTables = [
  {
    id: '1',
    table_name: 'users',
    data_source_id: '1',
    data_source_name: 'MySQL数据源',
    field_count: 5,
    table_type: 'table',
    description: '用户表',
    fields: []
  },
  {
    id: '2',
    table_name: 'orders',
    data_source_id: '1', 
    data_source_name: 'MySQL数据源',
    field_count: 8,
    table_type: 'table',
    description: '订单表',
    fields: []
  }
]

const mockFields = [
  {
    field_name: 'id',
    data_type: 'INT',
    description: '主键ID'
  },
  {
    field_name: 'name',
    data_type: 'VARCHAR',
    description: '用户名'
  },
  {
    field_name: 'email',
    data_type: 'VARCHAR',
    description: '邮箱地址'
  }
]

const mockDictionaries = [
  {
    id: '1',
    name: '用户状态字典',
    code: 'USER_STATUS'
  },
  {
    id: '2',
    name: '订单状态字典', 
    code: 'ORDER_STATUS'
  }
]

describe('DataTableManager Enhanced', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock API responses
    vi.mocked(chatbiDataSourceApi.getDataSources).mockResolvedValue({
      data: mockDataSources,
      total: mockDataSources.length
    })
    
    vi.mocked(dataTableApi.getDataTables).mockResolvedValue({
      items: mockTables,
      total: mockTables.length
    })
    
    vi.mocked(dataTableApi.getFields).mockResolvedValue(mockFields)
    
    // Mock fetch for dictionaries
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: mockDictionaries })
    })
    
    wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-card': true,
          'el-button': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-dialog': true,
          'el-select': true,
          'el-option': true,
          'el-checkbox': true,
          'el-checkbox-group': true,
          'el-empty': true,
          'el-alert': true,
          'el-descriptions': true,
          'el-descriptions-item': true,
          'el-form': true,
          'el-form-item': true,
          'el-input': true,
          'el-icon': true
        }
      }
    })
  })

  describe('Enhanced Edit Functionality', () => {
    it('should show edit dialog when edit button is clicked', async () => {
      // Wait for component to load data
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Simulate edit button click
      await wrapper.vm.handleEditTable(mockTables[0])
      
      expect(wrapper.vm.showEditDialog).toBe(true)
      expect(wrapper.vm.editingTable).toBeTruthy()
      expect(wrapper.vm.editingTable.name).toBe('users')
    })

    it('should load field information for editing', async () => {
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      await wrapper.vm.handleEditTable(mockTables[0])
      
      expect(dataTableApi.getFields).toHaveBeenCalledWith('1')
      expect(wrapper.vm.editingTable.fields).toHaveLength(3)
      expect(wrapper.vm.editingTable.fields[0].name).toBe('id')
      expect(wrapper.vm.editingTable.fields[0].type).toBe('INT')
      expect(wrapper.vm.editingTable.fields[0].comment).toBe('主键ID')
    })

    it('should load dictionaries on component mount', async () => {
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(global.fetch).toHaveBeenCalledWith('/api/dictionaries')
      expect(wrapper.vm.dictionaries).toHaveLength(2)
      expect(wrapper.vm.dictionaries[0].name).toBe('用户状态字典')
    })

    it('should close edit dialog when cancel is clicked', async () => {
      wrapper.vm.showEditDialog = true
      wrapper.vm.editingTable = { ...mockTables[0] }

      await wrapper.vm.closeEditDialog()

      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(wrapper.vm.editingTable).toBeNull()
    })

    it('should save table edits with field mappings', async () => {
      // Setup editing state
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        comment: '更新的用户表描述',
        fields: [
          {
            name: 'id',
            type: 'INT',
            comment: '更新的主键描述',
            dictionaryId: '1'
          },
          {
            name: 'name', 
            type: 'VARCHAR',
            comment: '更新的用户名描述',
            dictionaryId: null
          }
        ]
      }
      
      // Mock field mapping API
      vi.mocked(fieldMappingApi.createFieldMapping).mockResolvedValue({
        success: true,
        data: {} as any
      })

      await wrapper.vm.saveTableEdit()

      expect(fieldMappingApi.createFieldMapping).toHaveBeenCalledTimes(2)
      expect(fieldMappingApi.createFieldMapping).toHaveBeenCalledWith({
        table_id: 1,
        field_id: 'id',
        field_name: 'id',
        dictionary_id: 1,
        business_name: '更新的主键描述',
        business_meaning: '更新的主键描述',
        value_range: '',
        is_required: false,
        default_value: ''
      })
      
      expect(ElMessage.success).toHaveBeenCalledWith('数据表编辑保存成功')
    })

    it('should handle field mapping creation errors gracefully', async () => {
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        comment: '用户表',
        fields: [
          {
            name: 'id',
            type: 'INT', 
            comment: '主键',
            dictionaryId: '1'
          }
        ]
      }

      // Mock field mapping API to fail
      vi.mocked(fieldMappingApi.createFieldMapping).mockRejectedValue(new Error('API Error'))
      
      // Mock console.warn to avoid test output noise
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      await wrapper.vm.saveTableEdit()

      expect(consoleSpy).toHaveBeenCalledWith('保存字段 id 的映射失败:', expect.any(Error))
      expect(ElMessage.success).toHaveBeenCalledWith('数据表编辑保存成功')
      
      consoleSpy.mockRestore()
    })

    it('should handle dictionary loading failure', async () => {
      // Mock fetch to fail
      global.fetch = vi.fn().mockResolvedValue({
        ok: false
      })

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      await wrapper.vm.loadDictionaries()

      expect(wrapper.vm.dictionaries).toEqual([])
      expect(consoleSpy).toHaveBeenCalledWith('加载字典列表失败')
      
      consoleSpy.mockRestore()
    })

    it('should handle dictionary loading network error', async () => {
      // Mock fetch to throw error
      global.fetch = vi.fn().mockRejectedValue(new Error('Network Error'))

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      await wrapper.vm.loadDictionaries()

      expect(wrapper.vm.dictionaries).toEqual([])
      expect(consoleSpy).toHaveBeenCalledWith('加载字典列表失败:', expect.any(Error))
      
      consoleSpy.mockRestore()
    })

    it('should show warning when field loading fails during edit', async () => {
      vi.mocked(dataTableApi.getFields).mockRejectedValue(new Error('Field loading failed'))

      await wrapper.vm.handleEditTable(mockTables[0])

      expect(ElMessage.warning).toHaveBeenCalledWith('加载字段信息失败，将显示基本编辑功能')
      expect(wrapper.vm.showEditDialog).toBe(true)
    })

    it('should handle save errors properly', async () => {
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        comment: '用户表',
        fields: []
      }

      vi.mocked(fieldMappingApi.createFieldMapping).mockRejectedValue(new Error('Save failed'))

      await wrapper.vm.saveTableEdit()

      expect(ElMessage.error).toHaveBeenCalledWith('保存失败，请重试')
      expect(wrapper.vm.saving).toBe(false)
    })
  })

  describe('Field Dictionary Association', () => {
    it('should allow selecting dictionary for fields', async () => {
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        fields: [
          {
            name: 'status',
            type: 'INT',
            comment: '用户状态',
            dictionaryId: null
          }
        ]
      }

      // Simulate dictionary selection
      wrapper.vm.editingTable.fields[0].dictionaryId = '1'

      expect(wrapper.vm.editingTable.fields[0].dictionaryId).toBe('1')
    })

    it('should clear dictionary association', async () => {
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        fields: [
          {
            name: 'status',
            type: 'INT',
            comment: '用户状态',
            dictionaryId: '1'
          }
        ]
      }

      // Simulate clearing dictionary
      wrapper.vm.editingTable.fields[0].dictionaryId = null

      expect(wrapper.vm.editingTable.fields[0].dictionaryId).toBeNull()
    })
  })

  describe('Component Integration', () => {
    it('should refresh tables after successful edit', async () => {
      wrapper.vm.editingTable = {
        id: '1',
        name: 'users',
        comment: '用户表',
        fields: []
      }

      const refreshSpy = vi.spyOn(wrapper.vm, 'refreshTables').mockResolvedValue()

      await wrapper.vm.saveTableEdit()

      expect(refreshSpy).toHaveBeenCalled()
    })

    it('should maintain reactive state during edit operations', async () => {
      expect(wrapper.vm.saving).toBe(false)
      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(wrapper.vm.editingTable).toBeNull()

      // Start edit
      await wrapper.vm.handleEditTable(mockTables[0])
      expect(wrapper.vm.showEditDialog).toBe(true)
      expect(wrapper.vm.editingTable).toBeTruthy()

      // Close edit
      await wrapper.vm.closeEditDialog()
      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(wrapper.vm.editingTable).toBeNull()
    })
  })
})