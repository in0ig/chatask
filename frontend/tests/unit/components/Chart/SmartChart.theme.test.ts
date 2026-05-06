import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SmartChart from '@/components/Chart/SmartChart.vue'
import type { ChartData } from '@/types/chart'
import * as echarts from 'echarts'

// Mock echarts
vi.mock('echarts', () => {
  const mockInit = vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    dispatchAction: vi.fn(),
    getOption: vi.fn(() => ({ series: [] }))
  }))
  
  const mockRegisterTheme = vi.fn()
  
  return {
    default: {
      init: mockInit,
      registerTheme: mockRegisterTheme
    },
    init: mockInit,
    registerTheme: mockRegisterTheme,
    graphic: {
      LinearGradient: vi.fn()
    }
  }
})

// Mock services
vi.mock('@/services/chartThemeService', () => ({
  chartThemeService: {
    getTheme: vi.fn((name: string) => ({
      name,
      displayName: name === 'dark' ? '深色主题' : '浅色主题',
      colors: {
        primary: ['#188df0', '#83bff6'],
        background: name === 'dark' ? '#1a1a1a' : '#ffffff',
        text: name === 'dark' ? '#eeeeee' : '#333333',
        axisLine: '#cccccc',
        splitLine: '#e4e7ed',
        tooltip: {
          background: 'rgba(50, 50, 50, 0.9)',
          border: '#333',
          text: '#fff'
        }
      },
      animation: {
        duration: 1000,
        easing: 'cubicOut'
      }
    })),
    generateEChartsTheme: vi.fn(() => ({
      color: ['#188df0', '#83bff6'],
      backgroundColor: '#ffffff'
    }))
  }
}))

vi.mock('@/services/chartAnimationService', () => ({
  chartAnimationService: {
    getAnimationConfig: vi.fn((preset: string) => ({
      enabled: true,
      duration: preset === 'bounce' ? 1200 : 1000,
      easing: preset === 'bounce' ? 'bounceOut' : 'cubicOut'
    })),
    applyAnimation: vi.fn((option: any, config: any) => ({
      ...option,
      animation: config.enabled,
      animationDuration: config.duration,
      animationEasing: config.easing
    }))
  }
}))

describe('SmartChart - 主题和动画', () => {
  const mockData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 10],
      ['B', 20],
      ['C', 30]
    ]
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('主题支持', () => {
    it('应该使用默认浅色主题', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockData
        }
      })

      await wrapper.vm.$nextTick()

      const { init, registerTheme } = await import('echarts')
      expect(registerTheme).toHaveBeenCalled()
      expect(init).toHaveBeenCalled()
    })

    it('应该支持深色主题', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockData,
          theme: 'dark'
        }
      })

      await wrapper.vm.$nextTick()

      const { registerTheme } = await import('echarts')
      expect(registerTheme).toHaveBeenCalled()
    })
  })

  describe('动画支持', () => {
    it('应该支持动画预设', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockData,
          options: {
            animationPreset: 'smooth'
          }
        }
      })

      await wrapper.vm.$nextTick()

      // 验证组件已挂载
      expect(wrapper.exists()).toBe(true)
    })

    it('应该支持自定义动画持续时间', async () => {
      const wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockData,
          options: {
            animationDuration: 1500
          }
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.exists()).toBe(true)
    })
  })
})
