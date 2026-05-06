import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ChartStreamingService } from '@/services/chartStreamingService'

describe('ChartStreamingService', () => {
  let service: ChartStreamingService

  beforeEach(() => {
    service = new ChartStreamingService()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  describe('配置管理', () => {
    it('应该返回默认配置', () => {
      const config = service.getConfig()
      
      expect(config.enabled).toBe(true)
      expect(config.batchSize).toBe(50)
      expect(config.batchInterval).toBe(100)
      expect(config.showLoadingAnimation).toBe(true)
      expect(config.enableIncrementalUpdate).toBe(true)
      expect(config.largeDataThreshold).toBe(1000)
    })

    it('应该能够更新配置', () => {
      service.updateConfig({
        batchSize: 100,
        batchInterval: 200
      })

      const config = service.getConfig()
      expect(config.batchSize).toBe(100)
      expect(config.batchInterval).toBe(200)
      expect(config.enabled).toBe(true) // 其他配置保持不变
    })
  })

  describe('状态管理', () => {
    it('应该返回初始状态', () => {
      const state = service.getState()
      
      expect(state.isStreaming).toBe(false)
      expect(state.renderedCount).toBe(0)
      expect(state.totalCount).toBe(0)
      expect(state.progress).toBe(0)
    })
  })

  describe('流式渲染判断', () => {
    it('应该判断是否需要流式渲染', () => {
      expect(service.shouldUseStreaming(30)).toBe(false) // 小于batchSize
      expect(service.shouldUseStreaming(100)).toBe(true) // 大于batchSize
    })

    it('应该判断是否为大数据量', () => {
      expect(service.isLargeDataset(500)).toBe(false)
      expect(service.isLargeDataset(1500)).toBe(true)
    })

    it('禁用流式渲染时应该返回false', () => {
      service.updateConfig({ enabled: false })
      expect(service.shouldUseStreaming(100)).toBe(false)
    })
  })

  describe('流式数据渲染', () => {
    it('应该分批渲染数据', async () => {
      const data = Array.from({ length: 150 }, (_, i) => ({ value: i }))
      const batches: any[] = []
      const accumulated: any[][] = []

      const promise = service.streamData(
        'test-chart',
        data,
        (batch, accData) => {
          batches.push(batch)
          accumulated.push([...accData])
        }
      )

      // 执行所有定时器
      await vi.runAllTimersAsync()
      await promise

      // 验证批次数量（150 / 50 = 3批）
      expect(batches.length).toBe(3)
      
      // 验证第一批
      expect(batches[0].index).toBe(0)
      expect(batches[0].data.length).toBe(50)
      expect(batches[0].isLast).toBe(false)
      
      // 验证最后一批
      expect(batches[2].index).toBe(2)
      expect(batches[2].data.length).toBe(50)
      expect(batches[2].isLast).toBe(true)
      
      // 验证累积数据
      expect(accumulated[0].length).toBe(50)
      expect(accumulated[1].length).toBe(100)
      expect(accumulated[2].length).toBe(150)
    })

    it('应该更新渲染状态', async () => {
      const data = Array.from({ length: 100 }, (_, i) => ({ value: i }))

      const promise = service.streamData(
        'test-chart',
        data,
        () => {}
      )

      // 初始状态
      let state = service.getState()
      expect(state.isStreaming).toBe(true)
      expect(state.totalCount).toBe(100)

      // 执行所有定时器
      await vi.runAllTimersAsync()
      await promise

      // 完成状态
      state = service.getState()
      expect(state.isStreaming).toBe(false)
      expect(state.renderedCount).toBe(100)
      expect(state.progress).toBe(100)
    })

    it('应该在完成时调用回调', async () => {
      const data = Array.from({ length: 50 }, (_, i) => ({ value: i }))
      const onComplete = vi.fn()

      const promise = service.streamData(
        'test-chart',
        data,
        () => {},
        onComplete
      )

      await vi.runAllTimersAsync()
      await promise

      expect(onComplete).toHaveBeenCalledTimes(1)
    })

    it('应该能够停止流式渲染', async () => {
      const data = Array.from({ length: 150 }, (_, i) => ({ value: i }))
      const batches: any[] = []

      service.streamData(
        'test-chart',
        data,
        (batch) => {
          batches.push(batch)
        }
      )

      // 渲染第一批后停止
      await vi.advanceTimersByTimeAsync(100)
      
      // 记录当前批次数
      const batchesBeforeStop = batches.length
      
      service.stopStreaming('test-chart')

      // 执行剩余定时器
      await vi.runAllTimersAsync()

      // 应该没有新的批次被渲染
      expect(batches.length).toBe(batchesBeforeStop)
      expect(service.getState().isStreaming).toBe(false)
    })
  })

  describe('增量更新', () => {
    it('应该合并新数据和现有数据', () => {
      const existing = [{ value: 1 }, { value: 2 }]
      const newData = [{ value: 3 }, { value: 4 }]

      const merged = service.incrementalUpdate('test-chart', newData, existing)

      expect(merged.length).toBe(4)
      expect(merged[0].value).toBe(1)
      expect(merged[3].value).toBe(4)
    })

    it('禁用增量更新时应该返回新数据', () => {
      service.updateConfig({ enableIncrementalUpdate: false })

      const existing = [{ value: 1 }, { value: 2 }]
      const newData = [{ value: 3 }, { value: 4 }]

      const result = service.incrementalUpdate('test-chart', newData, existing)

      expect(result).toEqual(newData)
      expect(result.length).toBe(2)
    })
  })

  describe('大数据量优化', () => {
    it('应该优化大数据量图表配置', () => {
      const option = {
        series: [
          {
            type: 'line',
            data: [],
            label: { show: true },
            lineStyle: { width: 2 },
            symbol: 'circle'
          }
        ]
      }

      const optimized = service.optimizeForLargeDataset(option, 2000)

      expect(optimized.animation).toBe(false)
      expect(optimized.progressive).toBe(1000)
      expect(optimized.large).toBe(true)
      
      const series = optimized.series as any[]
      expect(series[0].large).toBe(true)
      expect(series[0].label.show).toBe(false)
      expect(series[0].lineStyle.width).toBe(1)
      expect(series[0].symbol).toBe('none')
    })

    it('小数据量时不应该优化', () => {
      const option = {
        series: [{ type: 'line', data: [] }]
      }

      const optimized = service.optimizeForLargeDataset(option, 500)

      expect(optimized).toEqual(option)
    })
  })

  describe('数据采样', () => {
    it('应该对大数据量进行采样', () => {
      const data = Array.from({ length: 1000 }, (_, i) => ({ value: i }))
      const sampled = service.sampleData(data, 100)

      expect(sampled.length).toBe(100)
      expect(sampled[0].value).toBe(0)
      expect(sampled[99].value).toBeGreaterThan(900)
    })

    it('数据量小于目标时不应该采样', () => {
      const data = Array.from({ length: 50 }, (_, i) => ({ value: i }))
      const sampled = service.sampleData(data, 100)

      expect(sampled).toEqual(data)
      expect(sampled.length).toBe(50)
    })
  })

  describe('加载动画', () => {
    it('应该返回加载动画配置', () => {
      const animation = service.getLoadingAnimation()

      expect(animation.text).toBe('数据加载中...')
      expect(animation.color).toBe('#409EFF')
      expect(animation.textColor).toBe('#000')
      expect(animation.maskColor).toBe('rgba(255, 255, 255, 0.8)')
      expect(animation.zlevel).toBe(0)
    })
  })

  describe('资源清理', () => {
    it('应该清理指定图表的资源', async () => {
      const data = Array.from({ length: 100 }, (_, i) => ({ value: i }))

      // 启动第一个图表的流式渲染
      const promise1 = service.streamData('chart-1', data, () => {})
      
      await vi.advanceTimersByTimeAsync(100)

      // 清理 chart-1
      service.cleanup('chart-1')

      // 执行剩余定时器
      await vi.runAllTimersAsync()

      // 验证 chart-1 的渲染被停止
      // 由于只有一个图表在渲染，清理后状态应该是 false
      expect(service.getState().isStreaming).toBe(false)
    })

    it('应该清理所有资源', async () => {
      const data = Array.from({ length: 100 }, (_, i) => ({ value: i }))

      service.streamData('chart-1', data, () => {})
      service.streamData('chart-2', data, () => {})

      await vi.advanceTimersByTimeAsync(100)

      service.cleanup()

      const state = service.getState()
      expect(state.isStreaming).toBe(false)
      expect(state.renderedCount).toBe(0)
      expect(state.totalCount).toBe(0)
      expect(state.progress).toBe(0)
    })
  })
})
