import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessage } from 'element-plus'
import DataSourceForm from '@/components/DataSource/DataSourceForm.vue'
import { useDataSourceStore } from '@/store/modules/dataSource'
import type { DataSourceConfig } from '@/types/dataSource'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

describe('DataSource Connection Test', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataSourceStore()
    
    // Mock store methods
    store.testConnection = vi.fn()

    wrapper = mount(DataSourceForm, {
      props: {
        dataSource: null,
        loading: false
      },
      global: {
        stubs: {
          'el-form': {
            template: '<div><slot /></div>',
            methods: {
              validate: vi.fn().mockImplementation((callback) => {
                callback(true)
                return Promise.resolve(true)
              }),
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

  describe('MySQL连接测试', () => {
    const mysqlConfig: DataSourceConfig = {
      name: 'MySQL测试数据源',
      type: 'mysql',
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
    }

    it('应该成功测试MySQL连接', async () => {
      store.testConnection.mockResolvedValue({
        success: true,
        message: 'MySQL连接测试成功',
        response_time: 0.5
      })

      wrapper.vm.formData = mysqlConfig

      await wrapper.vm.testConnection()

      expect(store.testConnection).toHaveBeenCalledWith(mysqlConfig)
      expect(ElMessage.success).toHaveBeenCalledWith('连接测试成功')
    })

    it('应该处理MySQL连接超时', async () => {
      store.testConnection.mockResolvedValue({
        success: false,
        error: 'MySQL连接超时',
        error_code: 'CONNECTION_TIMEOUT'
      })

      wrapper.vm.formData = mysqlConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败: MySQL连接超时')
    })

    it('应该处理MySQL认证失败', async () => {
      store.testConnection.mockResolvedValue({
        success: false,
        error: 'Access denied for user',
        error_code: 'AUTH_FAILED'
      })

      wrapper.vm.formData = mysqlConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败: Access denied for user')
    })
  })

  describe('SQL Server连接测试', () => {
    const sqlServerConfig: DataSourceConfig = {
      name: 'SQL Server测试数据源',
      type: 'sqlserver',
      host: '192.168.1.100',
      port: 1433,
      database: 'test_db',
      username: 'sa',
      password: 'password',
      connectionPool: {
        min: 3,
        max: 15,
        timeout: 60
      }
    }

    it('应该成功测试SQL Server连接', async () => {
      store.testConnection.mockResolvedValue({
        success: true,
        message: 'SQL Server连接测试成功',
        response_time: 1.2
      })

      wrapper.vm.formData = sqlServerConfig

      await wrapper.vm.testConnection()

      expect(store.testConnection).toHaveBeenCalledWith(sqlServerConfig)
      expect(ElMessage.success).toHaveBeenCalledWith('连接测试成功')
    })

    it('应该处理SQL Server连接失败', async () => {
      store.testConnection.mockResolvedValue({
        success: false,
        error: 'Cannot connect to SQL Server',
        error_code: 'CONNECTION_FAILED'
      })

      wrapper.vm.formData = sqlServerConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败: Cannot connect to SQL Server')
    })
  })

  describe('连接池配置测试', () => {
    it('应该验证连接池最小连接数', async () => {
      const invalidConfig = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 0, // 无效的最小连接数
          max: 20,
          timeout: 30
        }
      }

      wrapper.vm.formData = invalidConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.warning).toHaveBeenCalledWith('请先填写完整的连接信息')
    })

    it('应该验证连接池最大连接数', async () => {
      const invalidConfig = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 3, // max < min
          timeout: 30
        }
      }

      wrapper.vm.formData = invalidConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.warning).toHaveBeenCalledWith('请先填写完整的连接信息')
    })

    it('应该验证连接超时时间', async () => {
      const invalidConfig = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: -1 // 无效的超时时间
        }
      }

      wrapper.vm.formData = invalidConfig

      await wrapper.vm.testConnection()

      expect(ElMessage.warning).toHaveBeenCalledWith('请先填写完整的连接信息')
    })
  })

  describe('网络错误处理', () => {
    it('应该处理网络连接错误', async () => {
      store.testConnection.mockRejectedValue(new Error('Network Error'))

      wrapper.vm.formData = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      await wrapper.vm.testConnection()

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败')
    })

    it('应该处理API服务器错误', async () => {
      store.testConnection.mockRejectedValue(new Error('Internal Server Error'))

      wrapper.vm.formData = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      await wrapper.vm.testConnection()

      expect(ElMessage.error).toHaveBeenCalledWith('连接测试失败')
    })
  })

  describe('表单验证集成', () => {
    it('应该在连接测试前验证必填字段', async () => {
      // 设置不完整的表单数据
      wrapper.vm.formData = {
        name: '',
        type: 'mysql' as const,
        host: '',
        port: 3306,
        database: '',
        username: '',
        password: '',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      await wrapper.vm.testConnection()

      expect(store.testConnection).not.toHaveBeenCalled()
      expect(ElMessage.warning).toHaveBeenCalledWith('请先填写完整的连接信息')
    })

    it('应该验证端口号格式', async () => {
      wrapper.vm.formData = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 'invalid' as any, // 无效端口
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      await wrapper.vm.testConnection()

      expect(ElMessage.warning).toHaveBeenCalledWith('请先填写完整的连接信息')
    })
  })

  describe('连接状态反馈', () => {
    it('应该显示连接测试进度', async () => {
      let resolveConnection: (value: any) => void
      const connectionPromise = new Promise(resolve => {
        resolveConnection = resolve
      })
      
      store.testConnection.mockReturnValue(connectionPromise)

      wrapper.vm.formData = {
        name: '测试数据源',
        type: 'mysql' as const,
        host: 'localhost',
        port: 3306,
        database: 'test',
        username: 'user',
        password: 'pass',
        connectionPool: {
          min: 5,
          max: 20,
          timeout: 30
        }
      }

      // 开始连接测试
      const testPromise = wrapper.vm.testConnection()

      // 验证加载状态
      expect(wrapper.vm.testing).toBe(true)

      // 完成连接测试
      resolveConnection!({ success: true })
      await testPromise

      // 验证加载状态重置
      expect(wrapper.vm.testing).toBe(false)
    })
  })
})