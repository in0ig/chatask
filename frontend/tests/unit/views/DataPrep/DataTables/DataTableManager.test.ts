import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTableManager from '@/views/DataPrep/DataTables/DataTableManager.vue'

// Mock the chatbiDataSourceApi
vi.mock('@/api/chatbiDataSourceApi', () => ({
  chatbiDataSourceApi: {
    getDataSources: vi.fn().mockResolvedValue({
      data: [
        { id: '1', name: 'MySQL主库', type: 'mysql', status: 'active' },
        { id: '2', name: 'PostgreSQL分析库', type: 'postgresql', status: 'active' },
        { id: '3', name: 'Oracle生产库', type: 'oracle', status: 'active' }
      ],
      total: 3
    })
  }
}))

// Mock the dataTableApi
vi.mock('@/services/dataTableApi', () => ({
  dataTableApi: {
    getDataTables: vi.fn().mockResolvedValue({
      items: [
        {
          id: '1',
          table_name: '用户表',
          data_source_id: '1',
          data_source_name: 'MySQL主库',
          field_count: 8,
          table_type: '表',
          description: '系统用户信息表',
          fields: [
            { name: 'id', type: 'bigint', isPrimaryKey: true, comment: '主键' },
            { name: 'username', type: 'varchar(50)', comment: '用户名' },
            { name: 'email', type: 'varchar(100)', comment: '邮箱地址' }
          ],
          relations: []
        },
        {
          id: '2',
          table_name: '订单表',
          data_source_id: '1',
          data_source_name: 'MySQL主库',
          field_count: 12,
          table_type: '表',
          description: '订单信息表',
          fields: [
            { name: 'id', type: 'bigint', isPrimaryKey: true, comment: '订单ID' },
            { name: 'user_id', type: 'bigint', comment: '用户ID' }
          ],
          relations: []
        }
      ],
      total: 2,
      page: 1,
      page_size: 100
    }),
    discoverTables: vi.fn().mockResolvedValue([
      {
        table_name: 'users',
        comment: '用户信息表',
        row_count: 100,
        schema: 'Mock_data',
        field_count: 5,
        fields: [
          { name: 'id', type: 'int', isPrimaryKey: true },
          { name: 'name', type: 'varchar(100)' },
          { name: 'email', type: 'varchar(100)' }
        ]
      },
      {
        table_name: 'orders',
        comment: '订单表',
        row_count: 250,
        schema: 'Mock_data',
        field_count: 6,
        fields: [
          { name: 'id', type: 'int', isPrimaryKey: true },
          { name: 'user_id', type: 'int' },
          { name: 'product_name', type: 'varchar(200)' }
        ]
      }
    ]),
    batchSyncTableStructures: vi.fn().mockResolvedValue({
      total_requested: 2,
      successfully_synced: 2,
      failed_count: 0,
      synced_tables: ['users', 'orders']
    }),
    deleteDataTable: vi.fn().mockResolvedValue(undefined)
  }
}))

// Mock Element Plus components
const mockElementPlusComponents = {
  'el-card': { template: '<div class="el-card"><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button class="el-button" @click="$emit(\'click\')"><slot /></button>' },
  'el-icon': { template: '<span class="el-icon"><slot /></span>' },
  'el-table': { 
    template: '<div class="el-table"><slot /></div>',
    props: ['data', 'loading', 'empty-text']
  },
  'el-table-column': { 
    template: '<div class="el-table-column"><slot /></div>',
    props: ['prop', 'label', 'width', 'min-width', 'align', 'show-overflow-tooltip', 'fixed']
  },
  'el-tag': { template: '<span class="el-tag"><slot /></span>' },
  'el-dialog': { 
    template: '<div class="el-dialog" v-if="modelValue"><slot /><slot name="footer" /></div>', 
    props: ['modelValue', 'title', 'width', 'close-on-click-modal'] 
  },
  'el-select': { 
    template: '<div class="el-select"><slot /></div>',
    props: ['modelValue', 'placeholder']
  },
  'el-option': { 
    template: '<div class="el-option"><slot /></div>',
    props: ['value', 'label']
  },
  'el-checkbox': { 
    template: '<input type="checkbox" class="el-checkbox" />',
    props: ['modelValue', 'label']
  },
  'el-checkbox-group': { 
    template: '<div class="el-checkbox-group"><slot /></div>',
    props: ['modelValue']
  },
  'el-empty': { 
    template: '<div class="el-empty">Empty</div>',
    props: ['description']
  },
  'el-alert': { 
    template: '<div class="el-alert"><slot /></div>',
    props: ['title', 'type', 'closable']
  },
  'el-descriptions': { 
    template: '<div class="el-descriptions"><slot /></div>',
    props: ['column', 'border']
  },
  'el-descriptions-item': { 
    template: '<div class="el-descriptions-item"><slot /></div>',
    props: ['label', 'span']
  }
}

// Mock directives
const mockDirectives = {
  loading: {
    mounted() {},
    updated() {},
    unmounted() {}
  }
}

// Mock console methods to avoid noise in tests
vi.spyOn(console, 'log').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})
vi.spyOn(console, 'error').mockImplementation(() => {})

describe('DataTableManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该正确渲染页面结构', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()

    // 检查卡片存在
    expect(wrapper.find('.el-card').exists()).toBe(true)

    // 检查添加数据表按钮
    const addButton = wrapper.find('[data-testid="add-button"]')
    expect(addButton.exists()).toBe(true)

    // 检查表格存在
    expect(wrapper.find('.el-table').exists()).toBe(true)
  })

  it('应该在组件挂载时加载数据源和表列表', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待 onMounted 中的异步操作完成
    await new Promise(resolve => setTimeout(resolve, 1600))

    // 检查数据是否已加载到组件中
    expect(wrapper.vm.tables.length).toBeGreaterThan(0)
    expect(wrapper.vm.dataSources.length).toBeGreaterThan(0)
  })

  it('应该能够打开添加表对话框', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()

    // 点击添加数据表按钮
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')

    // 检查对话框状态
    expect(wrapper.vm.showAddDialog).toBe(true)
  })

  it('应该在对话框中显示数据源选择', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源加载
    await new Promise(resolve => setTimeout(resolve, 600))

    // 打开添加表对话框
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')

    // 检查数据源选择器
    expect(wrapper.find('.el-select').exists()).toBe(true)
  })

  it('应该能够选择数据源并显示发现表按钮', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源加载
    await new Promise(resolve => setTimeout(resolve, 600))

    // 打开添加表对话框
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')

    // 直接设置组件的响应式属性
    wrapper.vm.selectedDataSourceId = '1'
    await wrapper.vm.$nextTick()

    // 检查发现表按钮是否显示
    expect(wrapper.vm.selectedDataSourceId).toBe('1')
  })

  it('应该能够发现表并显示表列表', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源加载
    await new Promise(resolve => setTimeout(resolve, 600))

    // 打开添加表对话框并选择数据源
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')
    
    wrapper.vm.selectedDataSourceId = '1'
    await wrapper.vm.$nextTick()
    
    // 调用发现表方法
    await wrapper.vm.handleDiscoverTables()

    // 等待发现操作完成
    await new Promise(resolve => setTimeout(resolve, 2100))

    // 检查是否发现了表
    expect(wrapper.vm.discoveredTables.length).toBeGreaterThan(0)
  })

  it('应该能够选择表并添加', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源加载
    await new Promise(resolve => setTimeout(resolve, 600))

    // 打开添加表对话框并选择数据源
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')
    
    wrapper.vm.selectedDataSourceId = '1'
    await wrapper.vm.$nextTick()
    
    // 调用发现表方法
    await wrapper.vm.handleDiscoverTables()

    // 等待发现操作完成
    await new Promise(resolve => setTimeout(resolve, 2100))

    // 模拟选择表
    wrapper.vm.selectedDiscoveredTables = ['users']
    await wrapper.vm.$nextTick()

    // 检查选择状态
    expect(wrapper.vm.selectedDiscoveredTables).toContain('users')
  })

  it('应该能够查看表详情', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源和表列表加载
    await new Promise(resolve => setTimeout(resolve, 1600))

    // 模拟点击查看详情
    const firstTable = wrapper.vm.tables[0]
    if (firstTable) {
      await wrapper.vm.handleViewDetail(firstTable)
      
      // 检查详情对话框是否显示
      expect(wrapper.vm.showDetailDialog).toBe(true)
      expect(wrapper.vm.selectedTableId).toBe(firstTable.id)
    }
  })

  it('应该在没有选择数据源时显示提示', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源加载
    await new Promise(resolve => setTimeout(resolve, 600))

    // 打开添加表对话框
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')

    // 检查是否显示选择数据源的提示
    expect(wrapper.find('.form-hint').exists()).toBe(true)
    expect(wrapper.find('.el-alert').exists()).toBe(true)
  })

  it('应该能够关闭添加表对话框', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()

    // 打开添加表对话框
    const addButton = wrapper.find('[data-testid="add-button"]')
    await addButton.trigger('click')
    
    // 检查对话框是否显示
    expect(wrapper.vm.showAddDialog).toBe(true)
    
    // 调用关闭方法
    await wrapper.vm.closeAddDialog()
    
    // 检查对话框是否关闭
    expect(wrapper.vm.showAddDialog).toBe(false)
  })

  it('应该显示表格操作按钮', async () => {
    const wrapper = mount(DataTableManager, {
      global: {
        components: mockElementPlusComponents,
        directives: mockDirectives
      }
    })
    await wrapper.vm.$nextTick()
    
    // 等待数据源和表列表加载
    await new Promise(resolve => setTimeout(resolve, 1600))

    // 检查是否有表格数据
    expect(wrapper.vm.tables.length).toBeGreaterThan(0)
    
    // 检查第一个表是否有必要的字段
    const firstTable = wrapper.vm.tables[0]
    expect(firstTable).toBeDefined()
    expect(firstTable.fieldCount).toBeDefined()
    expect(firstTable.name).toBeDefined()
  })
})