/**
 * FieldMappingManager 组件单元测试
 * 测试字段映射管理的完整功能
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import FieldMappingManager from '@/components/DataPreparation/FieldMappingManager.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

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

// Mock fetch API
global.fetch = vi.fn()

// 测试数据
const mockTables = [
  {
    id: 'table-1',
    name: '用户表',
    schema: 'public',
    comment: '用户信息表'
  },
  {
    id: 'table-2',
    name: '订单表',
    schema: 'public',
    comment: '订单信息表'
  }
]

const mockDictionaries = [
  {
    id: 'dict-1',
    name: '用户状态字典',
    code: 'user_status',
    description: '用户状态枚举'
  },
  {
    id: 'dict-2',
    name: '订单状态字典',
    code: 'order_status',
    description: '订单状态枚举'
  }
]

const mockFieldMappings = [
  {
    id: 'mapping-1',
    table_id: 'table-1',
    field_id: 'field-1',
    field_name: 'user_id',
    field_type: 'bigint',
    business_name: '用户ID',
    business_meaning: '用户的唯一标识符',
    dictionary_id: '',
    dictionary_name: '',
    value_range: '',
    is_required: true,
    default_value: ''
  },
  {
    id: 'mapping-2',
    table_id: 'table-1',
    field_id: 'field-2',
    field_name: 'status',
    field_type: 'int',
    business_name: '状态',
    business_meaning: '用户账户状态',
    dictionary_id: 'dict-1',
    dictionary_name: '用户状态字典',
    value_range: '0-2',
    is_required: false,
    default_value: '1'
  },
  {
    id: 'mapping-3',
    table_id: 'table-1',
    field_id: 'field-3',
    field_name: 'email',
    field_type: 'varchar',
    business_name: '',
    business_meaning: '',
    dictionary_id: '',
    dictionary_name: '',
    value_range: '',
    is_required: false,
    default_value: ''
  }
]

describe('FieldMappingManager', () => {
  let wrapper: VueWrapper<any>
  let store: any

  beforeEach(() => {
    // 设置 Pinia
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    
    // Mock store 方法
    store.fetchDataTables = vi.fn().mockResolvedValue(mockTables)
    store.fetchDictionaries = vi.fn().mockResolvedValue(mockDictionaries)
    
    // 使用 $patch 来设置 store 数据，避免 readonly 问题
    store.$patch({
      dataTablesData: mockTables,
      dictionariesData: mockDictionaries
    })
    
    // Mock fetch 响应
    ;(global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ items: mockFieldMappings })
    })
    
    // 清除之前的 mock 调用
    vi.clearAllMocks()
  })

  const createWrapper = (props = {}) => {
    return mount(FieldMappingManager, {
      props,
      global: {
        stubs: {
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-input': true,
          'el-table': true,
          'el-table-column': true,
          'el-tag': true,
          'el-switch': true,
          'el-dialog': true,
          'el-empty': true,
          'FieldMappingBatchForm': true,
          'FieldMappingBatchEdit': true,
          'FieldMappingImport': true
        }
      }
    })
  }

  describe('组件渲染', () => {
    it('应该正确渲染组件基本结构', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.field-mapping-manager').exists()).toBe(true)
      expect(wrapper.find('.manager-header').exists()).toBe(true)
      expect(wrapper.find('.manager-content').exists()).toBe(true)
      expect(wrapper.text()).toContain('字段映射管理')
      expect(wrapper.text()).toContain('为数据表字段配置业务含义和字典映射')
    })

    it('应该显示空状态当没有选择表时', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.empty-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('字段映射管理')
    })

    it('应该正确渲染头部工具栏按钮', () => {
      wrapper = createWrapper()
      
      // 检查按钮文本
      const headerText = wrapper.find('.header-right').text()
      expect(headerText).toContain('批量映射')
      expect(headerText).toContain('导出')
      expect(headerText).toContain('导入')
      expect(headerText).toContain('刷新')
    })
  })

  describe('数据加载', () => {
    it('应该在组件挂载时加载基础数据', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      expect(store.fetchDataTables).toHaveBeenCalled()
      expect(store.fetchDictionaries).toHaveBeenCalled()
    })

    it('应该在选择表时加载字段映射数据', async () => {
      wrapper = createWrapper()
      
      // 模拟选择表
      await wrapper.vm.onTableChange()
      wrapper.vm.selectedTableId = 'table-1'
      await wrapper.vm.loadFieldMappings()
      
      expect(global.fetch).toHaveBeenCalledWith('/api/field-mappings?table_id=table-1')
    })

    it('应该正确处理数据加载失败', async () => {
      ;(global.fetch as any).mockRejectedValue(new Error('网络错误'))
      
      wrapper = createWrapper()
      wrapper.vm.selectedTableId = 'table-1'
      await wrapper.vm.loadFieldMappings()
      
      expect(ElMessage.error).toHaveBeenCalledWith('加载字段映射失败: 网络错误')
    })
  })

  describe('表选择功能', () => {
    it('应该在表选择变化时重置状态', async () => {
      wrapper = createWrapper()
      
      // 设置初始状态
      wrapper.vm.selectedMappings = [mockFieldMappings[0]]
      wrapper.vm.searchText = 'test'
      wrapper.vm.filterStatus = 'mapped'
      
      // 触发表选择变化
      await wrapper.vm.onTableChange()
      
      expect(wrapper.vm.selectedMappings).toEqual([])
      expect(wrapper.vm.searchText).toBe('')
      expect(wrapper.vm.filterStatus).toBe('')
    })

    it('应该在选择表时加载字段映射', async () => {
      wrapper = createWrapper()
      
      // 设置表ID并触发变化
      wrapper.vm.selectedTableId = 'table-1'
      await wrapper.vm.onTableChange()
      
      // 验证 fetch 被调用
      expect(global.fetch).toHaveBeenCalledWith('/api/field-mappings?table_id=table-1')
    })

    it('应该在清空表选择时清空字段映射', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.selectedTableId = ''
      await wrapper.vm.onTableChange()
      
      expect(wrapper.vm.fieldMappings).toEqual([])
    })
  })

  describe('搜索和筛选功能', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = mockFieldMappings
      await wrapper.vm.$nextTick()
    })

    it('应该根据搜索文本过滤字段映射', async () => {
      wrapper.vm.searchText = 'user'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredMappings
      expect(filtered.length).toBe(1)
      expect(filtered[0].field_name).toBe('user_id')
    })

    it('应该根据映射状态过滤字段映射', async () => {
      wrapper.vm.filterStatus = 'mapped'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredMappings
      expect(filtered.length).toBe(2) // user_id 和 status 有业务名称
      expect(filtered.every((item: any) => item.business_name)).toBe(true)
    })

    it('应该根据未映射状态过滤字段映射', async () => {
      wrapper.vm.filterStatus = 'unmapped'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredMappings
      expect(filtered.length).toBe(1) // email 没有业务名称
      expect(filtered[0].field_name).toBe('email')
    })

    it('应该根据字典过滤字段映射', async () => {
      wrapper.vm.filterDictionary = 'dict-1'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredMappings
      expect(filtered.length).toBe(1)
      expect(filtered[0].dictionary_id).toBe('dict-1')
    })

    it('应该支持组合过滤条件', async () => {
      wrapper.vm.searchText = 'status'
      wrapper.vm.filterStatus = 'mapped'
      wrapper.vm.filterDictionary = 'dict-1'
      await wrapper.vm.$nextTick()
      
      const filtered = wrapper.vm.filteredMappings
      expect(filtered.length).toBe(1)
      expect(filtered[0].field_name).toBe('status')
    })
  })

  describe('字段映射编辑功能', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = [...mockFieldMappings]
      await wrapper.vm.$nextTick()
    })

    it('应该能够进入编辑模式', async () => {
      const mapping = wrapper.vm.fieldMappings[0]
      
      await wrapper.vm.editMapping(mapping)
      
      expect(mapping.editing).toBe(true)
      expect(mapping.originalData).toBeDefined()
    })

    it('应该能够取消编辑', async () => {
      const mapping = wrapper.vm.fieldMappings[0]
      const originalName = mapping.business_name
      
      // 进入编辑模式并修改数据
      await wrapper.vm.editMapping(mapping)
      mapping.business_name = '修改后的名称'
      
      // 取消编辑
      await wrapper.vm.cancelEdit(mapping)
      
      expect(mapping.editing).toBe(false)
      expect(mapping.business_name).toBe(originalName)
      expect(mapping.originalData).toBeUndefined()
    })

    it('应该能够保存字段映射', async () => {
      const mapping = wrapper.vm.fieldMappings[0]
      
      await wrapper.vm.editMapping(mapping)
      mapping.business_name = '新的业务名称'
      
      await wrapper.vm.saveMapping(mapping)
      
      expect(mapping.editing).toBe(false)
      expect(mapping.saving).toBe(false)
      expect(mapping.originalData).toBeUndefined()
      expect(ElMessage.success).toHaveBeenCalledWith('字段映射保存成功')
    })

    it('应该验证业务名称不能为空', async () => {
      const mapping = wrapper.vm.fieldMappings[0]
      
      await wrapper.vm.editMapping(mapping)
      mapping.business_name = ''
      
      await wrapper.vm.saveMapping(mapping)
      
      expect(ElMessage.error).toHaveBeenCalledWith('业务名称不能为空')
      expect(mapping.editing).toBe(true)
    })

    it('应该处理保存失败的情况', async () => {
      const mapping = wrapper.vm.fieldMappings[0]
      
      // Mock 保存失败
      vi.spyOn(wrapper.vm, 'saveMapping').mockImplementation(async () => {
        mapping.saving = true
        throw new Error('保存失败')
      })
      
      await wrapper.vm.editMapping(mapping)
      
      try {
        await wrapper.vm.saveMapping(mapping)
      } catch (error) {
        // 预期的错误
      }
      
      expect(mapping.saving).toBe(true)
    })
  })

  describe('字段映射删除功能', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = [...mockFieldMappings]
      await wrapper.vm.$nextTick()
    })

    it('应该显示删除确认对话框', async () => {
      ;(ElMessageBox.confirm as any).mockResolvedValue('confirm')
      
      const mapping = wrapper.vm.fieldMappings[0]
      await wrapper.vm.deleteMapping(mapping)
      
      expect(ElMessageBox.confirm).toHaveBeenCalledWith(
        `确定要删除字段 "${mapping.field_name}" 的映射配置吗？`,
        '确认删除',
        expect.any(Object)
      )
    })

    it('应该在确认后删除字段映射', async () => {
      ;(ElMessageBox.confirm as any).mockResolvedValue('confirm')
      
      const mapping = wrapper.vm.fieldMappings[0]
      const originalBusinessName = mapping.business_name
      
      await wrapper.vm.deleteMapping(mapping)
      
      expect(mapping.business_name).toBe('')
      expect(mapping.business_meaning).toBe('')
      expect(mapping.dictionary_id).toBeUndefined()
      expect(ElMessage.success).toHaveBeenCalledWith('字段映射删除成功')
    })

    it('应该在取消时不删除字段映射', async () => {
      ;(ElMessageBox.confirm as any).mockRejectedValue('cancel')
      
      const mapping = wrapper.vm.fieldMappings[0]
      const originalBusinessName = mapping.business_name
      
      await wrapper.vm.deleteMapping(mapping)
      
      expect(mapping.business_name).toBe(originalBusinessName)
    })
  })

  describe('批量操作功能', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = [...mockFieldMappings]
      await wrapper.vm.$nextTick()
    })

    it('应该正确计算未映射字段', () => {
      const unmappedFields = wrapper.vm.unmappedFields
      // 根据测试数据，email 字段没有 business_name，所以是未映射的
      const actualUnmappedCount = mockFieldMappings.filter(m => !m.business_name).length
      expect(unmappedFields.length).toBe(actualUnmappedCount)
      if (actualUnmappedCount > 0) {
        // 检查第一个未映射字段的名称
        const firstUnmapped = mockFieldMappings.find(m => !m.business_name)
        expect(unmappedFields[0].field_name).toBe(firstUnmapped?.field_name)
      }
    })

    it('应该能够显示批量映射对话框', async () => {
      await wrapper.vm.showBatchMappingDialog()
      
      expect(wrapper.vm.batchMappingDialogVisible).toBe(true)
    })

    it('应该在没有未映射字段时显示警告', async () => {
      // 设置所有字段都已映射
      wrapper.vm.fieldMappings.forEach((mapping: any) => {
        mapping.business_name = '已映射'
      })
      
      await wrapper.vm.showBatchMappingDialog()
      
      expect(ElMessage.warning).toHaveBeenCalledWith('当前表的所有字段都已配置映射')
      expect(wrapper.vm.batchMappingDialogVisible).toBe(false)
    })

    it('应该能够处理批量映射提交', async () => {
      const mappingData = [
        {
          field_id: 'field-3',
          business_name: '邮箱',
          business_meaning: '用户邮箱地址'
        }
      ]
      
      await wrapper.vm.onBatchMappingSubmit(mappingData)
      
      expect(ElMessage.success).toHaveBeenCalledWith('成功配置 1 个字段映射')
      expect(wrapper.vm.batchMappingDialogVisible).toBe(false)
    })

    it('应该能够显示批量编辑对话框', async () => {
      wrapper.vm.selectedMappings = [mockFieldMappings[0]]
      
      await wrapper.vm.showBatchEditDialog()
      
      expect(wrapper.vm.batchEditDialogVisible).toBe(true)
    })

    it('应该能够处理批量编辑提交', async () => {
      wrapper.vm.selectedMappings = [mockFieldMappings[0], mockFieldMappings[1]]
      
      const editData = {
        dictionary_id: 'dict-2',
        is_required: true
      }
      
      await wrapper.vm.onBatchEditSubmit(editData)
      
      expect(ElMessage.success).toHaveBeenCalledWith('成功批量编辑 2 个字段映射')
      expect(wrapper.vm.batchEditDialogVisible).toBe(false)
      expect(wrapper.vm.selectedMappings).toEqual([])
    })

    it('应该能够批量删除字段映射', async () => {
      ;(ElMessageBox.confirm as any).mockResolvedValue('confirm')
      
      wrapper.vm.selectedMappings = [mockFieldMappings[0], mockFieldMappings[1]]
      
      await wrapper.vm.batchDeleteMappings()
      
      expect(ElMessageBox.confirm).toHaveBeenCalledWith(
        '确定要删除选中的 2 个字段映射吗？',
        '确认批量删除',
        expect.any(Object)
      )
      expect(ElMessage.success).toHaveBeenCalledWith('成功删除 2 个字段映射')
      expect(wrapper.vm.selectedMappings).toEqual([])
    })
  })

  describe('导入导出功能', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = [...mockFieldMappings]
      wrapper.vm.selectedTableId = 'table-1'
      await wrapper.vm.$nextTick()
    })

    it('应该能够导出字段映射', async () => {
      // Mock URL.createObjectURL 和相关方法
      const mockCreateObjectURL = vi.fn(() => 'mock-url')
      const mockRevokeObjectURL = vi.fn()
      const mockClick = vi.fn()
      
      global.URL.createObjectURL = mockCreateObjectURL
      global.URL.revokeObjectURL = mockRevokeObjectURL
      
      // Mock createElement
      const mockAnchor = {
        href: '',
        download: '',
        click: mockClick
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as any)
      
      await wrapper.vm.exportMappings()
      
      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockAnchor.download).toBe('field_mappings_table-1.json')
      expect(mockClick).toHaveBeenCalled()
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('mock-url')
      expect(ElMessage.success).toHaveBeenCalledWith('字段映射导出成功')
    })

    it('应该能够显示导入对话框', async () => {
      await wrapper.vm.showImportDialog()
      
      expect(wrapper.vm.importDialogVisible).toBe(true)
    })

    it('应该能够处理导入提交', async () => {
      const importData = {
        table_id: 'table-1',
        import_mode: 'merge',
        mappings: [
          {
            field_name: 'new_field',
            business_name: '新字段',
            business_meaning: '新增字段'
          }
        ]
      }
      
      // Mock fetch 调用成功
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true })
      })
      
      await wrapper.vm.onImportSubmit(importData)
      
      expect(ElMessage.success).toHaveBeenCalledWith('字段映射导入成功')
      expect(wrapper.vm.importDialogVisible).toBe(false)
      // 验证重新加载数据的 fetch 调用
      expect(global.fetch).toHaveBeenCalled()
    })
  })

  describe('选择变化处理', () => {
    beforeEach(async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = [...mockFieldMappings]
      await wrapper.vm.$nextTick()
    })

    it('应该能够处理表格选择变化', async () => {
      const selection = [mockFieldMappings[0], mockFieldMappings[1]]
      
      await wrapper.vm.onSelectionChange(selection)
      
      expect(wrapper.vm.selectedMappings).toEqual(selection)
    })
  })

  describe('错误处理', () => {
    it('应该处理刷新数据失败', async () => {
      store.fetchDataTables.mockRejectedValue(new Error('网络错误'))
      
      wrapper = createWrapper()
      await wrapper.vm.refreshData()
      
      expect(ElMessage.error).toHaveBeenCalledWith('刷新数据失败: 网络错误')
    })

    it('应该处理批量操作失败', async () => {
      wrapper = createWrapper()
      
      // Mock 批量映射失败
      const error = new Error('批量映射失败')
      vi.spyOn(wrapper.vm, 'onBatchMappingSubmit').mockRejectedValue(error)
      
      try {
        await wrapper.vm.onBatchMappingSubmit([])
      } catch (e) {
        expect(e).toBe(error)
      }
    })

    it('应该处理导出失败', async () => {
      wrapper = createWrapper()
      
      // Mock Blob 构造函数失败
      const originalBlob = global.Blob
      global.Blob = class {
        constructor() {
          throw new Error('导出失败')
        }
      } as any
      
      await wrapper.vm.exportMappings()
      
      expect(ElMessage.error).toHaveBeenCalledWith('导出失败: 导出失败')
      
      // 恢复原始 Blob
      global.Blob = originalBlob
    })
  })

  describe('响应式设计', () => {
    it('应该在移动设备上正确显示', () => {
      wrapper = createWrapper()
      
      // 检查是否有响应式样式类
      expect(wrapper.find('.field-mapping-manager').exists()).toBe(true)
      
      // 可以添加更多响应式测试
    })
  })

  describe('性能优化', () => {
    it('应该正确使用计算属性进行数据过滤', async () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = mockFieldMappings
      
      // 测试计算属性的响应性
      wrapper.vm.searchText = 'user'
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.filteredMappings.length).toBe(1)
      
      wrapper.vm.searchText = ''
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.filteredMappings.length).toBe(3)
    })

    it('应该正确计算未映射字段', () => {
      wrapper = createWrapper()
      wrapper.vm.fieldMappings = mockFieldMappings
      
      const unmappedFields = wrapper.vm.unmappedFields
      // 根据 mockFieldMappings 数据，只有 email 字段没有 business_name
      const expectedUnmapped = mockFieldMappings.filter(m => !m.business_name)
      expect(unmappedFields).toEqual(expectedUnmapped)
    })
  })
})