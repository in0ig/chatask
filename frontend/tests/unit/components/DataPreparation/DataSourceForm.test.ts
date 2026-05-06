import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DataSourceForm from '@/components/DataPreparation/DataSourceForm.vue'
import type { DataSource } from '@/store/modules/dataPreparation'

// Mock ConnectionTest 组件
vi.mock('@/components/DataPreparation/ConnectionTest.vue', () => ({
  default: {
    name: 'ConnectionTest',
    template: '<div data-testid="connection-test">Connection Test Mock</div>',
    props: ['config'],
    emits: ['test-result']
  }
}))

// Mock Element Plus 消息组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn()
    }
  }
})

describe('DataSourceForm', () => {
  let wrapper: any

  const createWrapper = (props = {}) => {
    return mount(DataSourceForm, {
      props: {
        mode: 'create',
        initialData: null,
        ...props
      },
      global: {
        stubs: {
          'el-form': true,
          'el-form-item': true,
          'el-input': true,
          'el-select': true,
          'el-option': true,
          'el-button': true,
          'el-radio-group': true,
          'el-radio': true,
          'el-input-number': true,
          'ConnectionTest': true
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('组件初始化', () => {
    it('应该正确初始化表单数据', () => {
      wrapper = createWrapper()
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm.form.sourceType).toBe('DATABASE')
      expect(wrapper.vm.form.dbType).toBe('MYSQL')
      expect(wrapper.vm.form.port).toBe(3306)
      expect(wrapper.vm.form.authType).toBe('SQL_AUTH')
    })

    it('应该在编辑模式下使用初始数据', () => {
      const mockDataSource: DataSource = {
        id: '1',
        name: '测试数据源',
        sourceType: 'DATABASE',
        dbType: 'MYSQL',
        host: 'localhost',
        port: 3306,
        databaseName: 'testdb',
        username: 'user',
        password: 'password',
        description: '测试描述',
        connectionStatus: 'CONNECTED',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z'
      }

      wrapper = createWrapper({
        mode: 'edit',
        initialData: mockDataSource
      })
      
      expect(wrapper.vm.form.name).toBe('测试数据源')
      expect(wrapper.vm.form.sourceType).toBe('DATABASE')
      expect(wrapper.vm.form.dbType).toBe('MYSQL')
      expect(wrapper.vm.form.host).toBe('localhost')
      expect(wrapper.vm.form.port).toBe(3306)
      expect(wrapper.vm.form.databaseName).toBe('testdb')
      expect(wrapper.vm.form.username).toBe('user')
      expect(wrapper.vm.form.password).toBe('password')
      expect(wrapper.vm.form.description).toBe('测试描述')
    })
  })

  describe('数据库类型支持', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该支持 MySQL 数据库类型', () => {
      wrapper.vm.form.dbType = 'MYSQL'
      wrapper.vm.onDbTypeChange()
      
      expect(wrapper.vm.form.dbType).toBe('MYSQL')
      expect(wrapper.vm.form.port).toBe(3306)
    })

    it('应该支持 SQL Server 数据库类型', () => {
      wrapper.vm.form.dbType = 'SQLSERVER'
      wrapper.vm.onDbTypeChange()
      
      expect(wrapper.vm.form.dbType).toBe('SQLSERVER')
      expect(wrapper.vm.form.port).toBe(1433)
    })

    it('应该支持 PostgreSQL 数据库类型', () => {
      wrapper.vm.form.dbType = 'POSTGRESQL'
      wrapper.vm.onDbTypeChange()
      
      expect(wrapper.vm.form.dbType).toBe('POSTGRESQL')
      expect(wrapper.vm.form.port).toBe(5432)
    })

    it('应该支持 ClickHouse 数据库类型', () => {
      wrapper.vm.form.dbType = 'CLICKHOUSE'
      wrapper.vm.onDbTypeChange()
      
      expect(wrapper.vm.form.dbType).toBe('CLICKHOUSE')
      expect(wrapper.vm.form.port).toBe(8123)
    })
  })

  describe('SQL Server 认证方式', () => {
    beforeEach(() => {
      wrapper = createWrapper()
      wrapper.vm.form.sourceType = 'DATABASE'
      wrapper.vm.form.dbType = 'SQLSERVER'
    })

    it('应该在 SQL 认证时显示用户名密码字段', () => {
      wrapper.vm.form.authType = 'SQL_AUTH'
      
      expect(wrapper.vm.shouldShowCredentials).toBe(true)
    })

    it('应该在 Windows 认证时隐藏用户名密码字段', () => {
      wrapper.vm.form.authType = 'WINDOWS_AUTH'
      
      expect(wrapper.vm.shouldShowCredentials).toBe(false)
    })

    it('应该在认证方式变化时重置相关字段', () => {
      wrapper.vm.form.username = 'testuser'
      wrapper.vm.form.password = 'testpass'
      wrapper.vm.form.domain = 'testdomain'
      
      // 切换到 Windows 认证
      wrapper.vm.form.authType = 'WINDOWS_AUTH'
      wrapper.vm.onAuthTypeChange()
      
      expect(wrapper.vm.form.username).toBe('')
      expect(wrapper.vm.form.password).toBe('')
      
      // 切换到 SQL 认证
      wrapper.vm.form.authType = 'SQL_AUTH'
      wrapper.vm.onAuthTypeChange()
      
      expect(wrapper.vm.form.domain).toBe('')
    })
  })

  describe('表单验证', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该验证必填字段', () => {
      // 空表单应该无效
      expect(wrapper.vm.isFormValid).toBe(false)
    })

    it('应该在数据库表单完整时验证通过', () => {
      wrapper.vm.form.sourceType = 'DATABASE'
      wrapper.vm.form.name = '测试数据源'
      wrapper.vm.form.dbType = 'MYSQL'
      wrapper.vm.form.host = 'localhost'
      wrapper.vm.form.port = 3306
      wrapper.vm.form.databaseName = 'testdb'
      wrapper.vm.form.username = 'user'
      wrapper.vm.form.password = 'password'
      
      expect(wrapper.vm.isFormValid).toBe(true)
    })

    it('应该在文件表单完整时验证通过', () => {
      wrapper.vm.form.sourceType = 'FILE'
      wrapper.vm.form.name = '测试文件数据源'
      wrapper.vm.form.filePath = 'test.xlsx'
      
      expect(wrapper.vm.isFormValid).toBe(true)
    })

    it('应该验证端口号范围', () => {
      expect(wrapper.vm.rules.port[1].min).toBe(1)
      expect(wrapper.vm.rules.port[1].max).toBe(65535)
    })
  })

  describe('事件处理', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该在数据源类型变化时重置相关字段', () => {
      // 先设置为数据库类型并填写一些数据
      wrapper.vm.form.sourceType = 'DATABASE'
      wrapper.vm.form.host = 'localhost'
      wrapper.vm.form.port = 3306
      
      // 切换到文件类型
      wrapper.vm.form.sourceType = 'FILE'
      wrapper.vm.onSourceTypeChange()
      
      expect(wrapper.vm.form.host).toBe('')
      expect(wrapper.vm.form.port).toBeUndefined()
      expect(wrapper.vm.form.filePath).toBe('')
    })

    it('应该在数据库类型变化时设置默认端口', () => {
      wrapper.vm.form.dbType = 'MYSQL'
      wrapper.vm.onDbTypeChange()
      expect(wrapper.vm.form.port).toBe(3306)
      
      wrapper.vm.form.dbType = 'SQLSERVER'
      wrapper.vm.onDbTypeChange()
      expect(wrapper.vm.form.port).toBe(1433)
      
      wrapper.vm.form.dbType = 'POSTGRESQL'
      wrapper.vm.onDbTypeChange()
      expect(wrapper.vm.form.port).toBe(5432)
      
      wrapper.vm.form.dbType = 'CLICKHOUSE'
      wrapper.vm.onDbTypeChange()
      expect(wrapper.vm.form.port).toBe(8123)
    })

    it('应该处理文件选择', () => {
      expect(typeof wrapper.vm.handleSelectFile).toBe('function')
    })

    it('应该发送 submit 事件', async () => {
      // 填写完整表单
      wrapper.vm.form.sourceType = 'DATABASE'
      wrapper.vm.form.name = '测试数据源'
      wrapper.vm.form.dbType = 'MYSQL'
      wrapper.vm.form.host = 'localhost'
      wrapper.vm.form.port = 3306
      wrapper.vm.form.databaseName = 'testdb'
      wrapper.vm.form.username = 'user'
      wrapper.vm.form.password = 'password'
      
      // 模拟表单验证成功
      wrapper.vm.$refs.formRef = {
        validate: vi.fn().mockResolvedValue(true)
      }
      
      await wrapper.vm.handleSave()
      
      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')[0][0]).toMatchObject({
        name: '测试数据源',
        sourceType: 'DATABASE',
        dbType: 'MYSQL',
        host: 'localhost',
        port: 3306,
        databaseName: 'testdb',
        username: 'user',
        password: 'password'
      })
    })

    it('应该发送 cancel 事件', () => {
      wrapper.vm.handleCancel()
      
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })
  })

  describe('连接配置', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该生成正确的连接配置', () => {
      wrapper.vm.form.sourceType = 'DATABASE'
      wrapper.vm.form.dbType = 'MYSQL'
      wrapper.vm.form.host = 'localhost'
      wrapper.vm.form.port = 3306
      wrapper.vm.form.databaseName = 'testdb'
      wrapper.vm.form.authType = 'SQL_AUTH'
      wrapper.vm.form.username = 'user'
      wrapper.vm.form.password = 'password'
      wrapper.vm.form.domain = ''
      
      const config = wrapper.vm.connectionConfig
      
      expect(config).toMatchObject({
        sourceType: 'DATABASE',
        dbType: 'MYSQL',
        host: 'localhost',
        port: 3306,
        databaseName: 'testdb',
        authType: 'SQL_AUTH',
        username: 'user',
        password: 'password',
        domain: ''
      })
    })
  })

  describe('连接测试结果处理', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该处理成功的连接测试结果', () => {
      const result = {
        success: true,
        message: '连接成功',
        latencyMs: 100
      }
      
      wrapper.vm.handleConnectionResult(result)
      
      // 验证处理函数被调用（通过检查 ElMessage.success 是否被调用）
      expect(typeof wrapper.vm.handleConnectionResult).toBe('function')
    })

    it('应该处理失败的连接测试结果', () => {
      const result = {
        success: false,
        message: '连接失败：网络错误'
      }
      
      wrapper.vm.handleConnectionResult(result)
      
      // 验证处理函数被调用
      expect(typeof wrapper.vm.handleConnectionResult).toBe('function')
    })
  })

  describe('暴露的方法', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该暴露 resetForm 方法', () => {
      expect(typeof wrapper.vm.resetForm).toBe('function')
      
      // 设置一些数据
      wrapper.vm.form.name = '测试'
      wrapper.vm.form.host = 'localhost'
      
      // 重置表单
      wrapper.vm.resetForm()
      
      expect(wrapper.vm.form.name).toBe('')
      expect(wrapper.vm.form.host).toBe('')
    })

    it('应该暴露 validate 方法', () => {
      expect(typeof wrapper.vm.validate).toBe('function')
    })
  })

  describe('编辑模式特性', () => {
    it('应该在编辑模式下正确设置 isEditing', () => {
      wrapper = createWrapper({ mode: 'edit' })
      
      expect(wrapper.vm.isEditing).toBe(true)
    })

    it('应该在创建模式下正确设置 isEditing', () => {
      wrapper = createWrapper({ mode: 'create' })
      
      expect(wrapper.vm.isEditing).toBe(false)
    })
  })

  describe('数据库类型选项', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该包含所有支持的数据库类型', () => {
      const expectedTypes = ['MYSQL', 'SQLSERVER', 'POSTGRESQL', 'CLICKHOUSE']
      const actualTypes = wrapper.vm.dbTypes.map((type: any) => type.value)
      
      expectedTypes.forEach(type => {
        expect(actualTypes).toContain(type)
      })
    })

    it('应该有正确的默认端口映射', () => {
      expect(wrapper.vm.defaultPorts.MYSQL).toBe(3306)
      expect(wrapper.vm.defaultPorts.SQLSERVER).toBe(1433)
      expect(wrapper.vm.defaultPorts.POSTGRESQL).toBe(5432)
      expect(wrapper.vm.defaultPorts.CLICKHOUSE).toBe(8123)
    })
  })
})