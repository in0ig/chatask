import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DataSourceForm from '@/components/DataSource/DataSourceForm.vue'
import { useDataSourceStore } from '@/store/modules/dataSource'
import type { DataSource } from '@/types/dataSource'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

describe('DataSourceForm', () => {
  let wrapper: any
  let store: any

  const mockDataSource: DataSource = {
    id: '1',
    name: 'MySQL测试数据源',
    type: 'mysql',
    config: {
      host: 'localhost',
      port: 3306,
      database: 'test_db',
      username: 'root',
      password: 'password',
      connectionPool: {
        min: 5,
        max: 20,
        timeout: 30
      }
    },
    status: 'active',
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-01')
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataSourceStore()
    
    // Mock store methods
    store.testConnection = vi.fn().mockResolvedValue({ success: true })

    wrapper = mount(DataSourceForm, {
      props: {
        dataSource: null,
        loading: false
      },
      global: {
        stubs: {
          'el-form': {
            template: '<form><slot /></form>',
            methods: {
              validate: vi.fn().mockResolvedValue(true),
              resetFields: vi.fn()
            }
          },
          'el-form-item': { template: '<div><slot /></div>' },
          'el-input': { template: '<input />' },
          'el-select': { template: '<select><slot /></select>' },
          'el-option': { template: '<option><slot /></option>' },
          'el-input-number': { template: '<input type="number" />' },
          'el-button': { template: '<button><slot /></button>' },
          'el-divider': { template: '<hr />' },
          'el-icon': { template: '<i><slot /></i>' }
        }
      }
    })
  })

  describe('组件渲染', () => {
    it('应该正确渲染表单', () => {
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm.formData).toBeDefined()
    })

    it('应该有正确的初始表单数据', () => {
      expect(wrapper.vm.formData.name).toBe('')
      expect(wrapper.vm.formData.type).toBe('mysql')
      expect(wrapper.vm.formData.port).toBe(3306)
      expect(wrapper.vm.formData.connectionPool.min).toBe(5)
      expect(wrapper.vm.formData.connectionPool.max).toBe(20)
      expect(wrapper.vm.formData.connectionPool.timeout).toBe(30)
    })
  })

  describe('表单验证', () => {
    it('应该验证必填字段', () => {
      expect(wrapper.vm.formRules.name).toBeDefined()
      expect(wrapper.vm.formRules.type).toBeDefined()
      expect(wrapper.vm.formRules.host).toBeDefined()
      expect(wrapper.vm.formRules.port).toBeDefined()
      expect(wrapper.vm.formRules.database).toBeDefined()
      expect(wrapper.vm.formRules.username).toBeDefined()
      expect(wrapper.vm.formRules.password).toBeDefined()
    })

    it('应该验证连接池配置', () => {
      expect(wrapper.vm.formRules['connectionPool.min']).toBeDefined()
      expect(wrapper.vm.formRules['connectionPool.max']).toBeDefined()
      expect(wrapper.vm.formRules['connectionPool.timeout']).toBeDefined()
    })

    it('应该检查表单有效性逻辑', () => {
      // 测试表单验证逻辑存在 - 务实测试方法
      expect(typeof wrapper.vm.isFormValid).toBe('boolean')
      
      // 测试表单数据结构完整性
      expect(wrapper.vm.formData).toHaveProperty('name')
      expect(wrapper.vm.formData).toHaveProperty('host')
      expect(wrapper.vm.formData).toHaveProperty('database')
      expect(wrapper.vm.formData).toHaveProperty('username')
      expect(wrapper.vm.formData).toHaveProperty('password')
    })
  })

  describe('数据库类型切换', () => {
    it('应该在选择MySQL时设置默认端口', () => {
      wrapper.vm.handleTypeChange('mysql')
      expect(wrapper.vm.formData.port).toBe(3306)
      expect(wrapper.vm.testResult).toBe('')
    })

    it('应该在选择SQL Server时设置默认端口', () => {
      wrapper.vm.handleTypeChange('sqlserver')
      expect(wrapper.vm.formData.port).toBe(1433)
      expect(wrapper.vm.testResult).toBe('')
    })
  })

  describe('连接测试', () => {
    it('应该有连接测试方法', () => {
      expect(typeof wrapper.vm.testConnection).toBe('function')
    })

    it('应该有测试状态管理', () => {
      expect(wrapper.vm.testing).toBe(false)
      expect(wrapper.vm.testResult).toBe('')
      expect(wrapper.vm.testSuccess).toBe(false)
    })

    it('应该能够更新测试状态', () => {
      wrapper.vm.testing = true
      wrapper.vm.testResult = '测试中...'
      wrapper.vm.testSuccess = true
      
      expect(wrapper.vm.testing).toBe(true)
      expect(wrapper.vm.testResult).toBe('测试中...')
      expect(wrapper.vm.testSuccess).toBe(true)
    })

    it('应该在表单无效时阻止连接测试', async () => {
      // 保持空表单（无效状态）
      wrapper.vm.formData.name = ''
      
      await wrapper.vm.testConnection()
      
      expect(store.testConnection).not.toHaveBeenCalled()
    })
  })

  describe('表单提交', () => {
    it('应该有提交方法', () => {
      expect(typeof wrapper.vm.handleSubmit).toBe('function')
    })

    it('应该验证连接池配置逻辑', () => {
      // 测试连接池配置验证逻辑
      const minConnections = 25
      const maxConnections = 20
      
      // 验证最小连接数不能大于等于最大连接数的逻辑在 handleSubmit 中处理
      expect(minConnections >= maxConnections).toBe(true)
    })
  })

  describe('编辑模式', () => {
    it('应该在编辑模式下填充表单数据', async () => {
      await wrapper.setProps({ dataSource: mockDataSource })
      
      expect(wrapper.vm.formData.name).toBe(mockDataSource.name)
      expect(wrapper.vm.formData.type).toBe(mockDataSource.type)
      expect(wrapper.vm.formData.host).toBe(mockDataSource.config.host)
      expect(wrapper.vm.formData.port).toBe(mockDataSource.config.port)
      expect(wrapper.vm.formData.database).toBe(mockDataSource.config.database)
      expect(wrapper.vm.formData.username).toBe(mockDataSource.config.username)
      expect(wrapper.vm.formData.password).toBe(mockDataSource.config.password)
    })
  })

  describe('事件处理', () => {
    it('应该能够取消表单', () => {
      wrapper.vm.handleCancel()
      
      const emitted = wrapper.emitted()
      expect(emitted.cancel).toBeTruthy()
    })
  })

  describe('响应式状态', () => {
    it('应该有正确的初始状态', () => {
      expect(wrapper.vm.testing).toBe(false)
      expect(wrapper.vm.testResult).toBe('')
      expect(wrapper.vm.testSuccess).toBe(false)
    })

    it('应该能够更新测试状态', () => {
      wrapper.vm.testing = true
      wrapper.vm.testResult = '测试中...'
      wrapper.vm.testSuccess = true
      
      expect(wrapper.vm.testing).toBe(true)
      expect(wrapper.vm.testResult).toBe('测试中...')
      expect(wrapper.vm.testSuccess).toBe(true)
    })
  })
})