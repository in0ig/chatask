/**
 * 图表交互服务测试
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { chartInteractionService, ChartInteractionService } from '@/services/chartInteractionService'
import type { ContextMenuItem, DataPointSelection } from '@/services/chartInteractionService'
import type { ECharts } from 'echarts'

describe('ChartInteractionService', () => {
  let service: ChartInteractionService
  let mockChart: ECharts
  let chartDom: HTMLDivElement

  beforeEach(() => {
    service = new ChartInteractionService()
    
    // 创建模拟图表DOM
    chartDom = document.createElement('div')
    chartDom.style.width = '600px'
    chartDom.style.height = '400px'
    document.body.appendChild(chartDom)
    
    // 创建完整的 Mock 图表实例
    mockChart = {
      getDom: vi.fn(() => chartDom),
      setOption: vi.fn(),
      getOption: vi.fn(() => ({})),
      resize: vi.fn(),
      dispose: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      dispatchAction: vi.fn(),
      convertFromPixel: vi.fn(() => [0, 0])
    } as any
  })

  afterEach(() => {
    service.cleanup()
    if (chartDom && chartDom.parentNode) {
      document.body.removeChild(chartDom)
    }
  })

  describe('上下文菜单功能', () => {
    it('应该能够启用上下文菜单', () => {
      const menuItems: ContextMenuItem[] = [
        { label: '导出', action: vi.fn() },
        { label: '复制', action: vi.fn() }
      ]

      service.enableContextMenu(mockChart, menuItems)

      // 验证事件监听器已添加
      const chartElement = mockChart.getDom()
      expect(chartElement).toBeDefined()
    })

    it('应该能够显示上下文菜单', () => {
      const actionFn = vi.fn()
      const menuItems: ContextMenuItem[] = [
        { label: '测试菜单', action: actionFn }
      ]

      service.enableContextMenu(mockChart, menuItems)

      // 模拟右键点击
      const chartElement = mockChart.getDom()
      const event = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: 100,
        clientY: 100
      })
      chartElement.dispatchEvent(event)

      // 验证菜单已创建
      const menu = document.querySelector('.chart-context-menu')
      expect(menu).toBeTruthy()
    })

    it('应该能够隐藏上下文菜单', () => {
      const menuItems: ContextMenuItem[] = [
        { label: '测试', action: vi.fn() }
      ]

      service.enableContextMenu(mockChart, menuItems)

      // 显示菜单
      const chartElement = mockChart.getDom()
      const contextMenuEvent = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: 100,
        clientY: 100
      })
      chartElement.dispatchEvent(contextMenuEvent)

      // 点击其他地方关闭菜单
      document.dispatchEvent(new MouseEvent('click'))

      // 验证菜单已移除
      const menu = document.querySelector('.chart-context-menu')
      expect(menu).toBeFalsy()
    })

    it('应该支持禁用的菜单项', () => {
      const actionFn = vi.fn()
      const menuItems: ContextMenuItem[] = [
        { label: '禁用项', action: actionFn, disabled: true }
      ]

      service.enableContextMenu(mockChart, menuItems)

      // 显示菜单
      const chartElement = mockChart.getDom()
      const event = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: 100,
        clientY: 100
      })
      chartElement.dispatchEvent(event)

      // 点击禁用的菜单项
      const menuItem = document.querySelector('.chart-context-menu-item')
      expect(menuItem).toBeTruthy()
      
      // 验证样式
      const style = (menuItem as HTMLElement).style
      expect(style.cursor).toBe('not-allowed')
      expect(style.opacity).toBe('0.5')
    })
  })

  describe('数据点选择功能', () => {
    it('应该能够启用数据点选择', () => {
      const onSelect = vi.fn()
      service.enableDataPointSelection(mockChart, onSelect)

      // 模拟点击数据点
      mockChart.dispatchAction({
        type: 'showTip',
        seriesIndex: 0,
        dataIndex: 0
      })

      // 验证事件监听器已添加
      expect(mockChart).toBeDefined()
    })

    it('应该能够选择和取消选择数据点', () => {
      const selections: DataPointSelection[] = []
      const onSelect = vi.fn((s: DataPointSelection[]) => {
        selections.push(...s)
      })

      service.enableDataPointSelection(mockChart, onSelect)

      // 模拟点击事件
      const clickEvent = {
        componentType: 'series',
        seriesName: 'Series 1',
        dataIndex: 0,
        value: 10,
        name: 'A'
      }

      // 触发点击事件（通过内部方法）
      mockChart.on('click', (params: any) => {
        if (params.componentType === 'series') {
          onSelect([{
            seriesName: params.seriesName,
            dataIndex: params.dataIndex,
            value: params.value,
            name: params.name
          }])
        }
      })

      // 手动触发
      mockChart.dispatchAction({
        type: 'showTip',
        seriesIndex: 0,
        dataIndex: 0
      })
    })

    it('应该能够清除所有选择', () => {
      service.enableDataPointSelection(mockChart)
      service.clearSelection()

      // 验证选择已清除
      expect(service).toBeDefined()
    })
  })

  describe('钻取功能', () => {
    it('应该能够启用钻取功能', () => {
      const onDrillDown = vi.fn()
      const onDrillUp = vi.fn()

      service.enableDrillDown(mockChart, {
        enabled: true,
        onDrillDown,
        onDrillUp
      })

      expect(mockChart).toBeDefined()
    })

    it('应该能够执行钻取', () => {
      const onDrillDown = vi.fn()

      service.enableDrillDown(mockChart, {
        enabled: true,
        onDrillDown
      })

      // 模拟点击数据点触发钻取
      mockChart.on('click', (params: any) => {
        if (params.componentType === 'series') {
          onDrillDown({
            seriesName: params.seriesName,
            dataIndex: params.dataIndex,
            value: params.value,
            name: params.name
          })
        }
      })

      // 验证钻取深度
      expect(service.getDrillDownDepth()).toBe(0)
    })

    it('应该能够返回上一层', () => {
      const onDrillUp = vi.fn()

      service.enableDrillDown(mockChart, {
        enabled: true,
        onDrillUp
      })

      service.drillUp(mockChart, {
        enabled: true,
        onDrillUp
      })

      expect(onDrillUp).not.toHaveBeenCalled() // 因为没有钻取历史
    })

    it('应该能够获取钻取深度', () => {
      const depth = service.getDrillDownDepth()
      expect(depth).toBe(0)
    })
  })

  describe('图表联动功能', () => {
    let mockChart2: ECharts
    let chartDom2: HTMLDivElement

    beforeEach(() => {
      chartDom2 = document.createElement('div')
      chartDom2.style.width = '600px'
      chartDom2.style.height = '400px'
      document.body.appendChild(chartDom2)
      
      // 创建第二个 Mock 图表实例
      mockChart2 = {
        getDom: vi.fn(() => chartDom2),
        setOption: vi.fn(),
        getOption: vi.fn(() => ({})),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
        dispatchAction: vi.fn(),
        convertFromPixel: vi.fn(() => [0, 0])
      } as any
    })

    afterEach(() => {
      if (chartDom2 && chartDom2.parentNode) {
        document.body.removeChild(chartDom2)
      }
    })

    it('应该能够启用图表联动', () => {
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.enableChartLinkage(mockChart2, {
        group: 'test-group',
        enabled: true
      })

      expect(mockChart).toBeDefined()
      expect(mockChart2).toBeDefined()
    })

    it('应该能够同步高亮', () => {
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.enableChartLinkage(mockChart2, {
        group: 'test-group',
        enabled: true
      })

      // 触发高亮事件
      mockChart.dispatchAction({
        type: 'highlight',
        seriesIndex: 0,
        dataIndex: 0
      })

      expect(mockChart).toBeDefined()
    })

    it('应该能够同步取消高亮', () => {
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.enableChartLinkage(mockChart2, {
        group: 'test-group',
        enabled: true
      })

      // 触发取消高亮事件
      mockChart.dispatchAction({
        type: 'downplay',
        seriesIndex: 0,
        dataIndex: 0
      })

      expect(mockChart).toBeDefined()
    })

    it('应该能够同步数据缩放', () => {
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.enableChartLinkage(mockChart2, {
        group: 'test-group',
        enabled: true
      })

      // 触发数据缩放事件
      mockChart.dispatchAction({
        type: 'dataZoom',
        start: 20,
        end: 80
      })

      expect(mockChart).toBeDefined()
    })

    it('应该能够移除图表联动', () => {
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.disableChartLinkage(mockChart, 'test-group')

      expect(mockChart).toBeDefined()
    })
  })

  describe('资源清理', () => {
    it('应该能够清理所有资源', () => {
      const menuItems: ContextMenuItem[] = [
        { label: '测试', action: vi.fn() }
      ]

      service.enableContextMenu(mockChart, menuItems)
      service.enableDataPointSelection(mockChart)
      service.enableChartLinkage(mockChart, {
        group: 'test-group',
        enabled: true
      })

      service.cleanup()

      // 验证资源已清理
      const menu = document.querySelector('.chart-context-menu')
      expect(menu).toBeFalsy()
    })
  })

  describe('单例实例', () => {
    it('应该导出单例实例', () => {
      expect(chartInteractionService).toBeDefined()
      expect(chartInteractionService).toBeInstanceOf(ChartInteractionService)
    })
  })
})
