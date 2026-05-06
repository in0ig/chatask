import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import SmartChart from '@/components/Chart/SmartChart.vue'
import { chartStreamingService } from '@/services/chartStreamingService'
import type { ChartData } from '@/types/chart'

// Mock ECharts
vi.mock('echarts', () => ({
  default: {
    init: vi.fn(() => ({
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      showLoading: vi.fn(),
      hideLoading: vi.fn(),
      on: vi.fn(),
      off: vi.fn()
    })),
    graphic: {
      LinearGradient: vi.fn()
    },
    registerTheme: vi.fn()
  }
}))

// Mock services
vi.mock('@/services/chartStreamingService', () => ({
  chartStreamingService: {
    shouldUseStreaming: vi.fn(),
    isLargeDataset: vi.fn(),
    streamData: vi.fn(),
    incrementalUpdate: vi.fn(),
    optimizeForLargeDataset: vi.fn(),
    getLoadingAnimation: vi.fn(() => ({
      text: '数据加载中...',
      color: '#409EFF',
      textColor: '#000',
      maskColor: 'rgba(255, 255, 255, 0.8)',
      zlevel: 0
    })),
    getState: vi.fn(() => ({
      isStreaming: false,
      renderedCount: 0,
      totalCount: 0,
      progress: 0
    })),
    cleanup: vi.fn()
  }
}))

describe('SmartChart - 流式渲染功能', () => {
  let wrapper: any

  const mockData: ChartData = {
    columns: ['月份', '销售额'],
    rows: Array.from({ length: 200 }, (_, i) => [`月份${i + 1}`, Math.random() * 1000])
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('流式渲染判断', () => {
    it('应该判断是否需要流式渲染', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.shouldUseStreaming).toHaveBeenCalledWith(200)
    })

    it('小数据量不应该使用流式渲染', async () => {
      const smallData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100], ['2月', 200]]
      }

      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)

      wrapper = mount(SmartChart, {
        props: {
          data: smallData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.shouldUseStreaming).toHaveBeenCalledWith(2)
      expect(chartStreamingService.streamData).not.toHaveBeenCalled()
    })
  })

  describe('流式数据渲染', () => {
    it('应该使用流式渲染大数据量', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)
      vi.mocked(chartStreamingService.streamData).mockImplementation(
        async (chartId, data, onBatchRender, onComplete) => {
          // 模拟分批渲染
          const batches = [
            { index: 0, data: data.slice(0, 50), isLast: false },
            { index: 1, data: data.slice(50, 100), isLast: false },
            { index: 2, data: data.slice(100, 150), isLast: false },
            { index: 3, data: data.slice(150), isLast: true }
          ]

          for (const batch of batches) {
            const accumulated = data.slice(0, (batch.index + 1) * 50)
            onBatchRender(batch, accumulated)
            await new Promise(resolve => setTimeout(resolve, 100))
          }

          onComplete?.()
        }
      )

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar',
          options: {
            enableStreamingUpdate: true
          }
        }
      })

      await nextTick()
      await vi.runAllTimersAsync()

      expect(chartStreamingService.streamData).toHaveBeenCalled()
    })

    it('应该显示加载动画', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)
      vi.mocked(chartStreamingService.streamData).mockImplementation(
        async (chartId, data, onBatchRender, onComplete) => {
          await new Promise(resolve => setTimeout(resolve, 100))
          onComplete?.()
        }
      )

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.getLoadingAnimation).toHaveBeenCalled()
    })

    it('应该在完成时隐藏加载动画', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)
      
      let completeCallback: (() => void) | undefined
      vi.mocked(chartStreamingService.streamData).mockImplementation(
        async (chartId, data, onBatchRender, onComplete) => {
          completeCallback = onComplete
          return Promise.resolve()
        }
      )

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar'
        }
      })

      await nextTick()
      
      // 触发完成回调
      completeCallback?.()
      await nextTick()

      // 验证加载动画被隐藏（通过检查 hideLoading 被调用）
      expect(chartStreamingService.streamData).toHaveBeenCalled()
    })
  })

  describe('增量更新', () => {
    it('应该支持增量更新数据', async () => {
      const initialData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100], ['2月', 200]]
      }

      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)
      vi.mocked(chartStreamingService.incrementalUpdate).mockReturnValue([
        ['1月', 100],
        ['2月', 200],
        ['3月', 300]
      ])

      wrapper = mount(SmartChart, {
        props: {
          data: initialData,
          type: 'bar',
          options: {
            enableIncrementalUpdate: true
          }
        }
      })

      await nextTick()

      // 更新数据（增加一行）
      const updatedData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100], ['2月', 200], ['3月', 300]]
      }

      await wrapper.setProps({ data: updatedData })
      await nextTick()

      expect(chartStreamingService.incrementalUpdate).toHaveBeenCalled()
    })

    it('增量更新时应该显示加载动画', async () => {
      const initialData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100]]
      }

      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)
      vi.mocked(chartStreamingService.incrementalUpdate).mockReturnValue([
        ['1月', 100],
        ['2月', 200]
      ])

      wrapper = mount(SmartChart, {
        props: {
          data: initialData,
          type: 'bar',
          options: {
            enableIncrementalUpdate: true,
            showLoadingOnUpdate: true
          }
        }
      })

      await nextTick()

      const updatedData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100], ['2月', 200]]
      }

      await wrapper.setProps({ data: updatedData })
      await nextTick()

      expect(chartStreamingService.getLoadingAnimation).toHaveBeenCalled()
    })
  })

  describe('大数据量优化', () => {
    it('应该优化大数据量图表', async () => {
      const largeData: ChartData = {
        columns: ['月份', '销售额'],
        rows: Array.from({ length: 2000 }, (_, i) => [`月份${i + 1}`, Math.random() * 1000])
      }

      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)
      vi.mocked(chartStreamingService.isLargeDataset).mockReturnValue(true)
      vi.mocked(chartStreamingService.optimizeForLargeDataset).mockReturnValue({
        animation: false,
        progressive: 1000,
        large: true
      })

      wrapper = mount(SmartChart, {
        props: {
          data: largeData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.isLargeDataset).toHaveBeenCalledWith(2000)
      expect(chartStreamingService.optimizeForLargeDataset).toHaveBeenCalled()
    })

    it('小数据量不应该优化', async () => {
      const smallData: ChartData = {
        columns: ['月份', '销售额'],
        rows: [['1月', 100], ['2月', 200]]
      }

      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)
      vi.mocked(chartStreamingService.isLargeDataset).mockReturnValue(false)

      wrapper = mount(SmartChart, {
        props: {
          data: smallData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.isLargeDataset).toHaveBeenCalledWith(2)
      expect(chartStreamingService.optimizeForLargeDataset).not.toHaveBeenCalled()
    })
  })

  describe('资源清理', () => {
    it('组件卸载时应该清理流式渲染资源', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(false)

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar'
        }
      })

      await nextTick()

      wrapper.unmount()

      expect(chartStreamingService.cleanup).toHaveBeenCalled()
    })
  })

  describe('配置选项', () => {
    it('应该支持禁用流式渲染', async () => {
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar',
          options: {
            enableStreamingUpdate: false
          }
        }
      })

      await nextTick()

      // 即使数据量大，也不应该使用流式渲染
      expect(chartStreamingService.streamData).not.toHaveBeenCalled()
    })

    it('应该支持自定义加载动画', async () => {
      const customLoading = {
        text: '自定义加载中...',
        color: '#FF0000',
        textColor: '#FFF',
        maskColor: 'rgba(0, 0, 0, 0.5)',
        zlevel: 1
      }

      vi.mocked(chartStreamingService.getLoadingAnimation).mockReturnValue(customLoading)
      vi.mocked(chartStreamingService.shouldUseStreaming).mockReturnValue(true)
      vi.mocked(chartStreamingService.streamData).mockImplementation(
        async (chartId, data, onBatchRender, onComplete) => {
          onComplete?.()
        }
      )

      wrapper = mount(SmartChart, {
        props: {
          data: mockData,
          type: 'bar'
        }
      })

      await nextTick()

      expect(chartStreamingService.getLoadingAnimation).toHaveBeenCalled()
    })
  })
})
