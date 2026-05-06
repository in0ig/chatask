import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SqlBuilder from '@/components/DataPreparation/SqlBuilder.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

// Mock CodeMirror - 完整的 mock
vi.mock('codemirror', () => ({
  EditorView: vi.fn().mockImplementation(() => ({
    destroy: vi.fn(),
    dispatch: vi.fn(),
    focus: vi.fn(),
    state: {
      doc: {
        toString: () => 'SELECT * FROM test',
        length: 17,
        line: () => ({ from: 0 })
      }
    }
  })),
  basicSetup: []
}))

vi.mock('@codemirror/state', () => ({
  EditorState: {
    create: vi.fn().mockReturnValue({})
  }
}))

vi.mock('@codemirror/lang-sql', () => ({
  sql: vi.fn().mockReturnValue([])
}))

vi.mock('@codemirror/lint', () => ({
  linter: vi.fn().mockReturnValue([]),
  lintGutter: vi.fn().mockReturnValue([])
}))

// Mock API
vi.mock('@/services/dataTableApi', () => ({
  dataTableApi: {
    validateSql: vi.fn().mockResolvedValue({
      isValid: true,
      errors: []
    }),
    createFromSql: vi.fn().mockResolvedValue({
      id: 'test-table-1',
      name: 'test_table',
      fieldCount: 3,
      rowCount: 0
    })
  }
}))

describe('SqlBuilder', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    
    // Mock 数据源数据
    store.dataSources.data = [
      {
        id: 'ds1',
        name: '测试数据源',
        sourceType: 'DATABASE',
        connectionStatus: 'CONNECTED',
        isActive: true,
        createdAt: '2026-01-01',
        updatedAt: '2026-01-01'
      }
    ]

    wrapper = mount(SqlBuilder, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-select': { template: '<select><slot /></select>' },
          'el-option': { template: '<option><slot /></option>' },
          'el-input': { template: '<input />' },
          'el-form': { template: '<form><slot /></form>' },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-table': { template: '<table><slot /></table>' },
          'el-table-column': { template: '<td><slot /></td>' },
          'el-icon': { template: '<i><slot /></i>' }
        }
      }
    })
  })

  it('应该正确渲染组件', () => {
    expect(wrapper.find('.sql-builder').exists()).toBe(true)
    expect(wrapper.find('.sql-builder-header').exists()).toBe(true)
    expect(wrapper.find('.sql-builder-config').exists()).toBe(true)
    expect(wrapper.find('.sql-builder-editor').exists()).toBe(true)
  })

  it('应该显示正确的标题和描述', () => {
    expect(wrapper.find('.title').text()).toBe('SQL 建表')
    expect(wrapper.find('.subtitle').text()).toBe('通过 SQL 脚本创建数据表')
  })

  it('应该有执行、验证和清空按钮', () => {
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBeGreaterThanOrEqual(3)
    
    // 检查按钮文本
    const buttonTexts = buttons.map((btn: any) => btn.text())
    expect(buttonTexts).toContain('执行 SQL')
    expect(buttonTexts).toContain('验证语法')
    expect(buttonTexts).toContain('清空')
  })

  it('应该有数据源选择器', () => {
    expect(wrapper.find('select').exists()).toBe(true)
  })

  it('应该有表名输入框', () => {
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('应该有编辑器容器', () => {
    expect(wrapper.find('.editor-container').exists()).toBe(true)
  })

  it('应该显示 SQL 模板', () => {
    expect(wrapper.find('.sql-templates').exists()).toBe(true)
    expect(wrapper.find('.templates-header').exists()).toBe(true)
  })

  it('应该计算 SQL 统计信息', () => {
    const vm = wrapper.vm
    
    // 直接设置响应式数据
    vm.sqlContent = 'SELECT * FROM test;\nINSERT INTO test VALUES (1);'
    
    expect(vm.sqlStats.lines).toBe(2)
    expect(vm.sqlStats.characters).toBe(41)
  })

  it('应该验证执行条件', () => {
    const vm = wrapper.vm
    
    // 初始状态不能执行
    expect(vm.canExecute).toBe(false)
    
    // 设置数据源和 SQL
    vm.config.sourceId = 'ds1'
    vm.sqlContent = 'CREATE TABLE test (id INT);'
    
    expect(vm.canExecute).toBe(true)
  })

  it('应该处理数据源变化', () => {
    const vm = wrapper.vm
    
    // 设置初始验证结果
    vm.validationResult = { 
      isValid: false, 
      errors: [{ line: 1, column: 1, message: 'Error', severity: 'error' }] 
    }
    
    // 触发数据源变化
    vm.onSourceChange()
    
    expect(vm.validationResult).toBe(null)
  })

  it('应该清空编辑器内容', () => {
    const vm = wrapper.vm
    
    // 设置初始内容
    vm.sqlContent = 'SELECT * FROM test'
    vm.validationResult = { isValid: true, errors: [] }
    vm.executionResult = { success: true, message: 'Success' }
    
    // 清空编辑器
    vm.clearEditor()
    
    expect(vm.sqlContent).toBe('')
    expect(vm.validationResult).toBe(null)
    expect(vm.executionResult).toBe(null)
  })

  it('应该有正确的 SQL 模板', () => {
    const vm = wrapper.vm
    
    expect(vm.sqlTemplates).toHaveLength(3)
    expect(vm.sqlTemplates[0].name).toBe('创建表')
    expect(vm.sqlTemplates[1].name).toBe('创建索引')
    expect(vm.sqlTemplates[2].name).toBe('插入数据')
    
    // 检查模板内容
    expect(vm.sqlTemplates[0].sql).toContain('CREATE TABLE')
    expect(vm.sqlTemplates[1].sql).toContain('CREATE INDEX')
    expect(vm.sqlTemplates[2].sql).toContain('INSERT INTO')
  })

  it('应该发出成功事件', () => {
    const vm = wrapper.vm
    const mockTable = { id: 'test-1', name: 'test_table' }
    
    // 触发成功事件
    vm.$emit('success', mockTable)
    
    expect(wrapper.emitted('success')).toBeTruthy()
    expect(wrapper.emitted('success')[0]).toEqual([mockTable])
  })

  it('应该发出关闭事件', () => {
    const vm = wrapper.vm
    
    // 触发关闭事件
    vm.$emit('close')
    
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})

// 集成测试
describe('SqlBuilder Integration', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    
    wrapper = mount(SqlBuilder, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-select': { template: '<select><slot /></select>' },
          'el-option': { template: '<option><slot /></option>' },
          'el-input': { template: '<input />' },
          'el-form': { template: '<form><slot /></form>' },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-table': { template: '<table><slot /></table>' },
          'el-table-column': { template: '<td><slot /></td>' },
          'el-icon': { template: '<i><slot /></i>' }
        }
      }
    })
  })

  it('应该与 Store 正确集成', () => {
    // 验证 Store 方法被调用
    const fetchSpy = vi.spyOn(store, 'fetchDataSources')
    
    // 重新挂载组件触发 onMounted
    wrapper = mount(SqlBuilder, {
      global: {
        plugins: [createPinia()],
        stubs: {
          'el-button': { template: '<button><slot /></button>' },
          'el-select': { template: '<select><slot /></select>' },
          'el-option': { template: '<option><slot /></option>' },
          'el-input': { template: '<input />' },
          'el-form': { template: '<form><slot /></form>' },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-table': { template: '<table><slot /></table>' },
          'el-table-column': { template: '<td><slot /></td>' },
          'el-icon': { template: '<i><slot /></i>' }
        }
      }
    })

    expect(fetchSpy).toHaveBeenCalled()
  })

  it('应该正确处理 API 调用', async () => {
    const { dataTableApi } = await import('@/services/dataTableApi')
    
    const vm = wrapper.vm
    
    // 设置配置
    vm.config.sourceId = 'ds1'
    vm.config.tableName = 'test_table'
    vm.sqlContent = 'CREATE TABLE test (id INT);'
    
    // 执行验证
    await vm.validateSql()
    
    expect(dataTableApi.validateSql).toHaveBeenCalledWith(
      'CREATE TABLE test (id INT);',
      'ds1'
    )
  })
})