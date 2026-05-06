/**
 * DictionaryImportExport组件Mock数据迁移测试
 * 
 * 测试目标：
 * 1. 验证组件使用真实的store API调用
 * 2. 验证导入导出功能正确集成
 * 3. 验证错误处理机制
 * 4. 验证用户交互流程
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessage } from 'element-plus'
import DictionaryImportExport from '@/components/DataPreparation/DictionaryImportExport.vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// Mock Element Plus
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

// Mock store
vi.mock('@/store/modules/dataPreparation', () => ({
  useDataPreparationStore: vi.fn()
}))

describe('DictionaryImportExport 组件 Mock 数据迁移测试', () => {
  let mockStore: any
  let wrapper: any

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // 创建mock store - 使用正确的方法名
    mockStore = {
      importDictionary: vi.fn(),
      exportDictionary: vi.fn()
    }
    
    vi.mocked(useDataPreparationStore).mockReturnValue(mockStore)
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.resetAllMocks()
  })

  describe('导入功能真实API集成', () => {
    beforeEach(() => {
      wrapper = mount(DictionaryImportExport, {
        props: {
          dictionaryId: 123
        }
      })
    })

    it('应该调用真实的store导入API', async () => {
      // 准备测试数据
      const mockFile = new File(['test content'], 'test.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      
      mockStore.importDictionary.mockResolvedValue(true)

      // 模拟文件选择
      await wrapper.vm.handleFileChange({ raw: mockFile })

      // 点击导入按钮
      await wrapper.vm.handleImport()

      // 验证调用了真实的store方法
      expect(mockStore.importDictionary).toHaveBeenCalledWith(mockFile)
      expect(ElMessage.success).toHaveBeenCalledWith('导入处理完成！')
    })

    it('应该正确处理导入API错误', async () => {
      const mockFile = new File(['test'], 'test.xlsx')
      
      mockStore.importDictionary.mockResolvedValue(false)

      // 模拟文件选择和导入
      await wrapper.vm.handleFileChange({ raw: mockFile })
      await wrapper.vm.handleImport()

      // 验证错误处理
      expect(mockStore.importDictionary).toHaveBeenCalledWith(mockFile)
      expect(ElMessage.error).toHaveBeenCalledWith('导入失败')
    })

    it('应该正确处理导入异常', async () => {
      const mockFile = new File(['test'], 'test.xlsx')
      
      mockStore.importDictionary.mockRejectedValue(new Error('网络错误'))

      // 模拟文件选择和导入
      await wrapper.vm.handleFileChange({ raw: mockFile })
      await wrapper.vm.handleImport()

      // 验证异常处理
      expect(mockStore.importDictionary).toHaveBeenCalledWith(mockFile)
      expect(ElMessage.error).toHaveBeenCalledWith('导入失败: 网络错误')
    })

    it('应该在没有字典ID时显示警告', async () => {
      // 重新挂载组件，不传递dictionaryId
      wrapper.unmount()
      wrapper = mount(DictionaryImportExport, {
        props: {}
      })

      // 尝试打开导入对话框
      await wrapper.vm.openImportDialog()

      // 验证显示警告
      expect(ElMessage.warning).toHaveBeenCalledWith('请先选择一个字典。')
    })
  })

  describe('导出功能真实API集成', () => {
    beforeEach(() => {
      wrapper = mount(DictionaryImportExport, {
        props: {
          dictionaryId: 123
        }
      })
    })

    it('应该调用真实的store导出API - Excel格式', async () => {
      const mockBlob = new Blob(['test data'])
      mockStore.exportDictionary.mockResolvedValue(mockBlob)

      // Mock DOM methods
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn()
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any)
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any)
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      // 设置导出格式为Excel
      wrapper.vm.exportFormat = 'excel'
      
      // 执行导出
      await wrapper.vm.handleExport()

      // 验证调用了真实的store方法
      expect(mockStore.exportDictionary).toHaveBeenCalledWith(123)
      expect(ElMessage.success).toHaveBeenCalledWith('导出成功！')
    })

    it('应该调用真实的store导出API - CSV格式', async () => {
      const mockBlob = new Blob(['test data'])
      mockStore.exportDictionary.mockResolvedValue(mockBlob)

      // Mock DOM methods
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn()
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any)
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any)
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      // 设置导出格式为CSV
      wrapper.vm.exportFormat = 'csv'
      
      // 执行导出
      await wrapper.vm.handleExport()

      // 验证调用了真实的store方法
      expect(mockStore.exportDictionary).toHaveBeenCalledWith(123)
      expect(ElMessage.success).toHaveBeenCalledWith('导出成功！')
    })

    it('应该正确处理导出API错误', async () => {
      mockStore.exportDictionary.mockResolvedValue(null)

      await wrapper.vm.handleExport()

      // 验证错误处理
      expect(mockStore.exportDictionary).toHaveBeenCalledWith(123)
      expect(ElMessage.error).toHaveBeenCalledWith('导出失败')
    })

    it('应该正确处理导出异常', async () => {
      mockStore.exportDictionary.mockRejectedValue(new Error('服务器错误'))

      await wrapper.vm.handleExport()

      // 验证异常处理
      expect(mockStore.exportDictionary).toHaveBeenCalledWith(123)
      expect(ElMessage.error).toHaveBeenCalledWith('导出失败: 服务器错误')
    })

    it('应该在没有字典ID时显示警告', async () => {
      // 重新挂载组件，不传递dictionaryId
      wrapper.unmount()
      wrapper = mount(DictionaryImportExport, {
        props: {}
      })

      // 尝试打开导出对话框
      await wrapper.vm.openExportDialog()

      // 验证显示警告
      expect(ElMessage.warning).toHaveBeenCalledWith('请先选择一个字典。')
    })
  })

  describe('用户交互流程', () => {
    beforeEach(() => {
      wrapper = mount(DictionaryImportExport, {
        props: {
          dictionaryId: 123
        }
      })
    })

    it('应该正确管理导入对话框状态', async () => {
      // 初始状态
      expect(wrapper.vm.importDialogVisible).toBe(false)

      // 打开导入对话框
      await wrapper.vm.openImportDialog()
      expect(wrapper.vm.importDialogVisible).toBe(true)

      // 关闭导入对话框
      await wrapper.vm.handleCloseImport()
      expect(wrapper.vm.importDialogVisible).toBe(false)
    })

    it('应该正确管理导出对话框状态', async () => {
      // 初始状态
      expect(wrapper.vm.exportDialogVisible).toBe(false)

      // 打开导出对话框
      await wrapper.vm.openExportDialog()
      expect(wrapper.vm.exportDialogVisible).toBe(true)

      // 关闭导出对话框
      wrapper.vm.exportDialogVisible = false
      expect(wrapper.vm.exportDialogVisible).toBe(false)
    })

    it('应该正确重置导入状态', async () => {
      // 设置一些状态
      wrapper.vm.importResult.completed = true
      wrapper.vm.importResult.total = 10
      wrapper.vm.selectedFile = new File(['test'], 'test.xlsx')

      // 重置状态
      await wrapper.vm.resetImportState()

      // 验证状态被重置
      expect(wrapper.vm.importResult.completed).toBe(false)
      expect(wrapper.vm.importResult.total).toBe(0)
      expect(wrapper.vm.selectedFile).toBe(null)
    })

    it('应该正确处理文件选择', async () => {
      const mockFile = new File(['test'], 'test.xlsx')
      
      // 模拟文件选择
      await wrapper.vm.handleFileChange({ raw: mockFile })

      // 验证文件被正确设置
      expect(wrapper.vm.selectedFile).toBe(mockFile)
    })

    it('应该正确处理文件数量超限', async () => {
      // 模拟文件数量超限
      await wrapper.vm.handleFileExceed()

      // 验证显示警告
      expect(ElMessage.warning).toHaveBeenCalledWith('一次只能上传一个文件。')
    })
  })

  describe('数据持久化验证', () => {
    beforeEach(() => {
      wrapper = mount(DictionaryImportExport, {
        props: {
          dictionaryId: 123
        }
      })
    })

    it('应该在导入成功后更新导入结果状态', async () => {
      const mockFile = new File(['test'], 'test.xlsx')
      
      mockStore.importDictionary.mockResolvedValue(true)

      // 选择文件并导入
      await wrapper.vm.handleFileChange({ raw: mockFile })
      await wrapper.vm.handleImport()

      // 验证导入结果状态
      expect(wrapper.vm.importResult.completed).toBe(true)
      expect(wrapper.vm.importResult.success).toBe(1)
      expect(wrapper.vm.importResult.failed).toBe(0)
    })

    it('应该在导入失败后更新导入结果状态', async () => {
      const mockFile = new File(['test'], 'test.xlsx')
      
      mockStore.importDictionary.mockResolvedValue(false)

      // 选择文件并导入
      await wrapper.vm.handleFileChange({ raw: mockFile })
      await wrapper.vm.handleImport()

      // 验证导入结果状态
      expect(wrapper.vm.importResult.completed).toBe(true)
      expect(wrapper.vm.importResult.success).toBe(0)
      expect(wrapper.vm.importResult.failed).toBe(1)
      expect(wrapper.vm.importResult.errors).toContain('导入失败')
    })

    it('应该在导出成功后关闭导出对话框', async () => {
      const mockBlob = new Blob(['test data'])
      mockStore.exportDictionary.mockResolvedValue(mockBlob)

      // Mock DOM methods
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn()
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any)
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any)
      vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:url')
      vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {})

      // 打开导出对话框
      wrapper.vm.exportDialogVisible = true
      
      // 执行导出
      await wrapper.vm.handleExport()

      // 验证对话框被关闭
      expect(wrapper.vm.exportDialogVisible).toBe(false)
    })
  })
})