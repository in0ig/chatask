import { shallowMount } from '@vue/test-utils'
import TableRelationList from '@/components/DataPreparation/TableRelationList.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { ElTable, ElButton, ElTag, ElLoading } from 'element-plus'

// 模拟表关联数据
const mockTableRelations = [
  { 
    id: 1, 
    name: '用户-销售关联', 
    type: '一对一', 
    source_table: 'users', 
    target_table: 'sales', 
    fields: [
      { id: 1, source_field: 'id', target_field: 'user_id' }
    ] 
  },
  { 
    id: 2, 
    name: '产品-订单关联', 
    type: '一对多', 
    source_table: 'products', 
    target_table: 'orders', 
    fields: [
      { id: 2, source_field: 'id', target_field: 'product_id' }
    ] 
  }
]

describe('TableRelationList.vue', () => {
  let wrapper
  let store

  beforeEach(() => {
    // 设置 Pinia
    setActivePinia(createPinia())
    store = useDataPrepStore()
    
    // 模拟 store 方法
    store.fetchAllData = vi.fn()
    store.tableRelations = mockTableRelations
    store.openAddTableRelationDialog = vi.fn()
    store.openEditTableRelationDialog = vi.fn()
    store.openTableRelationGraphDialog = vi.fn()
    store.deleteTableRelation = vi.fn()
    
    // 挂载组件，使用 stub 替换 Element Plus 组件
    wrapper = shallowMount(TableRelationList, {
      global: {
        plugins: [createPinia()],
        stubs: {
          ElTable: '<div class="el-table"><slot /></div>',
          ElButton: '<button class="el-button"><slot /></button>',
          ElTag: '<span class="el-tag"><slot /></span>',
          ElLoading: '<div class="el-loading"><slot /></div>'
        }
      }
    })
  })

  // 测试1：验证表关联列表正确渲染
  it('renders table relations list correctly', () => {
    const table = wrapper.find('.el-table')
    expect(table.exists()).toBe(true)
    
    // 验证表格有2行数据
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
    
    // 验证第一行数据
    const firstRow = rows[0]
    expect(firstRow.text()).toContain('用户-销售关联')
    expect(firstRow.text()).toContain('一对一')
    expect(firstRow.text()).toContain('users')
    expect(firstRow.text()).toContain('sales')
    
    // 验证第二行数据
    const secondRow = rows[1]
    expect(secondRow.text()).toContain('产品-订单关联')
    expect(secondRow.text()).toContain('一对多')
    expect(secondRow.text()).toContain('products')
    expect(secondRow.text()).toContain('orders')
  })

  // 测试2：验证搜索功能
  it('filters table relations by search text', async () => {
    const searchInput = wrapper.find('.el-input input')
    
    // 搜索'用户'
    await searchInput.setValue('用户')
    
    // 验证只有包含'用户'的表关联显示
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('用户-销售关联')
    
    // 清空搜索
    await searchInput.setValue('')
    
    // 验证所有表关联都显示
    const allRows = wrapper.findAll('.el-table__row')
    expect(allRows.length).toBe(2)
  })

  // 测试3：验证添加表关联按钮功能
  it('calls openAddTableRelationDialog when add button is clicked', async () => {
    const addButton = wrapper.find('.el-button:contains("添加表关联")')
    await addButton.trigger('click')
    
    expect(store.openAddTableRelationDialog).toHaveBeenCalledTimes(1)
  })

  // 测试4：验证编辑表关联按钮功能
  it('calls openEditTableRelationDialog when edit button is clicked', async () => {
    const editButton = wrapper.find('.el-button:has(.el-icon-edit)')
    await editButton.trigger('click')
    
    // 验证调用了编辑方法并传入了正确的数据
    expect(store.openEditTableRelationDialog).toHaveBeenCalledTimes(1)
    expect(store.openEditTableRelationDialog).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: '用户-销售关联'
    }))
  })

  // 测试5：验证查看关系图按钮功能
  it('calls openTableRelationGraphDialog when graph button is clicked', async () => {
    const graphButton = wrapper.find('.el-button:has(.el-icon-chart-line)')
    await graphButton.trigger('click')
    
    // 验证调用了查看关系图方法并传入了正确的数据
    expect(store.openTableRelationGraphDialog).toHaveBeenCalledTimes(1)
    expect(store.openTableRelationGraphDialog).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: '用户-销售关联'
    }))
  })

  // 测试6：验证删除表关联功能
  it('calls deleteTableRelation when delete button is clicked', async () => {
    // 模拟确认对话框
    window.confirm = vi.fn(() => true)
    
    const deleteButton = wrapper.find('.el-button:has(.el-icon-delete)')
    await deleteButton.trigger('click')
    
    // 验证调用了删除方法并传入了正确的ID
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(store.deleteTableRelation).toHaveBeenCalledTimes(1)
    expect(store.deleteTableRelation).toHaveBeenCalledWith(1)
  })

  // 测试7：验证加载状态
  it('displays loading state when loading is true', async () => {
    // 模拟加载状态
    store.loading = true
    
    // 重新挂载组件
    wrapper.destroy()
    wrapper = shallowMount(TableRelationList, {
      global: {
        plugins: [createPinia()],
        stubs: {
          ElTable: '<div class="el-table"><slot /></div>',
          ElButton: '<button class="el-button"><slot /></button>',
          ElTag: '<span class="el-tag"><slot /></span>',
          ElLoading: '<div class="el-loading"><slot /></div>'
        }
      }
    })
    
    // 验证加载状态显示
    expect(wrapper.find('.el-loading').exists()).toBe(true)
  })
})
