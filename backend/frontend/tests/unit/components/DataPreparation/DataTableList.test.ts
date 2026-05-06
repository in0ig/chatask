import { shallowMount } from '@vue/test-utils'
import DataTableList from '@/components/DataPreparation/DataTableList.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { ElTable, ElButton, ElInput, ElTag, ElLoading } from 'element-plus'

// 模拟数据表数据
const mockDataTables = [
  { id: 1, name: 'users', source_name: 'MySQL 数据库', row_count: 1000, column_count: 5, created_at: '2026-01-29', is_active: true },
  { id: 2, name: 'sales', source_name: '销售数据.xlsx', row_count: 500, column_count: 8, created_at: '2026-01-28', is_active: false }
]

describe('DataTableList.vue', () => {
  let wrapper
  let store

  beforeEach(() => {
    // 设置 Pinia
    setActivePinia(createPinia())
    store = useDataPrepStore()
    
    // 模拟 store 方法
    store.fetchAllData = vi.fn()
    store.dataTables = mockDataTables
    store.openAddDataTableDialog = vi.fn()
    store.openEditDataTableDialog = vi.fn()
    store.openTableFieldsDialog = vi.fn()
    store.deleteDataTable = vi.fn()
    store.syncTables = vi.fn()
    
    // 挂载组件，使用 stub 替换 Element Plus 组件
    wrapper = shallowMount(DataTableList, {
      global: {
        plugins: [createPinia()],
        stubs: {
          ElTable: '<div class="el-table"><slot /></div>',
          ElButton: '<button class="el-button"><slot /></button>',
          ElInput: '<input class="el-input" />',
          ElTag: '<span class="el-tag"><slot /></span>',
          ElLoading: '<div class="el-loading"><slot /></div>'
        }
      }
    })
  })

  // 测试1：验证数据表列表正确渲染
  it('renders data tables list correctly', () => {
    const table = wrapper.find('.el-table')
    expect(table.exists()).toBe(true)
    
    // 验证表格有2行数据
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
    
    // 验证第一行数据
    const firstRow = rows[0]
    expect(firstRow.text()).toContain('users')
    expect(firstRow.text()).toContain('MySQL 数据库')
    expect(firstRow.text()).toContain('1000')
    expect(firstRow.text()).toContain('5')
    expect(firstRow.find('.el-tag').text()).toContain('启用')
    
    // 验证第二行数据
    const secondRow = rows[1]
    expect(secondRow.text()).toContain('sales')
    expect(secondRow.text()).toContain('销售数据.xlsx')
    expect(secondRow.text()).toContain('500')
    expect(secondRow.text()).toContain('8')
    expect(secondRow.find('.el-tag').text()).toContain('禁用')
  })

  // 测试2：验证搜索功能
  it('filters data tables by search text', async () => {
    const searchInput = wrapper.find('.el-input input')
    
    // 搜索'users'
    await searchInput.setValue('users')
    
    // 验证只有包含'users'的数据表显示
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('users')
    
    // 清空搜索
    await searchInput.setValue('')
    
    // 验证所有数据表都显示
    const allRows = wrapper.findAll('.el-table__row')
    expect(allRows.length).toBe(2)
  })

  // 测试3：验证添加数据表按钮功能
  it('calls openAddDataTableDialog when add button is clicked', async () => {
    const addButton = wrapper.find('.el-button:contains("添加数据表")')
    await addButton.trigger('click')
    
    expect(store.openAddDataTableDialog).toHaveBeenCalledTimes(1)
  })

  // 测试4：验证编辑数据表按钮功能
  it('calls openEditDataTableDialog when edit button is clicked', async () => {
    const editButton = wrapper.find('.el-button:has(.el-icon-edit)')
    await editButton.trigger('click')
    
    // 验证调用了编辑方法并传入了正确的数据
    expect(store.openEditDataTableDialog).toHaveBeenCalledTimes(1)
    expect(store.openEditDataTableDialog).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: 'users'
    }))
  })

  // 测试5：验证查看字段按钮功能
  it('calls openTableFieldsDialog when fields button is clicked', async () => {
    const fieldsButton = wrapper.find('.el-button:has(.el-icon-view)')
    await fieldsButton.trigger('click')
    
    // 验证调用了查看字段方法并传入了正确的数据
    expect(store.openTableFieldsDialog).toHaveBeenCalledTimes(1)
    expect(store.openTableFieldsDialog).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: 'users'
    }))
  })

  // 测试6：验证删除数据表功能
  it('calls deleteDataTable when delete button is clicked', async () => {
    // 模拟确认对话框
    window.confirm = vi.fn(() => true)
    
    const deleteButton = wrapper.find('.el-button:has(.el-icon-delete)')
    await deleteButton.trigger('click')
    
    // 验证调用了删除方法并传入了正确的ID
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(store.deleteDataTable).toHaveBeenCalledTimes(1)
    expect(store.deleteDataTable).toHaveBeenCalledWith(1)
  })

  // 测试7：验证同步表功能
  it('calls syncTables when sync button is clicked', async () => {
    const syncButton = wrapper.find('.el-button:contains("同步表")')
    await syncButton.trigger('click')
    
    expect(store.syncTables).toHaveBeenCalledTimes(1)
  })

  // 测试8：验证加载状态
  it('displays loading state when loading is true', async () => {
    // 模拟加载状态
    store.loading = true
    
    // 重新挂载组件
    wrapper.destroy()
    wrapper = shallowMount(DataTableList, {
      global: {
        plugins: [createPinia()],
        stubs: {
          ElTable: '<div class="el-table"><slot /></div>',
          ElButton: '<button class="el-button"><slot /></button>',
          ElInput: '<input class="el-input" />',
          ElTag: '<span class="el-tag"><slot /></span>',
          ElLoading: '<div class="el-loading"><slot /></div>'
        }
      }
    })
    
    // 验证加载状态显示
    expect(wrapper.find('.el-loading').exists()).toBe(true)
  })
})
