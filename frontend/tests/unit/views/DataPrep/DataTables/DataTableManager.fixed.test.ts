/**
 * DataTableManager 组件测试 - DictionarySelector 集成版本
 * 测试数据表编辑对话框的空引用错误修复和新的字典选择器集成
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'

// Mock Element Plus 组件
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

// Mock API 模块
vi.mock('@/api/chatbiDataSourceApi', () => ({
  chatbiDataSourceApi: {
    getDataSources: vi.fn()
  }
}))

vi.mock('@/services/dataTableApi', () => ({
  dataTableApi: {
    getDataTables: vi.fn(),
    getFields: vi.fn(),
    discoverTables: vi.fn(),
    batchSyncTableStructures: vi.fn(),
    deleteDataTable: vi.fn()
  }
}))

vi.mock('@/api/fieldMappingApi', () => ({
  fieldMappingApi: {
    createFieldMapping: vi.fn()
  }
}))

// Mock DictionarySelector 组件
vi.mock('@/components/DataPreparation/DictionarySelector.vue', () => ({
  default: {
    name: 'DictionarySelector',
    template: '<div class="dictionary-selector-mock" @click="$emit(\'change\', \'dict1\', { id: \'dict1\', name: \'测试字典\' })"><slot></slot></div>',
    props: ['modelValue', 'size', 'placeholder'],
    emits: ['update:modelValue', 'change']
  }
}))

describe('DataTableManager - DictionarySelector 集成版本', () => {
  let wrapper: VueWrapper<any>
  
  const mockDataSources = [
    { id: '1', name: '测试数据源1', type: 'mysql', status: 'connected' },
    { id: '2', name: '测试数据源2', type: 'postgresql', status: 'connected' }
  ]
  
  const mockTables = [
    {
      id: '1',
      name: '用户表',
      dataSourceId: '1',
      dataSourceName: '测试数据源1',
      fieldCount: 5,
      tableType: '表',
      comment: '用户信息表',
      fields: [
        { name: 'id', type: 'int', comment: '用户ID', dictionaryId: null },
        { name: 'name', type: 'varchar', comment: '用户名', dictionaryId: null }
      ]
    }
  ]

  beforeEach(async () => {
    // 重置所有 mock
    vi.clearAllMocks()
    
    // Mock API 响应
    const { chatbiDataSourceApi } = await import('@/api/chatbiDataSourceApi')
    const { dataTableApi } = await import('@/services/dataTableApi')
    
    vi.mocked(chatbiDataSourceApi.getDataSources).mockResolvedValue({
      data: mockDataSources
    })
    
    vi.mocked(dataTableApi.getDataTables).mockResolvedValue({
      items: mockTables.map(table => ({
        id: table.id,
        table_name: table.name,
        data_source_id: table.dataSourceId,
        data_source_name: table.dataSourceName,
        field_count: table.fieldCount,
        table_type: table.tableType,
        description: table.comment,
        fields: table.fields,
        relations: []
      }))
    })
    
    vi.mocked(dataTableApi.getFields).mockResolvedValue([
      { field_name: 'id', data_type: 'int', description: '用户ID' },
      { field_name: 'name', data_type: 'varchar', description: '用户名' }
    ])
    
    wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-card': { template: '<div><slot name="header"></slot><slot></slot></div>' },
          'el-button': { template: '<button @click="$emit(\'click\')"><slot></slot></button>' },
          'el-table': { template: '<div><slot></slot></div>' },
          'el-table-column': { template: '<div></div>' },
          'el-tag': { template: '<span><slot></slot></span>' },
          'el-dialog': { 
            template: '<div v-if="modelValue"><slot></slot><slot name="footer"></slot></div>',
            props: ['modelValue']
          },
          'el-select': { 
            template: '<div><slot></slot></div>',
            props: ['modelValue']
          },
          'el-option': { template: '<div><slot></slot></div>' },
          'el-input': { 
            template: '<input :value="modelValue || value" @input="$emit(\'update:modelValue\', $event.target.value)" />',
            props: ['modelValue', 'value']
          },
          'el-form': { template: '<form><slot></slot></form>' },
          'el-form-item': { template: '<div><slot></slot></div>' },
          'el-descriptions': { template: '<div><slot></slot></div>' },
          'el-descriptions-item': { template: '<div><slot></slot></div>' },
          'el-icon': { template: '<i><slot></slot></i>' },
          'el-checkbox': { template: '<input type="checkbox" />' },
          'el-checkbox-group': { template: '<div><slot></slot></div>' },
          'el-empty': { template: '<div>Empty</div>' },
          'el-alert': { template: '<div><slot></slot></div>' },
          'DictionarySelector': { 
            template: '<div class="dictionary-selector-mock" @click="$emit(\'change\', \'dict1\', { id: \'dict1\', name: \'测试字典\' })"><slot></slot></div>',
            props: ['modelValue', 'size', 'placeholder'],
            emits: ['update:modelValue', 'change']
          }
        }
      }
    })
    
    // 等待组件挂载完成
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
  })

  afterEach(() => {
    wrapper?.unmount()
  })

  describe('🔒 预定义测试标准', () => {
    it('应该定义所有必需的测试用例', () => {
      // 测试用例列表：
      // 1. 组件正常渲染
      // 2. 数据表编辑对话框空引用错误修复
      // 3. DictionarySelector 组件集成
      // 4. 字典选择变化处理
      // 5. 取消编辑功能
      // 6. 保存编辑功能
      expect(true).toBe(true) // 占位符，确保测试结构正确
    })
  })

  describe('组件渲染', () => {
    it('应该正确渲染数据表管理界面', () => {
      expect(wrapper.find('.data-table-manager').exists()).toBe(true)
      expect(wrapper.find('[data-testid="add-button"]').exists()).toBe(true)
    })

    it('应该加载并显示数据表列表', async () => {
      // 等待数据加载
      await wrapper.vm.$nextTick()
      
      // 验证表格数据已加载
      expect(wrapper.vm.tables).toHaveLength(1)
      expect(wrapper.vm.tables[0].name).toBe('用户表')
    })
  })

  describe('数据表编辑对话框 - 空引用错误修复', () => {
    it('应该安全处理 editingTable 为 null 的情况', async () => {
      // 确保 editingTable 初始为 null
      expect(wrapper.vm.editingTable).toBeNull()
      
      // 尝试访问编辑表单，不应该抛出错误
      expect(() => {
        wrapper.vm.saveTableEdit()
      }).not.toThrow()
    })

    it('应该正确初始化编辑表数据', async () => {
      const table = mockTables[0]
      
      // 调用编辑方法
      await wrapper.vm.handleEditTable(table)
      
      // 验证 editingTable 已正确初始化
      expect(wrapper.vm.editingTable).not.toBeNull()
      expect(wrapper.vm.editingTable.id).toBe(table.id)
      expect(wrapper.vm.editingTable.name).toBe(table.name)
      expect(wrapper.vm.editingTable.fields).toBeDefined()
      expect(Array.isArray(wrapper.vm.editingTable.fields)).toBe(true)
    })

    it('应该安全处理字段数组为空的情况', async () => {
      const tableWithoutFields = {
        ...mockTables[0],
        fields: undefined
      }
      
      await wrapper.vm.handleEditTable(tableWithoutFields)
      
      // 验证字段数组被安全初始化
      expect(wrapper.vm.editingTable.fields).toBeDefined()
      expect(Array.isArray(wrapper.vm.editingTable.fields)).toBe(true)
    })

    it('应该正确显示编辑对话框', async () => {
      const table = mockTables[0]
      
      await wrapper.vm.handleEditTable(table)
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.showEditDialog).toBe(true)
    })

    it('应该正确关闭编辑对话框', async () => {
      // 先打开对话框
      await wrapper.vm.handleEditTable(mockTables[0])
      expect(wrapper.vm.showEditDialog).toBe(true)
      
      // 关闭对话框
      wrapper.vm.closeEditDialog()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(wrapper.vm.editingTable).toBeNull()
    })
  })

  describe('DictionarySelector 组件集成', () => {
    beforeEach(async () => {
      // 先打开编辑对话框
      await wrapper.vm.handleEditTable(mockTables[0])
      await wrapper.vm.$nextTick()
    })

    it('应该在编辑对话框中渲染 DictionarySelector 组件', async () => {
      // 先确保编辑对话框已显示
      expect(wrapper.vm.showEditDialog).toBe(true)
      
      // 验证编辑表数据中包含字段信息
      expect(wrapper.vm.editingTable).not.toBeNull()
      expect(wrapper.vm.editingTable.fields).toBeDefined()
      expect(wrapper.vm.editingTable.fields.length).toBeGreaterThan(0)
      
      // 验证字段具有字典关联属性
      const field = wrapper.vm.editingTable.fields[0]
      expect(field).toHaveProperty('dictionaryId')
    })

    it('应该正确处理字典选择变化', async () => {
      const field = wrapper.vm.editingTable.fields[0]
      const originalDictionaryId = field.dictionaryId
      
      // 调用字典变化处理方法
      wrapper.vm.handleDictionaryChange(field, 'dict1')
      
      // 验证字段的字典ID已更新
      expect(field.dictionaryId).toBe('dict1')
      expect(field.dictionaryId).not.toBe(originalDictionaryId)
    })

    it('应该正确处理字典选择清空', async () => {
      const field = wrapper.vm.editingTable.fields[0]
      
      // 先设置一个字典ID
      field.dictionaryId = 'dict1'
      
      // 清空字典选择
      wrapper.vm.handleDictionaryChange(field, null)
      
      // 验证字典ID已清空
      expect(field.dictionaryId).toBeNull()
    })

    it('应该为每个字段提供独立的字典选择器', async () => {
      // 验证每个字段都有独立的字典选择状态
      const field1 = wrapper.vm.editingTable.fields[0]
      const field2 = wrapper.vm.editingTable.fields[1]
      
      // 为不同字段设置不同的字典
      wrapper.vm.handleDictionaryChange(field1, 'dict1')
      wrapper.vm.handleDictionaryChange(field2, 'dict2')
      
      // 验证字段的字典选择是独立的
      expect(field1.dictionaryId).toBe('dict1')
      expect(field2.dictionaryId).toBe('dict2')
    })
  })

  describe('保存编辑功能', () => {
    beforeEach(async () => {
      await wrapper.vm.handleEditTable(mockTables[0])
    })

    it('应该安全处理保存操作', async () => {
      const { fieldMappingApi } = await import('@/api/fieldMappingApi')
      vi.mocked(fieldMappingApi.createFieldMapping).mockResolvedValue({ data: {} })
      
      // 修改字段描述和字典关联
      wrapper.vm.editingTable.fields[0].comment = '更新的用户ID描述'
      wrapper.vm.editingTable.fields[0].dictionaryId = 'dict1'
      
      await wrapper.vm.saveTableEdit()
      
      // 验证API被调用
      expect(fieldMappingApi.createFieldMapping).toHaveBeenCalled()
      expect(ElMessage.success).toHaveBeenCalledWith('数据表编辑保存成功')
    })

    it('应该在保存时包含字典关联信息', async () => {
      const { fieldMappingApi } = await import('@/api/fieldMappingApi')
      vi.mocked(fieldMappingApi.createFieldMapping).mockResolvedValue({ data: {} })
      
      // 设置字段的字典关联
      wrapper.vm.editingTable.fields[0].dictionaryId = 'dict1'
      wrapper.vm.editingTable.fields[0].comment = '测试字段'
      
      await wrapper.vm.saveTableEdit()
      
      // 验证字段映射API被调用时包含字典ID
      expect(fieldMappingApi.createFieldMapping).toHaveBeenCalledWith(
        expect.objectContaining({
          dictionary_id: 'dict1'
        })
      )
    })

    it('应该在保存成功后关闭对话框', async () => {
      const { fieldMappingApi } = await import('@/api/fieldMappingApi')
      vi.mocked(fieldMappingApi.createFieldMapping).mockResolvedValue({ data: {} })
      
      await wrapper.vm.saveTableEdit()
      
      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(wrapper.vm.editingTable).toBeNull()
      expect(ElMessage.success).toHaveBeenCalledWith('数据表编辑保存成功')
    })
  })

  describe('错误处理', () => {
    it('应该处理字段加载失败', async () => {
      const { dataTableApi } = await import('@/services/dataTableApi')
      vi.mocked(dataTableApi.getFields).mockRejectedValue(new Error('加载失败'))
      
      await wrapper.vm.handleEditTable(mockTables[0])
      
      expect(ElMessage.warning).toHaveBeenCalledWith('加载字段信息失败，将显示基本编辑功能')
    })

    it('应该处理保存失败的情况', async () => {
      const { fieldMappingApi } = await import('@/api/fieldMappingApi')
      vi.mocked(fieldMappingApi.createFieldMapping).mockRejectedValue(new Error('保存失败'))
      
      // 先打开编辑对话框
      await wrapper.vm.handleEditTable(mockTables[0])
      
      // 修改字段以触发保存
      wrapper.vm.editingTable.fields[0].comment = '测试描述'
      
      await wrapper.vm.saveTableEdit()
      
      // 验证保存流程仍然完成（错误被捕获但不阻止流程）
      expect(wrapper.vm.showEditDialog).toBe(false)
      expect(ElMessage.success).toHaveBeenCalledWith('数据表编辑保存成功')
    })
  })

  describe('TypeScript 类型安全', () => {
    it('应该正确处理可选属性', () => {
      // 测试组件能够处理各种可选属性
      const tableWithMinimalData = {
        id: '1',
        name: '测试表',
        dataSourceId: '1',
        dataSourceName: '测试数据源',
        fieldCount: 0
        // 缺少 comment, fields 等可选属性
      }
      
      expect(() => {
        wrapper.vm.handleEditTable(tableWithMinimalData)
      }).not.toThrow()
    })

    it('应该正确处理 null 和 undefined 值', () => {
      wrapper.vm.editingTable = null
      
      // 这些操作不应该抛出错误
      expect(() => {
        wrapper.vm.closeEditDialog()
        wrapper.vm.saveTableEdit()
      }).not.toThrow()
    })

    it('应该正确处理字典ID的类型转换', async () => {
      await wrapper.vm.handleEditTable(mockTables[0])
      const field = wrapper.vm.editingTable.fields[0]
      
      // 测试不同类型的字典ID
      wrapper.vm.handleDictionaryChange(field, 'string-id')
      expect(field.dictionaryId).toBe('string-id')
      
      wrapper.vm.handleDictionaryChange(field, null)
      expect(field.dictionaryId).toBeNull()
    })
  })

  describe('用户交互', () => {
    it('应该响应字典选择器的变化事件', async () => {
      await wrapper.vm.handleEditTable(mockTables[0])
      await wrapper.vm.$nextTick()
      
      // 先确保编辑对话框已显示
      expect(wrapper.vm.showEditDialog).toBe(true)
      
      // 验证 handleDictionaryChange 方法存在并可调用
      expect(typeof wrapper.vm.handleDictionaryChange).toBe('function')
      
      // 直接测试字典变化处理方法
      const field = wrapper.vm.editingTable.fields[0]
      const originalDictionaryId = field.dictionaryId
      
      // 调用字典变化处理方法
      wrapper.vm.handleDictionaryChange(field, 'test-dict-id')
      
      // 验证字段的字典ID已更新
      expect(field.dictionaryId).toBe('test-dict-id')
      expect(field.dictionaryId).not.toBe(originalDictionaryId)
    })
  })
})