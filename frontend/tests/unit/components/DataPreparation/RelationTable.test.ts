import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import RelationTable from '@/components/DataPreparation/RelationTable.vue'

describe('RelationTable', () => {
  let wrapper: any
  let pinia: any

  beforeEach(() => {
    pinia = createPinia()
    wrapper = mount(RelationTable, {
      global: {
        plugins: [pinia],
        stubs: {
          'el-input': true,
          'el-button': true,
          'el-table': true,
          'el-table-column': true,
          'el-pagination': true,
          'el-popconfirm': true,
          'el-dialog': true
        }
      }
    })
  })

  describe('基础渲染', () => {
    it('应该正确渲染表格容器', () => {
      expect(wrapper.find('.relation-table-container').exists()).toBe(true)
    })

    it('应该有工具栏', () => {
      const toolbar = wrapper.find('.table-toolbar')
      expect(toolbar.exists()).toBe(true)
    })

    it('应该有搜索输入框', () => {
      expect(wrapper.find('el-input-stub').exists()).toBe(true)
    })

    it('应该有新建关联按钮', () => {
      const createButton = wrapper.find('el-button-stub[type="primary"]')
      expect(createButton.exists()).toBe(true)
    })

    it('应该有数据表格', () => {
      expect(wrapper.find('el-table-stub').exists()).toBe(true)
    })

    it('应该有分页组件', () => {
      expect(wrapper.find('el-pagination-stub').exists()).toBe(true)
    })

    it('应该有对话框', () => {
      expect(wrapper.find('el-dialog-stub').exists()).toBe(true)
    })
  })

  describe('搜索功能', () => {
    it('应该初始化搜索关键词为空', () => {
      expect(wrapper.vm.search).toBe('')
    })

    it('应该能够更新搜索关键词', async () => {
      await wrapper.setData({ search: '测试关键词' })
      expect(wrapper.vm.search).toBe('测试关键词')
    })

    it('应该根据搜索关键词过滤数据', async () => {
      // 设置测试数据
      await wrapper.setData({
        relations: [
          { id: 1, mainTable: 'users', relatedTable: 'orders', joinType: 'LEFT', description: '用户订单' },
          { id: 2, mainTable: 'products', relatedTable: 'categories', joinType: 'INNER', description: '产品分类' }
        ]
      })

      // 测试搜索功能
      await wrapper.setData({ search: 'users' })
      const filteredData = wrapper.vm.filteredData
      expect(filteredData.length).toBe(1)
      expect(filteredData[0].mainTable).toBe('users')
    })

    it('应该支持不区分大小写的搜索', async () => {
      await wrapper.setData({
        relations: [
          { id: 1, mainTable: 'Users', relatedTable: 'Orders', joinType: 'LEFT', description: '用户订单' }
        ]
      })

      await wrapper.setData({ search: 'users' })
      const filteredData = wrapper.vm.filteredData
      expect(filteredData.length).toBe(1)
    })
  })

  describe('数据管理', () => {
    it('应该初始化为加载状态', () => {
      expect(wrapper.vm.loading).toBe(true)
    })

    it('应该有正确的初始分页设置', () => {
      expect(wrapper.vm.currentPage).toBe(1)
      expect(wrapper.vm.pageSize).toBe(10)
      expect(wrapper.vm.total).toBe(0)
    })

    it('应该有空的关联数据数组', () => {
      expect(wrapper.vm.relations).toEqual([])
    })
  })

  describe('对话框管理', () => {
    it('应该初始化对话框为关闭状态', () => {
      expect(wrapper.vm.dialogVisible).toBe(false)
    })

    it('应该有正确的对话框初始状态', () => {
      expect(wrapper.vm.dialogTitle).toBe('')
      expect(wrapper.vm.isEdit).toBe(false)
      expect(wrapper.vm.currentRelation).toBe(null)
    })
  })

  describe('操作功能', () => {
    it('应该能够处理创建操作', async () => {
      await wrapper.vm.handleCreate()
      
      expect(wrapper.vm.isEdit).toBe(false)
      expect(wrapper.vm.dialogTitle).toBe('新建关联关系')
      expect(wrapper.vm.currentRelation).toBe(null)
      expect(wrapper.vm.dialogVisible).toBe(true)
    })

    it('应该能够处理编辑操作', async () => {
      const testRelation = {
        id: 1,
        mainTable: 'users',
        relatedTable: 'orders',
        joinType: 'LEFT',
        description: '用户订单'
      }

      await wrapper.vm.handleEdit(testRelation)
      
      expect(wrapper.vm.isEdit).toBe(true)
      expect(wrapper.vm.dialogTitle).toBe('编辑关联关系')
      expect(wrapper.vm.currentRelation).toEqual(testRelation)
      expect(wrapper.vm.dialogVisible).toBe(true)
    })

    it('应该能够处理删除操作', () => {
      const consoleSpy = vi.spyOn(console, 'log')
      const testRelation = { id: 1, mainTable: 'users', relatedTable: 'orders', joinType: 'LEFT', description: '用户订单' }
      
      wrapper.vm.handleDelete(testRelation)
      
      expect(consoleSpy).toHaveBeenCalledWith('Delete relation:', 1)
    })

    it('应该能够处理分页大小变化', () => {
      wrapper.vm.handleSizeChange(20)
      expect(wrapper.vm.pageSize).toBe(20)
    })

    it('应该能够处理当前页变化', () => {
      wrapper.vm.handleCurrentChange(2)
      expect(wrapper.vm.currentPage).toBe(2)
    })

    it('应该能够处理表单提交', () => {
      const consoleSpy = vi.spyOn(console, 'log')
      
      wrapper.vm.submitForm()
      
      expect(consoleSpy).toHaveBeenCalledWith('Form submitted')
      expect(wrapper.vm.dialogVisible).toBe(false)
    })
  })

  describe('生命周期', () => {
    it('应该在组件挂载时获取数据', () => {
      // 由于 fetchRelations 是异步的，我们检查它是否被调用
      expect(wrapper.vm.loading).toBe(true)
    })
  })

  describe('响应式设计', () => {
    it('应该有正确的样式类', () => {
      expect(wrapper.find('.relation-table-container').exists()).toBe(true)
      expect(wrapper.find('.table-toolbar').exists()).toBe(true)
      expect(wrapper.find('.table-pagination').exists()).toBe(true)
    })
  })
})