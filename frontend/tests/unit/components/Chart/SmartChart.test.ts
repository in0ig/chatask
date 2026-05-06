/**
 * SmartChart 组件测试
 * 测试智能图表组件的核心功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import SmartChart from '@/components/Chart/SmartChart.vue'
import type { ChartData } from '@/types/chart'
import * as echarts from 'echarts'
import ElementPlus from 'element-plus'

// Mock ECharts with proper LinearGradient constructor
vi.mock('echarts', () => {
  // Define LinearGradient class inside the factory
  class LinearGradient {
    type = 'linear'
    x: number
    y: number
    x2: number
    y2: number
    colorStops: any[]

    constructor(x0: number, y0: number, x1: number, y1: number, colorStops: any[]) {
      this.x = x0
      this.y = y0
      this.x2 = x1
      this.y2 = y1
      this.colorStops = colorStops
    }
  }

  return {
    default: {
      init: vi.fn(),
      graphic: {
        LinearGradient
      }
    },
    init: vi.fn(),
    graphic: {
      LinearGradient
    }
  }
})

describe('SmartChart.vue', () => {
  let wrapper: VueWrapper
  let mockChartInstance: any

  const sampleBarData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 100],
      ['B', 200],
      ['C', 150]
    ],
    title: '测试柱状图'
  }

  const sampleLineData: ChartData = {
    columns: ['日期', '销量'],
    rows: [
      ['2024-01', 100],
      ['2024-02', 200],
      ['2024-03', 150]
    ],
    metadata: {
      columnTypes: ['date', 'number']
    }
  }

  const samplePieData: ChartData = {
    columns: ['类别', '占比'],
    rows: [
      ['A', 30],
      ['B', 40],
      ['C', 30]
    ]
  }

  const sampleScatterData: ChartData = {
    columns: ['X轴', 'Y轴'],
    rows: [
      [10, 20],
      [20, 30],
      [30, 25]
    ],
    metadata: {
      columnTypes: ['number', 'number']
    }
  }

  beforeEach(() => {
    // 创建 mock chart 实例
    mockChartInstance = {
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      getDataURL: vi.fn(() => 'data:image/png;base64,mock')
    }

    // Mock echarts.init
    vi.mocked(echarts.init).mockReturnValue(mockChartInstance as any)

    // Mock window.addEventListener
    vi.spyOn(window, 'addEventListener')
    vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  // 测试1: 组件正确挂载和初始化 ECharts 实例
  it('应该正确挂载并初始化 ECharts 实例', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    expect(echarts.init).toHaveBeenCalled()
    expect(mockChartInstance.setOption).toHaveBeenCalled()
  })

  // 测试2: 支持 'auto' 模式自动选择图表类型
  it('应该在 auto 模式下自动选择图表类型', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: sampleLineData // 包含日期列，应该选择折线图
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 验证 setOption 被调用，且配置中包含 line 类型
    expect(mockChartInstance.setOption).toHaveBeenCalled()
    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('line')
  })

  // 测试3: 支持手动指定图表类型
  it('应该支持手动指定图表类型', async () => {
    const chartTypes = ['bar', 'line', 'pie', 'scatter'] as const

    for (const type of chartTypes) {
      wrapper = mount(SmartChart, {
        props: {
          type,
          data: sampleBarData
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      const optionCall = mockChartInstance.setOption.mock.calls[mockChartInstance.setOption.mock.calls.length - 1][0]
      expect(optionCall.series[0].type).toBe(type)

      wrapper.unmount()
      vi.clearAllMocks()
      mockChartInstance.setOption.mockClear()
    }
  })

  // 测试4: 正确渲染柱状图
  it('应该正确渲染柱状图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'bar',
        data: sampleBarData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('bar')
    expect(optionCall.xAxis.type).toBe('category')
    expect(optionCall.yAxis.type).toBe('value')
    expect(optionCall.xAxis.data).toEqual(['A', 'B', 'C'])
    expect(optionCall.series[0].data).toEqual([100, 200, 150])
  })

  // 测试5: 正确渲染折线图
  it('应该正确渲染折线图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'line',
        data: sampleLineData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('line')
    expect(optionCall.series[0].smooth).toBe(true)
    expect(optionCall.series[0].areaStyle).toBeDefined()
  })

  // 测试6: 正确渲染饼图
  it('应该正确渲染饼图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'pie',
        data: samplePieData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('pie')
    expect(optionCall.series[0].radius).toEqual(['40%', '70%'])
    expect(optionCall.series[0].data).toEqual([
      { name: 'A', value: 30 },
      { name: 'B', value: 40 },
      { name: 'C', value: 30 }
    ])
  })

  // 测试7: 正确渲染散点图
  it('应该正确渲染散点图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'scatter',
        data: sampleScatterData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('scatter')
    expect(optionCall.xAxis.type).toBe('value')
    expect(optionCall.yAxis.type).toBe('value')
    expect(optionCall.series[0].data).toEqual([
      [10, 20],
      [20, 30],
      [30, 25]
    ])
  })

  // 测试8: 响应式设计 - 窗口大小变化时图表自动调整
  it('应该在窗口大小变化时自动调整图表', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        responsive: true
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 验证添加了 resize 监听器
    expect(window.addEventListener).toHaveBeenCalledWith('resize', expect.any(Function))

    // 获取 resize 处理函数并调用
    const addEventListenerCalls = vi.mocked(window.addEventListener).mock.calls
    const resizeCall = addEventListenerCalls.find(call => call[0] === 'resize')
    
    if (resizeCall && resizeCall[1]) {
      const resizeHandler = resizeCall[1] as EventListener
      resizeHandler(new Event('resize'))
      
      // 等待下一个 tick
      await wrapper.vm.$nextTick()
      
      expect(mockChartInstance.resize).toHaveBeenCalled()
    } else {
      // 如果没有找到 resize 处理函数，至少验证 addEventListener 被调用了
      expect(window.addEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
    }
  })

  // 测试9: 数据变化时图表自动更新
  it('应该在数据变化时自动更新图表', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'bar',
        data: sampleBarData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const initialCallCount = mockChartInstance.setOption.mock.calls.length

    // 更新数据
    const newData: ChartData = {
      columns: ['类别', '数值'],
      rows: [
        ['D', 300],
        ['E', 400]
      ]
    }

    await wrapper.setProps({ data: newData })
    await wrapper.vm.$nextTick()

    // 验证 setOption 再次被调用
    expect(mockChartInstance.setOption.mock.calls.length).toBeGreaterThan(initialCallCount)
  })

  // 测试10: 支持图表导出功能
  it('应该支持图表导出功能', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        exportable: true
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // Mock document.createElement 和 click
    const mockLink = {
      download: '',
      href: '',
      click: vi.fn()
    }
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)

    // 触发导出
    const vm = wrapper.vm as any
    vm.exportChart('png')

    expect(mockChartInstance.getDataURL).toHaveBeenCalledWith({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    expect(mockLink.click).toHaveBeenCalled()
  })

  // 测试11: 支持主题切换
  it('应该支持主题切换', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        theme: 'light'
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    const initialInitCalls = vi.mocked(echarts.init).mock.calls.length

    // 切换主题
    await wrapper.setProps({ theme: 'dark' })
    await wrapper.vm.$nextTick()

    // 验证 dispose 和重新初始化
    expect(mockChartInstance.dispose).toHaveBeenCalled()
    expect(vi.mocked(echarts.init).mock.calls.length).toBeGreaterThan(initialInitCalls)
  })

  // 测试12: 组件卸载时正确清理 ECharts 实例
  it('应该在组件卸载时正确清理资源', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        responsive: true
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 卸载组件
    wrapper.unmount()

    // 验证清理操作
    expect(window.removeEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
    expect(mockChartInstance.dispose).toHaveBeenCalled()
  })

  // 额外测试: 图表类型切换
  it('应该支持通过工具栏切换图表类型', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: sampleBarData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 模拟点击切换图表类型
    const vm = wrapper.vm as any
    const initialType = vm.currentChartType

    vm.changeChartType('line')
    await wrapper.vm.$nextTick()

    expect(vm.currentChartType).toBe('line')
    expect(vm.currentChartType).not.toBe(initialType)
  })

  // 额外测试: 自定义配置选项
  it('应该支持自定义配置选项', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        options: {
          height: '500px',
          showToolbar: false,
          showLegend: false
        }
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 验证工具栏不显示
    const toolbar = wrapper.find('.chart-toolbar')
    expect(toolbar.exists()).toBe(false)

    // 验证高度设置
    const chartElement = wrapper.find('.chart-element')
    expect(chartElement.attributes('style')).toContain('500px')
  })

  // 额外测试: 空数据处理
  it('应该正确处理空数据', async () => {
    const emptyData: ChartData = {
      columns: [],
      rows: []
    }

    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: emptyData
      },
      global: {
        plugins: [ElementPlus]
      }
    })

    await wrapper.vm.$nextTick()

    // 应该默认使用柱状图
    expect(mockChartInstance.setOption).toHaveBeenCalled()
  })
})


describe('SmartChart.vue', () => {
  let wrapper: VueWrapper
  let mockChartInstance: any

  const sampleBarData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 100],
      ['B', 200],
      ['C', 150]
    ],
    title: '测试柱状图'
  }

  const sampleLineData: ChartData = {
    columns: ['日期', '销量'],
    rows: [
      ['2024-01', 100],
      ['2024-02', 200],
      ['2024-03', 150]
    ],
    metadata: {
      columnTypes: ['date', 'number']
    }
  }

  const samplePieData: ChartData = {
    columns: ['类别', '占比'],
    rows: [
      ['A', 30],
      ['B', 40],
      ['C', 30]
    ]
  }

  const sampleScatterData: ChartData = {
    columns: ['X轴', 'Y轴'],
    rows: [
      [10, 20],
      [20, 30],
      [30, 25]
    ],
    metadata: {
      columnTypes: ['number', 'number']
    }
  }

  beforeEach(() => {
    // 创建 mock chart 实例
    mockChartInstance = {
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      getDataURL: vi.fn(() => 'data:image/png;base64,mock')
    }

    // Mock echarts.init
    vi.mocked(echarts.init).mockReturnValue(mockChartInstance as any)

    // Mock window.addEventListener
    vi.spyOn(window, 'addEventListener')
    vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  // 测试1: 组件正确挂载和初始化 ECharts 实例
  it('应该正确挂载并初始化 ECharts 实例', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData
      }
    })

    await wrapper.vm.$nextTick()

    expect(echarts.init).toHaveBeenCalled()
    expect(mockChartInstance.setOption).toHaveBeenCalled()
  })

  // 测试2: 支持 'auto' 模式自动选择图表类型
  it('应该在 auto 模式下自动选择图表类型', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: sampleLineData // 包含日期列，应该选择折线图
      }
    })

    await wrapper.vm.$nextTick()

    // 验证 setOption 被调用，且配置中包含 line 类型
    expect(mockChartInstance.setOption).toHaveBeenCalled()
    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('line')
  })

  // 测试3: 支持手动指定图表类型
  it('应该支持手动指定图表类型', async () => {
    const chartTypes = ['bar', 'line', 'pie', 'scatter'] as const

    for (const type of chartTypes) {
      wrapper = mount(SmartChart, {
        props: {
          type,
          data: sampleBarData
        }
      })

      await wrapper.vm.$nextTick()

      const optionCall = mockChartInstance.setOption.mock.calls[mockChartInstance.setOption.mock.calls.length - 1][0]
      expect(optionCall.series[0].type).toBe(type)

      wrapper.unmount()
      vi.clearAllMocks()
      mockChartInstance.setOption.mockClear()
    }
  })

  // 测试4: 正确渲染柱状图
  it('应该正确渲染柱状图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'bar',
        data: sampleBarData
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('bar')
    expect(optionCall.xAxis.type).toBe('category')
    expect(optionCall.yAxis.type).toBe('value')
    expect(optionCall.xAxis.data).toEqual(['A', 'B', 'C'])
    expect(optionCall.series[0].data).toEqual([100, 200, 150])
  })

  // 测试5: 正确渲染折线图
  it('应该正确渲染折线图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'line',
        data: sampleLineData
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('line')
    expect(optionCall.series[0].smooth).toBe(true)
    expect(optionCall.series[0].areaStyle).toBeDefined()
  })

  // 测试6: 正确渲染饼图
  it('应该正确渲染饼图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'pie',
        data: samplePieData
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('pie')
    expect(optionCall.series[0].radius).toEqual(['40%', '70%'])
    expect(optionCall.series[0].data).toEqual([
      { name: 'A', value: 30 },
      { name: 'B', value: 40 },
      { name: 'C', value: 30 }
    ])
  })

  // 测试7: 正确渲染散点图
  it('应该正确渲染散点图', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'scatter',
        data: sampleScatterData
      }
    })

    await wrapper.vm.$nextTick()

    const optionCall = mockChartInstance.setOption.mock.calls[0][0]
    expect(optionCall.series[0].type).toBe('scatter')
    expect(optionCall.xAxis.type).toBe('value')
    expect(optionCall.yAxis.type).toBe('value')
    expect(optionCall.series[0].data).toEqual([
      [10, 20],
      [20, 30],
      [30, 25]
    ])
  })

  // 测试8: 响应式设计 - 窗口大小变化时图表自动调整
  it('应该在窗口大小变化时自动调整图表', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        responsive: true
      }
    })

    await wrapper.vm.$nextTick()

    // 验证添加了 resize 监听器
    expect(window.addEventListener).toHaveBeenCalledWith('resize', expect.any(Function))

    // 模拟窗口大小变化
    const resizeHandler = vi.mocked(window.addEventListener).mock.calls.find(
      call => call[0] === 'resize'
    )?.[1] as EventListener

    if (resizeHandler) {
      resizeHandler(new Event('resize'))
      expect(mockChartInstance.resize).toHaveBeenCalled()
    }
  })

  // 测试9: 数据变化时图表自动更新
  it('应该在数据变化时自动更新图表', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'bar',
        data: sampleBarData
      }
    })

    await wrapper.vm.$nextTick()

    const initialCallCount = mockChartInstance.setOption.mock.calls.length

    // 更新数据
    const newData: ChartData = {
      columns: ['类别', '数值'],
      rows: [
        ['D', 300],
        ['E', 400]
      ]
    }

    await wrapper.setProps({ data: newData })
    await wrapper.vm.$nextTick()

    // 验证 setOption 再次被调用
    expect(mockChartInstance.setOption.mock.calls.length).toBeGreaterThan(initialCallCount)
  })

  // 测试10: 支持图表导出功能
  it('应该支持图表导出功能', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        exportable: true
      }
    })

    await wrapper.vm.$nextTick()

    // 查找导出按钮
    const exportButton = wrapper.find('.el-dropdown')
    expect(exportButton.exists()).toBe(true)

    // Mock document.createElement 和 click
    const mockLink = {
      download: '',
      href: '',
      click: vi.fn()
    }
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)

    // 触发导出
    const vm = wrapper.vm as any
    vm.exportChart('png')

    expect(mockChartInstance.getDataURL).toHaveBeenCalledWith({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    expect(mockLink.click).toHaveBeenCalled()
  })

  // 测试11: 支持主题切换
  it('应该支持主题切换', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        theme: 'light'
      }
    })

    await wrapper.vm.$nextTick()

    const initialInitCalls = vi.mocked(echarts.init).mock.calls.length

    // 切换主题
    await wrapper.setProps({ theme: 'dark' })
    await wrapper.vm.$nextTick()

    // 验证 dispose 和重新初始化
    expect(mockChartInstance.dispose).toHaveBeenCalled()
    expect(vi.mocked(echarts.init).mock.calls.length).toBeGreaterThan(initialInitCalls)
  })

  // 测试12: 组件卸载时正确清理 ECharts 实例
  it('应该在组件卸载时正确清理资源', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        responsive: true
      }
    })

    await wrapper.vm.$nextTick()

    // 卸载组件
    wrapper.unmount()

    // 验证清理操作
    expect(window.removeEventListener).toHaveBeenCalledWith('resize', expect.any(Function))
    expect(mockChartInstance.dispose).toHaveBeenCalled()
  })

  // 额外测试: 图表类型切换
  it('应该支持通过工具栏切换图表类型', async () => {
    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: sampleBarData
      }
    })

    await wrapper.vm.$nextTick()

    // 查找图表类型按钮
    const buttons = wrapper.findAll('.el-button')
    expect(buttons.length).toBeGreaterThan(0)

    // 模拟点击切换图表类型
    const vm = wrapper.vm as any
    const initialType = vm.currentChartType

    vm.changeChartType('line')
    await wrapper.vm.$nextTick()

    expect(vm.currentChartType).toBe('line')
    expect(vm.currentChartType).not.toBe(initialType)
  })

  // 额外测试: 自定义配置选项
  it('应该支持自定义配置选项', async () => {
    wrapper = mount(SmartChart, {
      props: {
        data: sampleBarData,
        options: {
          height: '500px',
          showToolbar: false,
          showLegend: false
        }
      }
    })

    await wrapper.vm.$nextTick()

    // 验证工具栏不显示
    const toolbar = wrapper.find('.chart-toolbar')
    expect(toolbar.exists()).toBe(false)

    // 验证高度设置
    const chartElement = wrapper.find('.chart-element')
    expect(chartElement.attributes('style')).toContain('500px')
  })

  // 额外测试: 空数据处理
  it('应该正确处理空数据', async () => {
    const emptyData: ChartData = {
      columns: [],
      rows: []
    }

    wrapper = mount(SmartChart, {
      props: {
        type: 'auto',
        data: emptyData
      }
    })

    await wrapper.vm.$nextTick()

    // 应该默认使用柱状图
    expect(mockChartInstance.setOption).toHaveBeenCalled()
  })
})
