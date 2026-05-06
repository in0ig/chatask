import { describe, it, expect, vi, beforeEach } from 'vitest'
import { chartAnimationService } from '@/services/chartAnimationService'
import type { EChartsOption } from 'echarts'

describe('ChartAnimationService', () => {
  describe('动画预设', () => {
    it('应该返回smooth动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('smooth')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(1000)
      expect(config.easing).toBe('cubicOut')
    })

    it('应该返回bounce动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('bounce')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(1200)
      expect(config.easing).toBe('bounceOut')
    })

    it('应该返回elastic动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('elastic')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(1500)
      expect(config.easing).toBe('elasticOut')
    })

    it('应该返回fade动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('fade')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(800)
      expect(config.easing).toBe('linear')
    })

    it('应该返回zoom动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('zoom')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(1000)
      expect(config.easing).toBe('cubicInOut')
    })

    it('应该返回slide动画配置', () => {
      const config = chartAnimationService.getAnimationConfig('slide')
      
      expect(config.enabled).toBe(true)
      expect(config.duration).toBe(1000)
      expect(config.easing).toBe('quadraticOut')
    })
  })

  describe('应用动画配置', () => {
    it('应该将动画配置应用到图表选项', () => {
      const baseOption: EChartsOption = {
        title: { text: 'Test Chart' },
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const animConfig = {
        enabled: true,
        duration: 1500,
        easing: 'elasticOut',
        delay: 100,
        delayUpdate: 200
      }

      const result = chartAnimationService.applyAnimation(baseOption, animConfig)

      expect(result.animation).toBe(true)
      expect(result.animationDuration).toBe(1500)
      expect(result.animationEasing).toBe('elasticOut')
      expect(result.animationDelay).toBe(100)
      expect(result.animationDelayUpdate).toBe(200)
    })

    it('应该保留原有的图表配置', () => {
      const baseOption: EChartsOption = {
        title: { text: 'Test Chart' },
        xAxis: { type: 'category' },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const animConfig = {
        enabled: true,
        duration: 1000,
        easing: 'cubicOut'
      }

      const result = chartAnimationService.applyAnimation(baseOption, animConfig)

      expect(result.title).toEqual({ text: 'Test Chart' })
      expect(result.xAxis).toEqual({ type: 'category' })
      expect(result.yAxis).toEqual({ type: 'value' })
      expect(result.series).toEqual([{ type: 'bar', data: [1, 2, 3] }])
    })
  })

  describe('渐进式加载动画', () => {
    it('应该创建渐进式加载动画配置', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3, 4, 5] }]
      }

      const result = chartAnimationService.createProgressiveAnimation(baseOption, 5)

      expect(result.animation).toBe(true)
      expect(result.animationDuration).toBe(1000)
      expect(result.animationEasing).toBe('cubicOut')
      expect(typeof result.animationDelay).toBe('function')
    })

    it('渐进式动画延迟应该随索引递增', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const result = chartAnimationService.createProgressiveAnimation(baseOption, 3)
      const delayFunc = result.animationDelay as (idx: number) => number

      expect(delayFunc(0)).toBe(0)
      expect(delayFunc(1)).toBe(50)
      expect(delayFunc(2)).toBe(100)
    })
  })

  describe('波浪式加载动画', () => {
    it('应该创建波浪式加载动画配置', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const result = chartAnimationService.createWaveAnimation(baseOption)

      expect(result.animation).toBe(true)
      expect(result.animationDuration).toBe(1000)
      expect(result.animationEasing).toBe('elasticOut')
      expect(typeof result.animationDelay).toBe('function')
    })

    it('波浪式动画延迟应该基于正弦函数', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const result = chartAnimationService.createWaveAnimation(baseOption)
      const delayFunc = result.animationDelay as (idx: number) => number

      const delay0 = delayFunc(0)
      const delay1 = delayFunc(1)
      
      expect(typeof delay0).toBe('number')
      expect(typeof delay1).toBe('number')
      expect(delay0).not.toBe(delay1)
    })
  })

  describe('随机延迟动画', () => {
    it('应该创建随机延迟动画配置', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const result = chartAnimationService.createRandomAnimation(baseOption, 500)

      expect(result.animation).toBe(true)
      expect(result.animationDuration).toBe(1000)
      expect(result.animationEasing).toBe('cubicOut')
      expect(typeof result.animationDelay).toBe('function')
    })

    it('随机延迟应该在指定范围内', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const maxDelay = 500
      const result = chartAnimationService.createRandomAnimation(baseOption, maxDelay)
      const delayFunc = result.animationDelay as () => number

      // 测试多次以确保随机性
      for (let i = 0; i < 10; i++) {
        const delay = delayFunc()
        expect(delay).toBeGreaterThanOrEqual(0)
        expect(delay).toBeLessThanOrEqual(maxDelay)
      }
    })
  })

  describe('分组动画', () => {
    it('应该创建分组动画配置', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3, 4, 5, 6] }]
      }

      const result = chartAnimationService.createGroupAnimation(baseOption, 2)

      expect(result.animation).toBe(true)
      expect(result.animationDuration).toBe(1000)
      expect(result.animationEasing).toBe('cubicOut')
      expect(typeof result.animationDelay).toBe('function')
    })

    it('同组元素应该有相同的延迟', () => {
      const baseOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3, 4, 5, 6] }]
      }

      const groupSize = 2
      const result = chartAnimationService.createGroupAnimation(baseOption, groupSize)
      const delayFunc = result.animationDelay as (idx: number) => number

      expect(delayFunc(0)).toBe(delayFunc(1)) // 第一组
      expect(delayFunc(2)).toBe(delayFunc(3)) // 第二组
      expect(delayFunc(4)).toBe(delayFunc(5)) // 第三组
      expect(delayFunc(0)).not.toBe(delayFunc(2)) // 不同组
    })
  })

  describe('获取可用预设', () => {
    it('应该返回所有可用的动画预设', () => {
      const presets = chartAnimationService.getAvailablePresets()

      expect(presets).toBeInstanceOf(Array)
      expect(presets.length).toBeGreaterThan(0)
      expect(presets).toContain('smooth')
      expect(presets).toContain('bounce')
      expect(presets).toContain('elastic')
      expect(presets).toContain('fade')
      expect(presets).toContain('zoom')
      expect(presets).toContain('slide')
    })
  })

  describe('获取预设显示名称', () => {
    it('应该返回正确的中文显示名称', () => {
      expect(chartAnimationService.getPresetDisplayName('smooth')).toBe('平滑')
      expect(chartAnimationService.getPresetDisplayName('bounce')).toBe('弹跳')
      expect(chartAnimationService.getPresetDisplayName('elastic')).toBe('弹性')
      expect(chartAnimationService.getPresetDisplayName('fade')).toBe('淡入淡出')
      expect(chartAnimationService.getPresetDisplayName('zoom')).toBe('缩放')
      expect(chartAnimationService.getPresetDisplayName('slide')).toBe('滑动')
    })
  })

  describe('图表实例动画', () => {
    let mockChart: any

    beforeEach(() => {
      mockChart = {
        getOption: vi.fn(() => ({
          series: [
            {
              type: 'bar',
              data: [1, 2, 3],
              itemStyle: {}
            }
          ]
        })),
        setOption: vi.fn(),
        dispatchAction: vi.fn(),
        showLoading: vi.fn(),
        hideLoading: vi.fn()
      }
    })

    it('应该显示加载动画', () => {
      chartAnimationService.showLoading(mockChart, '加载中...')

      expect(mockChart.showLoading).toHaveBeenCalledWith('default', expect.objectContaining({
        text: '加载中...',
        color: '#188df0'
      }))
    })

    it('应该隐藏加载动画', () => {
      chartAnimationService.hideLoading(mockChart)

      expect(mockChart.hideLoading).toHaveBeenCalled()
    })

    it('应该创建高亮动画', () => {
      vi.useFakeTimers()

      chartAnimationService.createHighlightAnimation(mockChart, 0, 0)

      expect(mockChart.dispatchAction).toHaveBeenCalledWith({
        type: 'highlight',
        seriesIndex: 0,
        dataIndex: 0
      })

      vi.advanceTimersByTime(2000)

      expect(mockChart.dispatchAction).toHaveBeenCalledWith({
        type: 'downplay',
        seriesIndex: 0,
        dataIndex: 0
      })

      vi.useRealTimers()
    })

    it('应该创建数据更新动画', () => {
      const newOption: EChartsOption = {
        series: [{ type: 'bar', data: [4, 5, 6] }]
      }

      chartAnimationService.createUpdateAnimation(mockChart, newOption, 'smooth')

      expect(mockChart.setOption).toHaveBeenCalledWith(
        expect.objectContaining({
          animation: true,
          animationDuration: 1000,
          animationEasing: 'cubicOut'
        }),
        expect.any(Object)
      )
    })

    it('应该创建过渡动画', () => {
      vi.useFakeTimers()

      const fromOption: EChartsOption = {
        series: [{ type: 'bar', data: [1, 2, 3] }]
      }

      const toOption: EChartsOption = {
        series: [{ type: 'bar', data: [4, 5, 6] }]
      }

      chartAnimationService.createTransitionAnimation(mockChart, fromOption, toOption, 1000)

      expect(mockChart.setOption).toHaveBeenCalledWith(fromOption, true)

      vi.advanceTimersByTime(50)

      expect(mockChart.setOption).toHaveBeenCalledWith(
        expect.objectContaining({
          animation: true,
          animationDuration: 1000,
          animationEasing: 'cubicInOut'
        }),
        false
      )

      vi.useRealTimers()
    })
  })

  describe('循环高亮动画', () => {
    let mockChart: any

    beforeEach(() => {
      mockChart = {
        getOption: vi.fn(() => ({
          series: [
            {
              type: 'bar',
              data: [1, 2, 3]
            }
          ]
        })),
        dispatchAction: vi.fn()
      }
    })

    it('应该创建循环高亮动画并返回停止函数', () => {
      const stopFunc = chartAnimationService.createLoopHighlightAnimation(mockChart, 100)

      expect(typeof stopFunc).toBe('function')
      expect(mockChart.dispatchAction).toHaveBeenCalled()

      stopFunc()
    })

    it('停止函数应该停止循环动画', () => {
      vi.useFakeTimers()

      const stopFunc = chartAnimationService.createLoopHighlightAnimation(mockChart, 100)
      
      vi.advanceTimersByTime(100)
      const callCountBefore = mockChart.dispatchAction.mock.calls.length

      stopFunc()
      
      vi.advanceTimersByTime(200)
      const callCountAfter = mockChart.dispatchAction.mock.calls.length

      // 停止后不应该有新的调用
      expect(callCountAfter).toBeLessThanOrEqual(callCountBefore + 2) // 允许停止时的downplay和hideTip

      vi.useRealTimers()
    })
  })
})
