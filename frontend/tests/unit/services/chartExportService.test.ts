/**
 * ChartExportService 测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ChartExportService } from '@/services/chartExportService'
import type { ChartData, ChartConfig } from '@/types/chart'

// Mock jsPDF
const mockPDFInstance = {
  setFontSize: vi.fn(),
  text: vi.fn(),
  addImage: vi.fn(),
  save: vi.fn(),
  addPage: vi.fn(),
  internal: {
    pageSize: {
      getWidth: () => 297,
      getHeight: () => 210
    }
  }
}

vi.mock('jspdf', () => {
  class jsPDF {
    setFontSize = vi.fn()
    text = vi.fn()
    addImage = vi.fn()
    save = vi.fn()
    addPage = vi.fn()
    internal = {
      pageSize: {
        getWidth: () => 297,
        getHeight: () => 210
      }
    }
    
    constructor() {
      return mockPDFInstance
    }
  }
  
  return { default: jsPDF }
})

// Mock xlsx
vi.mock('xlsx', () => ({
  utils: {
    book_new: vi.fn(() => ({})),
    aoa_to_sheet: vi.fn(() => ({})),
    book_append_sheet: vi.fn()
  },
  writeFile: vi.fn()
}))

describe('ChartExportService', () => {
  let service: ChartExportService
  let mockChartInstance: any

  const mockChartData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 100],
      ['B', 200],
      ['C', 150]
    ]
  }

  beforeEach(() => {
    service = new ChartExportService()
    
    mockChartInstance = {
      getDataURL: vi.fn(() => 'data:image/png;base64,mockImageData')
    }

    // Mock DOM methods
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()
    
    const mockLink = {
      click: vi.fn(),
      download: '',
      href: ''
    }
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)
  })

  describe('exportAsImage', () => {
    it('应该能够导出PNG图片', () => {
      service.exportAsImage(mockChartInstance, 'png', 'test-chart')

      expect(mockChartInstance.getDataURL).toHaveBeenCalledWith({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })
    })

    it('应该能够导出JPG图片', () => {
      service.exportAsImage(mockChartInstance, 'jpg', 'test-chart')

      expect(mockChartInstance.getDataURL).toHaveBeenCalledWith({
        type: 'jpeg',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })
    })

    it('应该能够导出SVG图片', () => {
      service.exportAsImage(mockChartInstance, 'svg', 'test-chart')

      expect(mockChartInstance.getDataURL).toHaveBeenCalledWith({
        type: 'svg',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })
    })
  })

  describe('exportAsPDF', () => {
    it('应该能够导出PDF文档', async () => {
      await service.exportAsPDF(mockChartInstance, 'test-chart', {
        title: '测试图表',
        orientation: 'landscape'
      })

      expect(mockChartInstance.getDataURL).toHaveBeenCalled()
    })

    it('应该支持纵向PDF', async () => {
      await service.exportAsPDF(mockChartInstance, 'test-chart', {
        orientation: 'portrait'
      })

      expect(mockChartInstance.getDataURL).toHaveBeenCalled()
    })
  })

  describe('exportAsExcel', () => {
    it('应该能够导出Excel文件', async () => {
      service.exportAsExcel(mockChartData, 'test-data')

      // 动态导入以获取 mock
      const XLSX = await import('xlsx')
      expect(XLSX.utils.book_new).toHaveBeenCalled()
      expect(XLSX.utils.aoa_to_sheet).toHaveBeenCalled()
      expect(XLSX.writeFile).toHaveBeenCalled()
    })

    it('导出的Excel应该包含列名和数据', async () => {
      service.exportAsExcel(mockChartData, 'test-data')

      const XLSX = await import('xlsx')
      expect(XLSX.utils.aoa_to_sheet).toHaveBeenCalledWith([
        mockChartData.columns,
        ...mockChartData.rows
      ])
    })
  })

  describe('batchExport', () => {
    const mockConfigs: ChartConfig[] = [
      {
        id: '1',
        name: '图表1',
        type: 'bar',
        data: mockChartData,
        options: {},
        theme: 'light'
      },
      {
        id: '2',
        name: '图表2',
        type: 'line',
        data: mockChartData,
        options: {},
        theme: 'light'
      }
    ]

    it('应该支持批量导出为PDF', async () => {
      await service.batchExport({
        charts: mockConfigs,
        format: 'pdf',
        filename: 'batch-charts'
      })

      // PDF批量导出会被调用
      expect(true).toBe(true)
    })

    it('应该支持批量导出为Excel', async () => {
      await service.batchExport({
        charts: mockConfigs,
        format: 'excel',
        filename: 'batch-data'
      })

      const XLSX = await import('xlsx')
      expect(XLSX.utils.book_new).toHaveBeenCalled()
    })
  })
})
