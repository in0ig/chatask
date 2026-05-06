import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { ElCard, ElUpload, ElButton, ElSelect, ElAlert, ElTable } from 'element-plus'
import DictionaryImportExport from '@/components/DataPreparation/DictionaryImportExport.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// Mock store
vi.mock('@/store/modules/dataPreparation', () => ({
  useDataPreparationStore: vi.fn(() => ({
    currentDictionary: {
      id: 'dict-1',
      name: '测试字典',
      code: 'TEST_DICT',
      type: 'STATIC',
      status: 'ENABLED',
      items: []
    },
    importDictionaryItems: vi.fn(),
    exportDictionaryItems: vi.fn()
  }))
}))

describe('DictionaryImportExport', () => {
  let wrapper: VueWrapper<any>
  let mockStore: any
  
  const createWrapper = (props = {}) => {
    return mount(DictionaryImportExport, {
      props,
      global: {
        components: {
          ElCard,
          ElUpload,
          ElButton,
          ElSelect,
          ElAlert,
          ElTable
        },
        stubs: {
          ElCard: true,
          ElUpload: true,
          ElButton: true,
          ElSelect: true,
          ElAlert: true,
          ElTable: true,
          ElIcon: true
        }
      }
    })
  }
  
  beforeEach(() => {
    vi.clearAllMocks()
    
    mockStore = {
      currentDictionary: {
        id: 'dict-1',
        name: '测试字典',
        code: 'TEST_DICT',
        type: 'STATIC',
        status: 'ENABLED',
        items: []
      },
      importDictionaryItems: vi.fn(),
      exportDictionaryItems: vi.fn()
    }
    
    vi.mocked(useDataPreparationStore).mockReturnValue(mockStore)
  })
  
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })
  
  describe('组件渲染', () => {
    it('应该正确渲染导入导出组件', () => {
      wrapper = createWrapper()
      
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.dictionary-import-export').exists()).toBe(true)
    })
    
    it('应该显示当前字典信息', () => {
      wrapper = createWrapper()
      
      const dictionaryInfo = wrapper.find('.dictionary-info')
      expect(dictionaryInfo.exists()).toBe(true)
      expect(dictionaryInfo.text()).toContain('测试字典')
    })
    
    it('应该显示导入和导出功能区域', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.import-section').exists()).toBe(true)
      expect(wrapper.find('.export-section').exists()).toBe(true)
    })
  })
  
  describe('Props 验证', () => {
    it('应该接收 dictionaryId 属性', () => {
      wrapper = createWrapper({ dictionaryId: 'dict-1' })
      
      expect(wrapper.props('dictionaryId')).toBe('dict-1')
    })
  })
  
  describe('文件处理', () => {
    it('应该验证文件类型', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      
      // 测试有效文件类型
      const validFile = { name: 'test.xlsx', size: 1024 }
      expect(vm.handleFileChange(validFile, [validFile])).toBe(true)
      
      // 测试无效文件类型
      const invalidFile = { name: 'test.txt', size: 1024 }
      expect(vm.handleFileChange(invalidFile, [invalidFile])).toBe(false)
    })
    
    it('应该验证文件大小', async () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      
      // 测试文件过大
      const largeFile = { name: 'test.xlsx', size: 11 * 1024 * 1024 } // 11MB
      expect(vm.handleFileChange(largeFile, [largeFile])).toBe(false)
      
      // 测试正常大小文件
      const normalFile = { name: 'test.xlsx', size: 5 * 1024 * 1024 } // 5MB
      expect(vm.handleFileChange(normalFile, [normalFile])).toBe(true)
    })
  })
  
  describe('导入功能', () => {
    it('应该正确处理导入操作', async () => {
      const mockResult = { success: true, message: '导入成功' }
      mockStore.importDictionaryItems.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ dictionaryId: 'dict-1' })
      
      const vm = wrapper.vm as any
      
      // 设置文件列表
      vm.fileList = [{ name: 'test.xlsx', raw: new File([''], 'test.xlsx') }]
      
      await vm.handleImport()
      
      expect(mockStore.importDictionaryItems).toHaveBeenCalledWith('dict-1', expect.any(File))
      expect(vm.importResult.success).toBe(true)
    })
    
    it('应该处理导入失败', async () => {
      const mockResult = { success: false, message: '导入失败' }
      mockStore.importDictionaryItems.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ dictionaryId: 'dict-1' })
      
      const vm = wrapper.vm as any
      vm.fileList = [{ name: 'test.xlsx', raw: new File([''], 'test.xlsx') }]
      
      await vm.handleImport()
      
      expect(vm.importResult.success).toBe(false)
      expect(vm.importResult.message).toBe('导入失败')
    })
  })
  
  describe('导出功能', () => {
    it('应该正确处理导出操作', async () => {
      const mockResult = { success: true, message: '导出成功' }
      mockStore.exportDictionaryItems.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ dictionaryId: 'dict-1' })
      
      const vm = wrapper.vm as any
      vm.exportFormat = 'excel'
      
      await vm.handleExport()
      
      expect(mockStore.exportDictionaryItems).toHaveBeenCalledWith('dict-1', 'excel')
    })
    
    it('应该处理导出失败', async () => {
      const mockResult = { success: false, message: '导出失败' }
      mockStore.exportDictionaryItems.mockResolvedValue(mockResult)
      
      wrapper = createWrapper({ dictionaryId: 'dict-1' })
      
      const vm = wrapper.vm as any
      
      await vm.handleExport()
      
      expect(vm.errorMessage).toBe('导出失败')
    })
  })
  
  describe('计算属性', () => {
    it('应该正确计算 hasValidFiles', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      
      // 无文件时
      vm.fileList = []
      expect(vm.hasValidFiles).toBe(false)
      
      // 有效文件时
      vm.fileList = [{ name: 'test.xlsx' }]
      expect(vm.hasValidFiles).toBe(true)
      
      // 无效文件时
      vm.fileList = [{ name: 'test.txt' }]
      expect(vm.hasValidFiles).toBe(false)
    })
  })
  
  describe('清理功能', () => {
    it('应该正确清空文件列表', () => {
      wrapper = createWrapper()
      
      const vm = wrapper.vm as any
      vm.fileList = [{ name: 'test.xlsx' }]
      vm.importResult = { success: true, message: '测试' }
      vm.errorMessage = '测试错误'
      
      vm.clearFiles()
      
      expect(vm.fileList).toEqual([])
      expect(vm.importResult).toBe(null)
      expect(vm.errorMessage).toBe('')
    })
  })
})