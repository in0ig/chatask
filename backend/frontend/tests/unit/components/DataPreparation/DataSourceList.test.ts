import { shallowMount } from '@vue/test-utils'
import DataSourceList from '@/components/DataPreparation/DataSourceList.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { ElTable, ElButton, ElInput, ElTag, ElLoading } from 'element-plus'

// 模拟数据源数据
const mockDataSources = [
  { id: 1, name: 'MySQL 数据库', type: 'mysql', connection_string: 'localhost:3306', is_active: true, created_at: '2026-01-29' },
  { id: 2, name: '销售数据.xlsx', type: 'excel', file_path: '/uploads/1769538779-test.xlsx', is_active: false, created_at: '2026-01-28' }
]

describe('DataSourceList.vue', () => {
  let wrapper
  let store

  beforeEach(() => {
    // 设置 Pinia
    setActivePinia(createPinia())
    store = useDataPrepStore()
    
    // 模拟 store 方法
    store.fetchAllData = vi.fn()
    store.dataSources = mockDataSources
    store.openAddDataSourceDialog = vi.fn()
    store.openEditDataSourceDialog = vi.fn()
    store.toggleDataSourceActive = vi.fn()
    store.deleteDataSource = vi.fn()
    
    // 挂载组件，使用 stub 替换 Element Plus 组件
    wrapper = shallowMount(DataSourceList, {
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

  // 测试1：验证数据源列表正确渲染
  it('renders data sources list correctly', () => {
    const table = wrapper.find('.el-table')
    expect(table.exists()).toBe(true)
    
    // 验证表格有2行数据
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
    
    // 验证第一行数据
    const firstRow = rows[0]
    expect(firstRow.text()).toContain('MySQL 数据库')
    expect(firstRow.text()).toContain('mysql')
    expect(firstRow.find('.el-tag').text()).toContain('启用')
    
    // 验证第二行数据
    const secondRow = rows[1]
    expect(secondRow.text()).toContain('销售数据.xlsx')
    expect(secondRow.text()).toContain('excel')
    expect(secondRow.find('.el-tag').text()).toContain('禁用')
  })

  // 测试2：验证搜索功能
  it('filters data sources by search text', async () => {
    const searchInput = wrapper.find('.el-input input')
    
    // 搜索'MySQL'
    await searchInput.setValue('MySQL')
    
    // 验证只有包含'MySQL'的数据源显示
    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('MySQL 数据库')
    
    // 清空搜索
    await searchInput.setValue('')
    
    // 验证所有数据源都显示
    const allRows = wrapper.findAll('.el-table__row')
    expect(allRows.length).toBe(2)
  })

  // 测试3：验证添加数据源按钮功能
  it('calls openAddDataSourceDialog when add button is clicked', async () => {
    const addButton = wrapper.find('.el-button:contains("添加数据源")')
    await addButton.trigger('click')
    
    expect(store.openAddDataSourceDialog).toHaveBeenCalledTimes(1)
  })

  // 测试4：验证编辑数据源按钮功能
  it('calls openEditDataSourceDialog when edit button is clicked', async () => {
    const editButton = wrapper.find('.el-button:has(.el-icon-edit)')
    await editButton.trigger('click')
    
    // 验证调用了编辑方法并传入了正确的数据
    expect(store.openEditDataSourceDialog).toHaveBeenCalledTimes(1)
    expect(store.openEditDataSourceDialog).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: 'MySQL 数据库'
    }))
  })

  // 测试5：验证切换激活状态功能
  it('calls toggleDataSourceActive when toggle button is clicked', async () => {
    const toggleButton = wrapper.find('.el-button:has(.el-icon-switch-button)')
    await toggleButton.trigger('click')
    
    // 验证调用了切换方法并传入了正确的ID
    expect(store.toggleDataSourceActive).toHaveBeenCalledTimes(1)
    expect(store.toggleDataSourceActive).toHaveBeenCalledWith(1)
  })

  // 测试6：验证删除数据源功能
  it('calls deleteDataSource when delete button is clicked', async () => {
    // 模拟确认对话框
    window.confirm = vi.fn(() => true)
    
    const deleteButton = wrapper.find('.el-button:has(.el-icon-delete)')
    await deleteButton.trigger('click')
    
    // 验证调用了删除方法并传入了正确的ID
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(store.deleteDataSource).toHaveBeenCalledTimes(1)
    expect(store.deleteDataSource).toHaveBeenCalledWith(1)
  })

  // 测试7：验证加载状态
  it('displays loading state when loading is true', async () => {
    // 模拟加载状态
    store.loading = true
    
    // 重新挂载组件
    wrapper.destroy()
    wrapper = shallowMount(DataSourceList, {
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
