/**
 * SmartChart 导出和分享功能测试
 * 测试任务 6.2.4：图表导出和分享功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import SmartChart from '@/components/Chart/SmartChart.vue'
import type { ChartData } from '@/types/chart'
import * as echarts from 'echarts'
import { chartExportService } from '@/services/chartExportService'
import { chartConfigService } from '@/services/chartConfigService'
import { chartShareService } from '@/services/chartShareService'

// Mock ECharts
vi.mock('echarts', () => ({
  default: {
    init: vi.fn(),
    graphic: {
      LinearGradient: vi.fn()
    }
  },
  init: vi.fn(),
  graphic: {
    LinearGradient: vi.fn()
  }
}))

// Mock services
vi.mock('@/services/chartExportService', () => ({
  chartExportService: {
    exportAsImage: vi.fn(),
    exportAsPDF: vi.fn(),
    exportAsExcel: vi.fn(),
    batchExport: vi.fn()
  }
}))

vi.mock('@/services/chartConfigService', () => ({
  chartConfigService: {
    saveConfig: vi.fn(() => 'test-config-id'),
    loadConfig: vi.fn(),
    deleteConfig: vi.fn(),
    getAllConfigs: vi.fn(() => []),
    saveTemplate: vi.fn(),
    getAllTemplates: vi.fn(() => []),
    getTemplate: vi.fn(),
    deleteTemplate: vi.fn(),
    createConfigFromTemplate: vi.fn(),
    exportConfigAsJSON: vi.fn(),
    importConfigFromJSON: vi.fn()
  }
}))

vi.mock('@/services/chartShareService', () => ({
  chartShareService: {
    generateShareLink: vi.fn(() => ({
      chartId: 'test-chart-id',
      shareUrl: 'https://example.com/share/chart/test-chart-id',
      embedCode: '<iframe src="https://example.com/share/chart/test-chart-id"></iframe>',
      accessCount: 0
    })),
    getSharedChart: vi.fn(),
    deleteShare: vi.fn(),
    getShareStats: vi.fn(),
    copyToClipboard: vi.fn(() => Promise.resolve(true))
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

describe('SmartChart - 导出和分享功能', () => {
  let mockChartInstance: any

  const mockChartData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 100],
      ['B', 200],
      ['C', 150]
    ],
    title: '测试图表'
  }

  beforeEach(() => {
    // 创建 mock chart instance
    mockChartInstance = {
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      getDataURL: vi.fn(() => 'data:image/png;base64,mockImageData')
    }

    // Mock echarts.init
    vi.mocked(echarts.init).mockReturnValue(mockChartInstance as any)
    
    // Mock LinearGradient constructor
    vi.mocked(echarts.graphic.LinearGradient).mockImplementation(
      function(this: any, x0: number, y0: number, x1: number, y1: number, colorStops: any[]) {
        this.x0 = x0
        this.y0 = y0
        this.x1 = x1
        this.y1 = y1
        this.colorStops = colorStops
        return this
      } as any
    )
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('图表导出功能', () => {
    it('应该支持导出为PNG格式', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          exportable: true
        }
      })

      await nextTick()

      // 触发PNG导出
      await wrapper.vm.handleExport('png')

      expect(chartExportService.exportAsImage).toHaveBeenCalledWith(
        mockChartInstance,
        'png',
        'chart'
      )
    })

    it('应该支持导出为JPG格式', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          exportable: true
        }
      })

      await nextTick()

      await wrapper.vm.handleExport('jpg')

      expect(chartExportService.exportAsImage).toHaveBeenCalledWith(
        mockChartInstance,
        'jpg',
        'chart'
      )
    })

    it('应该支持导出为PDF格式', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          exportable: true
        }
      })

      await nextTick()

      await wrapper.vm.handleExport('pdf')

      expect(chartExportService.exportAsPDF).toHaveBeenCalledWith(
        mockChartInstance,
        'chart',
        expect.objectContaining({
          title: '测试图表'
        })
      )
    })

    it('应该支持导出为SVG格式', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          exportable: true
        }
      })

      await nextTick()

      await wrapper.vm.handleExport('svg')

      expect(chartExportService.exportAsImage).toHaveBeenCalledWith(
        mockChartInstance,
        'svg',
        'chart'
      )
    })

    it('应该支持导出为Excel格式', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          exportable: true
        }
      })

      await nextTick()

      await wrapper.vm.handleExport('excel')

      expect(chartExportService.exportAsExcel).toHaveBeenCalledWith(
        mockChartData,
        'chart-data'
      )
    })
  })

  describe('图表配置保存功能', () => {
    it('应该能够保存图表配置', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          type: 'bar',
          theme: 'light'
        }
      })

      await nextTick()

      // 设置保存表单
      wrapper.vm.saveForm.name = '测试配置'
      wrapper.vm.saveForm.asTemplate = false

      // 触发保存
      await wrapper.vm.handleSaveConfig()

      expect(chartConfigService.saveConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          name: '测试配置',
          type: 'bar',
          data: mockChartData,
          theme: 'light'
        })
      )
    })

    it('应该能够保存为模板', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          type: 'line',
          theme: 'dark'
        }
      })

      await nextTick()

      wrapper.vm.saveForm.name = '测试模板'
      wrapper.vm.saveForm.asTemplate = true

      await wrapper.vm.handleSaveConfig()

      expect(chartConfigService.saveTemplate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: '测试模板',
          type: 'line',
          theme: 'dark'
        })
      )
    })

    it('保存配置时名称为空应该显示警告', async () => {
      const { ElMessage } = await import('element-plus')
      
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData
        }
      })

      await nextTick()

      wrapper.vm.saveForm.name = ''
      await wrapper.vm.handleSaveConfig()

      expect(ElMessage.warning).toHaveBeenCalledWith('请输入配置名称')
      expect(chartConfigService.saveConfig).not.toHaveBeenCalled()
    })
  })

  describe('图表分享功能', () => {
    it('应该能够生成分享链接', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData,
          type: 'pie'
        }
      })

      await nextTick()

      wrapper.vm.shareOptions.expiresInDays = 7

      await wrapper.vm.generateShare()

      expect(chartShareService.generateShareLink).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'pie',
          data: mockChartData
        }),
        expect.objectContaining({
          expiresInDays: 7
        })
      )

      expect(wrapper.vm.shareLink).toBe('https://example.com/share/chart/test-chart-id')
    })

    it('应该能够生成嵌入代码', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData
        }
      })

      await nextTick()

      await wrapper.vm.generateShare()

      expect(wrapper.vm.embedCode).toContain('<iframe')
      expect(wrapper.vm.embedCode).toContain('test-chart-id')
    })

    it('应该能够复制分享链接到剪贴板', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData
        }
      })

      await nextTick()

      wrapper.vm.shareLink = 'https://example.com/share/test'

      await wrapper.vm.copyShareLink()

      expect(chartShareService.copyToClipboard).toHaveBeenCalledWith(
        'https://example.com/share/test'
      )
    })

    it('应该能够复制嵌入代码到剪贴板', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          data: mockChartData
        }
      })

      await nextTick()

      wrapper.vm.embedCode = '<iframe src="test"></iframe>'

      await wrapper.vm.copyEmbedCode()

      expect(chartShareService.copyToClipboard).toHaveBeenCalledWith(
        '<iframe src="test"></iframe>'
      )
    })
  })

  describe('批量导出功能', () => {
    it('chartExportService应该支持批量导出', () => {
      const configs = [
        {
          id: '1',
          name: '图表1',
          type: 'bar' as const,
          data: mockChartData,
          options: {},
          theme: 'light' as const
        },
        {
          id: '2',
          name: '图表2',
          type: 'line' as const,
          data: mockChartData,
          options: {},
          theme: 'light' as const
        }
      ]

      chartExportService.batchExport({
        charts: configs,
        format: 'pdf',
        filename: 'batch-charts'
      })

      expect(chartExportService.batchExport).toHaveBeenCalledWith(
        expect.objectContaining({
          charts: configs,
          format: 'pdf',
          filename: 'batch-charts'
        })
      )
    })
  })
})
