/**
 * SmartChart 组件交互功能测试
 * 测试图表的高级交互功能：上下文菜单、数据点选择、钻取、联动等
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import SmartChart from '@/components/Chart/SmartChart.vue'
import type { ChartData, ChartOptions } from '@/types/chart'
import * as echarts from 'echarts'
import ElementPlus from 'element-plus'
import { chartInteractionService } from '@/services/chartInteractionService'

// Mock ECharts
vi.mock('echarts', () => {
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

// Mock chartInteractionService
vi.mock('@/services/chartInteractionService', () => ({
  chartInteractionService: {
    enableContextMenu: vi.fn(),
    enableDataPointSelection: vi.fn(),
    enableDrillDown: vi.fn(),
    enableChartLinkage: vi.fn(),
    disableChartLinkage: vi.fn(),
    cleanup: vi.fn()
  }
}))

describe('SmartChart.vue - 交互功能', () => {
  let wrapper: VueWrapper
  let mockChartInstance: any

  const mockChartData: ChartData = {
    columns: ['类别', '数值'],
    rows: [
      ['A', 10],
      ['B', 20],
      ['C', 30]
    ],
    title: '测试图表'
  }

  beforeEach(() => {
    // 创建 mock 图表实例
    mockChartInstance = {
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
      getDom: vi.fn(() => document.createElement('div')),
      on: vi.fn(),
      off: vi.fn(),
      dispatchAction: vi.fn(),
      getOption: vi.fn(() => ({})),
      convertFromPixel: vi.fn(() => [0, 0])
    }

    // Mock echarts.init
    vi.mocked(echarts.init).mockReturnValue(mockChartInstance as any)

    // 清除之前的 mock 调用
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('上下文菜单功能', () => {
    it('应该在启用上下文菜单选项时初始化上下文菜单', async () => {
      const options: ChartOptions = {
        enableContextMenu: true
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableContextMenu 被调用
      expect(chartInteractionService.enableContextMenu).toHaveBeenCalled()
    })

    it('应该在未启用上下文菜单选项时不初始化上下文菜单', async () => {
      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableContextMenu 未被调用
      expect(chartInteractionService.enableContextMenu).not.toHaveBeenCalled()
    })
  })

  describe('数据点选择功能', () => {
    it('应该在启用数据点选择选项时初始化数据点选择', async () => {
      const options: ChartOptions = {
        enableDataPointSelection: true
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableDataPointSelection 被调用
      expect(chartInteractionService.enableDataPointSelection).toHaveBeenCalled()
    })

    it('应该在未启用数据点选择选项时不初始化数据点选择', async () => {
      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableDataPointSelection 未被调用
      expect(chartInteractionService.enableDataPointSelection).not.toHaveBeenCalled()
    })
  })

  describe('钻取功能', () => {
    it('应该在启用钻取选项时初始化钻取功能', async () => {
      const options: ChartOptions = {
        enableDrillDown: true
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableDrillDown 被调用
      expect(chartInteractionService.enableDrillDown).toHaveBeenCalled()
    })

    it('应该在未启用钻取选项时不初始化钻取功能', async () => {
      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableDrillDown 未被调用
      expect(chartInteractionService.enableDrillDown).not.toHaveBeenCalled()
    })
  })

  describe('图表联动功能', () => {
    it('应该在启用图表联动选项时初始化图表联动', async () => {
      const options: ChartOptions = {
        enableChartLinkage: true,
        linkageGroup: 'test-group'
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableChartLinkage 被调用
      expect(chartInteractionService.enableChartLinkage).toHaveBeenCalled()
    })

    it('应该在未启用图表联动选项时不初始化图表联动', async () => {
      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableChartLinkage 未被调用
      expect(chartInteractionService.enableChartLinkage).not.toHaveBeenCalled()
    })

    it('应该在组件卸载时移除图表联动', async () => {
      const options: ChartOptions = {
        enableChartLinkage: true,
        linkageGroup: 'test-group'
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 卸载组件
      wrapper.unmount()

      // 验证 disableChartLinkage 被调用
      expect(chartInteractionService.disableChartLinkage).toHaveBeenCalledWith(
        mockChartInstance,
        'test-group'
      )
    })
  })

  describe('综合交互功能', () => {
    it('应该能够同时启用多个交互功能', async () => {
      const options: ChartOptions = {
        enableContextMenu: true,
        enableDataPointSelection: true,
        enableDrillDown: true,
        enableChartLinkage: true,
        linkageGroup: 'test-group'
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证所有交互功能都被初始化
      expect(chartInteractionService.enableContextMenu).toHaveBeenCalled()
      expect(chartInteractionService.enableDataPointSelection).toHaveBeenCalled()
      expect(chartInteractionService.enableDrillDown).toHaveBeenCalled()
      expect(chartInteractionService.enableChartLinkage).toHaveBeenCalled()
    })

    it('应该在组件卸载时清理所有交互资源', async () => {
      const options: ChartOptions = {
        enableContextMenu: true,
        enableDataPointSelection: true,
        enableDrillDown: true,
        enableChartLinkage: true,
        linkageGroup: 'test-group'
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 卸载组件
      wrapper.unmount()

      // 验证清理方法被调用
      expect(chartInteractionService.disableChartLinkage).toHaveBeenCalled()
      expect(chartInteractionService.cleanup).toHaveBeenCalled()
    })
  })

  describe('边界情况处理', () => {
    it('应该在图表实例不存在时不初始化交互功能', async () => {
      // Mock echarts.init 返回 null
      vi.mocked(echarts.init).mockReturnValue(null as any)

      const options: ChartOptions = {
        enableContextMenu: true
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证交互功能未被初始化
      expect(chartInteractionService.enableContextMenu).not.toHaveBeenCalled()
    })

    it('应该在没有联动组名称时不启用图表联动', async () => {
      const options: ChartOptions = {
        enableChartLinkage: true
        // 缺少 linkageGroup
      }

      wrapper = mount(SmartChart, {
        props: {
          type: 'bar',
          data: mockChartData,
          options
        },
        global: {
          plugins: [ElementPlus]
        }
      })

      await wrapper.vm.$nextTick()

      // 验证 enableChartLinkage 未被调用
      expect(chartInteractionService.enableChartLinkage).not.toHaveBeenCalled()
    })
  })
})
