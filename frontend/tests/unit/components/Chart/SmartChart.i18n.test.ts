/**
 * SmartChart i18n 属性测试
 * Feature: i18n-language-switch
 * Property 4: SmartChart labels follow locale
 * Validates: Requirements 2.4
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import * as fc from 'fast-check'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import SmartChart from '@/components/Chart/SmartChart.vue'
import zhCN from '@/locales/zh-CN'
import enUS from '@/locales/en-US'
import type { ChartData, ChartType } from '@/types/chart'
import * as echarts from 'echarts'

// Mock ECharts
vi.mock('echarts', () => {
  class LinearGradient {
    type = 'linear'
    x: number; y: number; x2: number; y2: number; colorStops: any[]
    constructor(x0: number, y0: number, x1: number, y1: number, colorStops: any[]) {
      this.x = x0; this.y = y0; this.x2 = x1; this.y2 = y1; this.colorStops = colorStops
    }
  }
  return {
    default: { init: vi.fn(), graphic: { LinearGradient }, registerTheme: vi.fn() },
    init: vi.fn(),
    graphic: { LinearGradient },
    registerTheme: vi.fn(),
  }
})

// 所有支持的图表类型
const CHART_TYPES: ChartType[] = ['bar', 'line', 'pie', 'scatter', 'heatmap', 'radar']

// 中文标签映射（来自 zh-CN.ts）
const ZH_LABELS: Record<ChartType, string> = {
  bar: '柱状图',
  line: '折线图',
  pie: '饼图',
  scatter: '散点图',
  heatmap: '热力图',
  radar: '雷达图',
}

// 英文标签映射（来自 en-US.ts）
const EN_LABELS: Record<ChartType, string> = {
  bar: 'Bar Chart',
  line: 'Line Chart',
  pie: 'Pie Chart',
  scatter: 'Scatter Chart',
  heatmap: 'Heatmap',
  radar: 'Radar Chart',
}

const sampleData: ChartData = {
  columns: ['类别', '数值'],
  rows: [['A', 100], ['B', 200]],
}

function createI18nInstance(locale: 'zh-CN' | 'en-US') {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'zh-CN',
    messages: { 'zh-CN': zhCN, 'en-US': enUS },
  })
}

describe('SmartChart i18n - Property 4: SmartChart labels follow locale', () => {
  let mockChartInstance: any

  beforeEach(() => {
    setActivePinia(createPinia())
    mockChartInstance = {
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      getDataURL: vi.fn(() => 'data:image/png;base64,mock'),
      showLoading: vi.fn(),
      hideLoading: vi.fn(),
    }
    vi.mocked(echarts.init).mockReturnValue(mockChartInstance as any)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Feature: i18n-language-switch, Property 4: SmartChart labels follow locale
  it('Property 4: getChartTypeLabel returns English labels when locale is en-US', () => {
    // fast-check: for any chart type, en-US locale returns English label
    fc.assert(
      fc.property(fc.constantFrom(...CHART_TYPES), (chartType) => {
        const i18n = createI18nInstance('en-US')
        const wrapper = mount(SmartChart, {
          props: { type: chartType, data: sampleData },
          global: { plugins: [i18n, createPinia()] },
        })

        const vm = wrapper.vm as any
        const label = vm.getChartTypeLabel(chartType)

        expect(label).toBe(EN_LABELS[chartType])
        wrapper.unmount()
      }),
      { numRuns: 100 }
    )
  })

  it('Property 4: getChartTypeLabel returns Chinese labels when locale is zh-CN', () => {
    // fast-check: for any chart type, zh-CN locale returns Chinese label
    fc.assert(
      fc.property(fc.constantFrom(...CHART_TYPES), (chartType) => {
        const i18n = createI18nInstance('zh-CN')
        const wrapper = mount(SmartChart, {
          props: { type: chartType, data: sampleData },
          global: { plugins: [i18n, createPinia()] },
        })

        const vm = wrapper.vm as any
        const label = vm.getChartTypeLabel(chartType)

        expect(label).toBe(ZH_LABELS[chartType])
        wrapper.unmount()
      }),
      { numRuns: 100 }
    )
  })

  it('Property 4: en-US and zh-CN labels are always different for all chart types', () => {
    // For any chart type, the English and Chinese labels must differ
    fc.assert(
      fc.property(fc.constantFrom(...CHART_TYPES), (chartType) => {
        expect(EN_LABELS[chartType]).not.toBe(ZH_LABELS[chartType])
      }),
      { numRuns: 100 }
    )
  })
})
