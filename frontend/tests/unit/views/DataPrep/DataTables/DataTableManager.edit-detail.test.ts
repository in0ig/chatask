import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'
import { dataTableApi } from '@/services/dataTableApi'
import { chatbiDataSourceApi } from '@/api/chatbiDataSourceApi'

// Mock APIs
vi.mock('@/services/dataTableApi')
vi.mock('@/api/chatbiDataSourceApi')
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn(),
    prompt: vi.fn()
  }
}))

describe('DataTableManager - Edit and Detail Functionality', () => {
  let wrapper: any
  
  const mockDataSources = [
    {
      id: '1',
      name: '测试数据源',
      type: 'mysql',
      status: 'active'
    }
  ]
  
  const mockTables = [
    {
      id: '1',
      table_name: '用户表',
      data_source_id: '1',
      data_source_name: '测试数据源',
      field_count: 5,
      table_type: '表',
      description: '用户信息表',
      fields: [
        { name: 'id', type: 'int', comment: '主键' },
        { name: 'name', type: 'varchar', comment: '用户名' }
      ],
      relations: []
    }
  ]
  
  const mockFields = [
    { id: '1', field_name: 'id', data_type: 'int', description: '主键', is_primary_key: true, is_nullable: false },
    { id: '2', field_name: 'name', data_type: 'varchar', description: '用户名', is_primary_key: false, is_nullable: false },
    { id: '3', field_name: 'email', data_type: 'varchar', description: '邮箱', is_primary_key: false, is_nullable: true }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock API responses
    vi.mocked(chatbiDataSourceApi.getDataSources).mockResolvedValue({
      data: mockDataSources
    })
    
    vi.mocked(dataTableApi.getDataTables).mockResolvedValue({
      items: mockTables,
      total: 1,
      page: 1,
      page_size: 100
    })
    
    vi.mocked(dataTableApi.getFields).mockResolvedValue(mockFields)
    
    wrapper = mount(DataTableManager, {
      global: {
        stubs: {
          'el-card': { template: '<div class="el-card"><slot name="header"></slot><slot></slot></div>' },
          'el-table': { template: '<div class="el-table"><slot></slot></div>' },
          'el-table-column': { template: '<div class="el-table-column"></div>' },
          'el-button': { 
            template: '<button @click="$emit(\'click\')" :data-testid="$attrs[\'data-testid\']"><slot></slot></button>',
            emits: ['click']
          },
          'el-tag': { template: '<span class="el-tag"><slot></slot></span>' },
          'el-dialog': { 
            template: '<div v-if="modelValue" class="el-dialog"><slot name="header"></slot><slot></slot><slot name="footer"></slot></div>',
            props: ['modelValue']
          },
          'el-select': { template: '<div class="el-select"><slot></slot></div>' },
          'el-option': { template: '<div class="el-option"></div>' },
          'el-checkbox': { template: '<div class="el-checkbox"><slot></slot></div>' },
          'el-checkbox-group': { template: '<div class="el-checkbox-group"><slot></slot></div>' },
          'el-empty': { template: '<div class="el-empty"><slot></slot></div>' },
          'el-alert': { template: '<div class="el-alert"><slot></slot></div>' },
          'el-descriptions': { template: '<div class="el-descriptions"><slot></slot></div>' },
          'el-descriptions-item': { template: '<div class="el-descriptions-item"><slot></slot></div>' },
          'el-icon': { template: '<i class="el-icon"><slot></slot></i>' },
          'Plus': { template: '<span>+</span>' },
          'Search': { template: '<span>🔍</span>' }
        }
      }
    })
  })

  describe('详情查看功能', () => {
    it('应该能够打开表详情对话框', async () => {
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击查看详情按钮
      await wrapper.vm.handleViewDetail(mockTables[0])
      
      // 验证对话框打开
      expect(wrapper.vm.showDetailDialog).toBe(true)
      expect(wrapper.vm.selectedTableId).toBe('1')
    })
    
    it('应该加载表的详细字段信息', async () => {
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击查看详情
      await wrapper.vm.handleViewDetail(mockTables[0])
      
      // 等待API调用完成
      await wrapper.vm.$nextTick()
      
      // 验证API被调用
      expect(dataTableApi.getFields).toHaveBeenCalledWith('1')
      
      // 验证字段信息被更新
      const selectedTable = wrapper.vm.selectedTable
      expect(selectedTable).toBeTruthy()
      expect(selectedTable.fields).toHaveLength(3)
      expect(selectedTable.fields[0].name).toBe('id')
      expect(selectedTable.fields[0].type).toBe('int')
      expect(selectedTable.fields[0].comment).toBe('主键')
    })
    
    it('应该处理字段加载失败的情况', async () => {
      // Mock API 失败
      vi.mocked(dataTableApi.getFields).mockRejectedValue(new Error('网络错误'))
      
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击查看详情
      await wrapper.vm.handleViewDetail(mockTables[0])
      
      // 等待API调用完成
      await wrapper.vm.$nextTick()
      
      // 验证错误处理
      expect(ElMessage.warning).toHaveBeenCalledWith('加载字段信息失败，显示基本信息')
    })
  })

  describe('编辑功能', () => {
    it('应该能够打开编辑对话框', async () => {
      // Mock ElMessageBox.prompt
      vi.mocked(ElMessageBox.prompt).mockResolvedValue({ value: '新的表描述' })
      
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击编辑按钮
      await wrapper.vm.handleEditTable(mockTables[0])
      
      // 验证编辑对话框被打开
      expect(ElMessageBox.prompt).toHaveBeenCalledWith(
        '请输入新的表描述（当前：用户信息表）',
        '编辑表 "用户表"',
        expect.objectContaining({
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputValue: '用户信息表',
          inputPlaceholder: '请输入表描述'
        })
      )
    })
    
    it('应该能够更新表描述', async () => {
      // Mock ElMessageBox.prompt 返回新描述
      vi.mocked(ElMessageBox.prompt).mockResolvedValue({ value: '更新后的表描述' })
      
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击编辑按钮
      await wrapper.vm.handleEditTable(mockTables[0])
      
      // 等待更新完成
      await wrapper.vm.$nextTick()
      
      // 验证本地数据被更新
      const updatedTable = wrapper.vm.tables.find((t: any) => t.id === '1')
      expect(updatedTable.comment).toBe('更新后的表描述')
      
      // 验证成功消息
      expect(ElMessage.success).toHaveBeenCalledWith('表描述更新成功')
    })
    
    it('应该处理编辑取消的情况', async () => {
      // Mock ElMessageBox.prompt 被取消
      vi.mocked(ElMessageBox.prompt).mockRejectedValue('cancel')
      
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 模拟点击编辑按钮
      await wrapper.vm.handleEditTable(mockTables[0])
      
      // 等待处理完成
      await wrapper.vm.$nextTick()
      
      // 验证没有显示错误消息（用户主动取消）
      expect(ElMessage.error).not.toHaveBeenCalled()
      expect(ElMessage.success).not.toHaveBeenCalled()
    })
  })

  describe('组件状态管理', () => {
    it('应该正确管理选中的表ID', async () => {
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 初始状态
      expect(wrapper.vm.selectedTableId).toBeNull()
      
      // 查看详情后
      await wrapper.vm.handleViewDetail(mockTables[0])
      expect(wrapper.vm.selectedTableId).toBe('1')
      
      // 编辑时
      await wrapper.vm.handleEditTable(mockTables[0])
      expect(wrapper.vm.selectedTableId).toBe('1')
    })
    
    it('应该正确计算选中的表对象', async () => {
      // 等待组件初始化完成
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // 选中表
      await wrapper.vm.handleViewDetail(mockTables[0])
      
      // 验证计算属性
      const selectedTable = wrapper.vm.selectedTable
      expect(selectedTable).toBeTruthy()
      expect(selectedTable.id).toBe('1')
      expect(selectedTable.name).toBe('用户表')
    })
  })
})