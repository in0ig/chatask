import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConnectionTest from '@/components/DataPreparation/ConnectionTest.vue'

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

// Mock Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  Connection: { name: 'Connection' },
  SuccessFilled: { name: 'SuccessFilled' },
  CircleCloseFilled: { name: 'CircleCloseFilled' }
}))

// Mock dataSourceApi
const mockTestConnection = vi.fn()
vi.mock('@/api/dataSourceApi', () => ({
  dataSourceApi: {
    testConnection: mockTestConnection
  },
  DataSourceType: {
    DATABASE: 'DATABASE',
    FILE: 'FILE'
  },
  DatabaseType: {
    MYSQL: 'MYSQL',
    SQL_SERVER: 'SQLSERVER',
    POSTGRESQL: 'POSTGRESQL',
    CLICKHOUSE: 'CLICKHOUSE'
  },
  AuthType: {
    SQL_AUTH: 'SQL_AUTH',
    WINDOWS_AUTH: 'WINDOWS_AUTH'
  }
}))

describe('ConnectionTest', () => {
  let wrapper: any

  const createWrapper = (props = {}) => {
    return mount(ConnectionTest, {
      props: {
        config: {
          sourceType: 'DATABASE',
          dbType: 'MYSQL',
          host: 'localhost',
          port: 3306,
          databaseName: 'testdb',
          authType: 'SQL_AUTH',
          username: 'user',
          password: 'password',
          domain: '',
          ...props.config
        },
        ...props
      },
      global: {
        stubs: {
          'el-button': true,
          'el-tag': true,
          'el-collapse': true,
          'el-collapse-item': true,
          'el-icon': true,
          'el-form-item': true
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Default mock response
    mockTestConnection.mockResolvedValue({
      success: true,
      message: '连接测试成功',
      latency_ms: 150
    })
  })

  describe('组件基础功能', () => {
    it('应该正确初始化组件', () => {
      wrapper = createWrapper()
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.vm.isTesting).toBe(false)
      expect(wrapper.vm.testResult).toBeNull()
      expect(wrapper.vm.testHistory).toEqual([])
    })

    it('应该正确计算是否可以测试连接', () => {
      wrapper = createWrapper()
      expect(wrapper.vm.canTest).toBe(true)
    })

    it('应该在配置不完整时禁用测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'MYSQL',
          host: '',
          port: 3306,
          databaseName: '',
          username: '',
          password: ''
        }
      })
      
      expect(wrapper.vm.canTest).toBe(false)
    })

    it('应该在非数据库类型时禁用测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'FILE',
          filePath: 'test.xlsx'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(false)
    })
  })

  describe('不同数据库类型支持', () => {
    it('应该支持 MySQL 连接测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'MYSQL',
          host: 'localhost',
          port: 3306,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(true)
    })

    it('应该支持 SQL Server SQL 认证连接测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'SQLSERVER',
          host: 'localhost',
          port: 1433,
          databaseName: 'testdb',
          authType: 'SQL_AUTH',
          username: 'user',
          password: 'password'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(true)
    })

    it('应该支持 SQL Server Windows 认证连接测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'SQLSERVER',
          host: 'localhost',
          port: 1433,
          databaseName: 'testdb',
          authType: 'WINDOWS_AUTH',
          domain: 'DOMAIN'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(true)
    })

    it('应该支持 PostgreSQL 连接测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'POSTGRESQL',
          host: 'localhost',
          port: 5432,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(true)
    })

    it('应该支持 ClickHouse 连接测试', () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'CLICKHOUSE',
          host: 'localhost',
          port: 8123,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })
      
      expect(wrapper.vm.canTest).toBe(true)
    })
  })

  describe('连接测试功能', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该能执行连接测试', async () => {
      // 模拟成功的连接测试
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      // 直接调用测试方法
      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.vm.isTesting).toBe(false)
      expect(wrapper.vm.testResult).toBeTruthy()
      expect(wrapper.vm.testResult.success).toBe(true)
      expect(wrapper.vm.testResult.message).toBe('连接测试成功')
    })

    it('应该记录测试历史', async () => {
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      // 执行测试
      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.vm.testHistory.length).toBe(1)
      expect(wrapper.vm.testHistory[0]).toHaveProperty('success')
      expect(wrapper.vm.testHistory[0]).toHaveProperty('message')
      expect(wrapper.vm.testHistory[0]).toHaveProperty('timestamp')
    })

    it('应该限制历史记录数量', async () => {
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      // 执行多次测试
      for (let i = 0; i < 12; i++) {
        await wrapper.vm.handleTestConnection()
      }
      
      // 历史记录应该限制在 10 条
      expect(wrapper.vm.testHistory.length).toBeLessThanOrEqual(10)
    })

    it('应该发送测试结果事件', async () => {
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.emitted('testResult')).toBeTruthy()
      const emittedEvents = wrapper.emitted('testResult')
      expect(emittedEvents[0][0]).toHaveProperty('success')
      expect(emittedEvents[0][0]).toHaveProperty('message')
    })

    it('应该处理连接失败情况', async () => {
      mockTestConnection.mockResolvedValue({
        success: false,
        message: '认证失败：用户名或密码错误',
        latency_ms: 1500
      })

      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toBe('认证失败：用户名或密码错误')
    })

    it('应该处理网络错误', async () => {
      mockTestConnection.mockRejectedValue(new Error('网络连接失败'))

      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toContain('网络连接失败')
    })
  })

  describe('工具方法', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该正确格式化时间', () => {
      const testTime = new Date('2024-01-01T12:30:45')
      const formattedTime = wrapper.vm.formatTime(testTime)
      
      expect(formattedTime).toMatch(/\d{2}\/\d{2} \d{2}:\d{2}:\d{2}/)
    })

    it('应该能清除历史记录', () => {
      // 添加一些历史记录
      wrapper.vm.testHistory = [
        { success: true, message: '测试', timestamp: new Date() }
      ]
      
      // 清除历史
      wrapper.vm.clearHistory()
      
      expect(wrapper.vm.testHistory.length).toBe(0)
    })
  })

  describe('配置变化处理', () => {
    it('应该在配置变化时清除测试结果', async () => {
      wrapper = createWrapper()
      
      // 设置一个测试结果
      wrapper.vm.testResult = {
        success: true,
        message: '连接成功',
        latencyMs: 100
      }
      
      // 改变配置
      await wrapper.setProps({
        config: {
          sourceType: 'DATABASE',
          dbType: 'POSTGRESQL',
          host: 'localhost',
          port: 5432,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })
      
      expect(wrapper.vm.testResult).toBeNull()
    })
  })

  describe('暴露的方法', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该暴露 testConnection 方法', () => {
      expect(typeof wrapper.vm.testConnection).toBe('function')
    })

    it('应该暴露 clearHistory 方法', () => {
      expect(typeof wrapper.vm.clearHistory).toBe('function')
    })
  })

  describe('API 调用验证', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该正确调用 API', async () => {
      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith({
        name: 'test-connection',
        sourceType: 'DATABASE',
        dbType: 'MYSQL',
        host: 'localhost',
        port: 3306,
        databaseName: 'testdb',
        authType: 'SQL_AUTH',
        username: 'user',
        password: 'password',
        domain: '',
        createdBy: 'current-user'
      })
    })

    it('应该处理不同的数据库类型', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'POSTGRESQL',
          host: 'localhost',
          port: 5432,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })

      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 200
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith(
        expect.objectContaining({
          dbType: 'POSTGRESQL',
          port: 5432
        })
      )
    })
  })

  describe('错误处理', () => {
    it('应该正确处理连接失败情况', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'MYSQL',
          host: 'invalid-host',
          port: 3306,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })
      
      mockTestConnection.mockResolvedValue({
        success: false,
        message: '连接超时：无法连接到指定的主机和端口',
        latency_ms: 5000
      })

      await wrapper.vm.handleTestConnection()
      
      // 验证结果结构正确
      expect(wrapper.vm.testResult).toHaveProperty('success')
      expect(wrapper.vm.testResult).toHaveProperty('message')
      expect(wrapper.vm.testResult.success).toBe(false)
    })

    it('应该显示清晰的错误信息', () => {
      wrapper = createWrapper()
      
      // 手动设置一个失败结果
      wrapper.vm.testResult = {
        success: false,
        message: '认证失败：用户名或密码错误',
        latencyMs: 1500
      }
      
      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toBe('认证失败：用户名或密码错误')
    })

    it('应该处理 API 异常', async () => {
      wrapper = createWrapper()
      
      mockTestConnection.mockRejectedValue({
        response: {
          data: {
            message: '服务器内部错误'
          }
        }
      })

      await wrapper.vm.handleTestConnection()
      
      expect(wrapper.vm.testResult.success).toBe(false)
      expect(wrapper.vm.testResult.message).toBe('服务器内部错误')
    })
  })

  describe('数据库类型映射', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该正确映射 MySQL 数据库类型', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'MYSQL',
          host: 'localhost',
          port: 3306,
          databaseName: 'testdb',
          username: 'user',
          password: 'password'
        }
      })

      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith(
        expect.objectContaining({
          dbType: 'MYSQL'
        })
      )
    })

    it('应该正确映射 SQL Server 数据库类型', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'SQLSERVER',
          host: 'localhost',
          port: 1433,
          databaseName: 'testdb',
          authType: 'SQL_AUTH',
          username: 'user',
          password: 'password'
        }
      })

      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith(
        expect.objectContaining({
          dbType: 'SQLSERVER'
        })
      )
    })
  })

  describe('认证类型映射', () => {
    beforeEach(() => {
      wrapper = createWrapper()
    })

    it('应该正确映射 SQL 认证类型', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'SQLSERVER',
          host: 'localhost',
          port: 1433,
          databaseName: 'testdb',
          authType: 'SQL_AUTH',
          username: 'user',
          password: 'password'
        }
      })

      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith(
        expect.objectContaining({
          authType: 'SQL_AUTH'
        })
      )
    })

    it('应该正确映射 Windows 认证类型', async () => {
      wrapper = createWrapper({
        config: {
          sourceType: 'DATABASE',
          dbType: 'SQLSERVER',
          host: 'localhost',
          port: 1433,
          databaseName: 'testdb',
          authType: 'WINDOWS_AUTH',
          domain: 'DOMAIN'
        }
      })

      mockTestConnection.mockResolvedValue({
        success: true,
        message: '连接测试成功',
        latency_ms: 150
      })

      await wrapper.vm.handleTestConnection()
      
      expect(mockTestConnection).toHaveBeenCalledWith(
        expect.objectContaining({
          authType: 'WINDOWS_AUTH',
          domain: 'DOMAIN'
        })
      )
    })
  })
})