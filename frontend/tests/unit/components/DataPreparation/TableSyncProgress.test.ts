import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { ElDialog, ElProgress, ElButton, ElIcon } from 'element-plus'
import { Check, Close } from '@element-plus/icons-vue'
import TableSyncProgress from '@/components/DataPreparation/TableSyncProgress.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// Mock store
vi.mock('@/store/modules/dataPreparation', () => ({
  useDataPreparationStore: vi.fn(() => ({
    syncTableStructure: vi.fn(),
    batchSyncTableStructure: vi.fn()
  }))
}))

describe('TableSyncProgress', () => {
  let wrapper: VueWrapper<any>
  let mockStore: any
  
  const defaultProps = {
    visible: true,
    tableIds: ['table1', 'table2'],
    tableName: 'Test Table'
  }
  
  const createWrapper = (props = {}) => {
    return mount(TableSyncProgress, {
      props: { ...defaultProps, ...props },
      global: {
        components: {
          ElDialog,
          ElProgress,
          ElButton,
          ElIcon,
          Check,
          Close
        },
        stubs: {
          ElDialog: true,
          ElProgress: true,
          ElButton: true,
          ElIcon: true
        }
      }
    })
  }
  
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    
    mockStore = {
      syncTableStructure: vi.fn(),
      batchSyncTableStructure: vi.fn()
    }
    
    vi.mocked(useDataPreparationStore).mockReturnValue(mockStore)
  })
  
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.useRealTimers()
  })
  
  describe('组件渲染', () => {
    it('应该正确渲染同步进度对话框', () => {
      wrapper = createWrapper()
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.sync-content').exists()).toBe(true)
    })
    
    it('应该显示状态文本', () => {
      wrapper = createWrapper()
      
      const statusText = wrapper.find('.status-text')
      expect(statusText.exists()).toBe(true)
      expect(statusText.text()).toBe('准备同步')
    })
    
    it('应该在有 tableIds 时显示开始同步按钮', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      expect(vm.syncing).toBe(false)
      expect(vm.syncResult).toBe(null)
    })
  })
  
  describe('Props 验证', () => {
    it('应该接收 visible 属性', () => {
      wrapper = createWrapper({ visible: false })
      
      expect(wrapper.props('visible')).toBe(false)
    })
    
    it('应该接收 tableIds 属性', () => {
      const tableIds = ['table1', 'table2', 'table3']
      wrapper = createWrapper({ tableIds })
      
      expect(wrapper.props('tableIds')).toEqual(tableIds)
    })
    
    it('应该接收 tableName 属性', () => {
      const tableName = 'Custom Table'
      wrapper = createWrapper({ tableName })
      
      expect(wrapper.props('tableName')).toBe(tableName)
    })
  })
  
  describe('计算属性', () => {
    it('应该正确计算状态文本 - 准备同步', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      expect(vm.statusText).toBe('准备同步')
    })
    
    it('应该正确计算状态文本 - 正在同步', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      vm.syncing = true
      await wrapper.vm.$nextTick()
      
      expect(vm.statusText).toBe('正在同步表结构...')
    })
    
    it('应该正确计算状态文本 - 同步完成', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      vm.syncResult = { success: true, totalTables: 1, successCount: 1, errorCount: 0, duration: 1000 }
      await wrapper.vm.$nextTick()
      
      expect(vm.statusText).toBe('同步完成')
    })
    
    it('应该正确计算状态文本 - 同步失败', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      vm.syncResult = { success: false, totalTables: 1, successCount: 0, errorCount: 1, duration: 1000, error: '测试错误' }
      await wrapper.vm.$nextTick()
      
      expect(vm.statusText).toBe('同步失败')
    })
  })
  
  describe('事件处理', () => {
    it('应该在关闭时触发 update:visible 事件', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      vm.handleClose()
      
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')![0]).toEqual([false])
    })
    
    it('应该在有同步结果时触发 complete 事件', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      const mockResult = { success: true, totalTables: 1, successCount: 1, errorCount: 0, duration: 1000 }
      vm.syncResult = mockResult
      vm.handleClose()
      
      expect(wrapper.emitted('complete')).toBeTruthy()
      expect(wrapper.emitted('complete')![0]).toEqual([mockResult])
    })
  })
  
  describe('同步功能', () => {
    it('应该正确处理单表同步', async () => {
      const mockResult = { success: true, message: '同步成功' }
      mockStore.syncTableStructure.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ tableIds: ['table1'] })
      
      const vm = wrapper.vm as any
      await vm.startSync()
      
      expect(mockStore.syncTableStructure).toHaveBeenCalledWith('table1')
      expect(vm.syncResult.success).toBe(true)
      expect(vm.syncResult.totalTables).toBe(1)
      expect(vm.syncResult.successCount).toBe(1)
      expect(vm.syncResult.errorCount).toBe(0)
    })
    
    it('应该正确处理批量同步', async () => {
      const mockResult = { success: true, data: { successCount: 2, errorCount: 0 } }
      mockStore.batchSyncTableStructure.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ tableIds: ['table1', 'table2'] })
      
      const vm = wrapper.vm as any
      await vm.startSync()
      
      expect(mockStore.batchSyncTableStructure).toHaveBeenCalledWith(['table1', 'table2'])
      expect(vm.syncResult.success).toBe(true)
      expect(vm.syncResult.totalTables).toBe(2)
      expect(vm.syncResult.successCount).toBe(2)
      expect(vm.syncResult.errorCount).toBe(0)
    })
    
    it('应该正确处理同步失败', async () => {
      const mockResult = { success: false, message: '同步失败' }
      mockStore.syncTableStructure.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ tableIds: ['table1'] })
      
      const vm = wrapper.vm as any
      await vm.startSync()
      
      expect(vm.syncResult.success).toBe(false)
      expect(vm.syncResult.error).toBe('同步失败')
    })
    
    it('应该正确处理同步异常', async () => {
      const error = new Error('网络错误')
      mockStore.syncTableStructure.mockRejectedValue(error)
      
      wrapper = createWrapper({ tableIds: ['table1'] })
      
      const vm = wrapper.vm as any
      await vm.startSync()
      
      expect(vm.syncResult.success).toBe(false)
      expect(vm.syncResult.error).toBe('网络错误')
    })
  })
  
  describe('工具函数', () => {
    it('应该正确格式化时间', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      const timestamp = new Date('2024-01-01T12:30:45').getTime()
      const formatted = vm.formatTime(timestamp)
      
      expect(formatted).toMatch(/\d{1,2}:\d{2}:\d{2}/)
    })
    
    it('应该正确格式化持续时间 - 秒数', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      expect(vm.formatDuration(5000)).toBe('5秒')
    })
    
    it('应该正确格式化持续时间 - 分钟和秒数', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      expect(vm.formatDuration(65000)).toBe('1分5秒')
    })
    
    it('应该正确格式化持续时间 - 只有分钟', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      expect(vm.formatDuration(120000)).toBe('2分0秒')
    })
  })
})