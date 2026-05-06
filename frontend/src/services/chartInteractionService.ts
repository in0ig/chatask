/**
 * 图表交互服务
 * 提供图表的高级交互功能：上下文菜单、数据点选择、钻取、联动等
 */

import type { ECharts } from 'echarts'
import type { ChartData } from '@/types/chart'

/**
 * 上下文菜单项
 */
export interface ContextMenuItem {
  label: string
  icon?: string
  action: (data: any) => void
  disabled?: boolean
}

/**
 * 数据点选择事件
 */
export interface DataPointSelection {
  seriesName: string
  dataIndex: number
  value: any
  name: string
}

/**
 * 钻取配置
 */
export interface DrillDownConfig {
  enabled: boolean
  onDrillDown?: (data: DataPointSelection) => void
  onDrillUp?: () => void
}

/**
 * 图表联动配置
 */
export interface ChartLinkageConfig {
  group: string // 联动组名称
  enabled: boolean
}

/**
 * 图表交互服务类
 */
export class ChartInteractionService {
  private contextMenuElement: HTMLElement | null = null
  private selectedDataPoints: Set<string> = new Set()
  private drillDownStack: any[] = []
  private linkageGroups: Map<string, Set<ECharts>> = new Map()

  /**
   * 启用上下文菜单
   */
  enableContextMenu(
    chart: ECharts,
    menuItems: ContextMenuItem[]
  ): void {
    const chartDom = chart.getDom()
    
    // 监听右键点击事件
    chartDom.addEventListener('contextmenu', (e: MouseEvent) => {
      e.preventDefault()
      
      // 获取点击位置的数据
      const params = chart.convertFromPixel('grid', [e.offsetX, e.offsetY])
      
      // 显示上下文菜单
      this.showContextMenu(e.clientX, e.clientY, menuItems, params)
    })

    // 点击其他地方关闭菜单
    document.addEventListener('click', () => {
      this.hideContextMenu()
    })
  }

  /**
   * 显示上下文菜单
   */
  private showContextMenu(
    x: number,
    y: number,
    items: ContextMenuItem[],
    data: any
  ): void {
    this.hideContextMenu()

    const menu = document.createElement('div')
    menu.className = 'chart-context-menu'
    menu.style.cssText = `
      position: fixed;
      left: ${x}px;
      top: ${y}px;
      background: white;
      border: 1px solid #ddd;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      z-index: 9999;
      min-width: 150px;
      padding: 4px 0;
    `

    items.forEach(item => {
      const menuItem = document.createElement('div')
      menuItem.className = 'chart-context-menu-item'
      menuItem.style.cssText = `
        padding: 8px 16px;
        cursor: ${item.disabled ? 'not-allowed' : 'pointer'};
        opacity: ${item.disabled ? '0.5' : '1'};
        transition: background-color 0.2s;
      `
      menuItem.textContent = item.label

      if (!item.disabled) {
        menuItem.addEventListener('mouseenter', () => {
          menuItem.style.backgroundColor = '#f5f5f5'
        })
        menuItem.addEventListener('mouseleave', () => {
          menuItem.style.backgroundColor = 'transparent'
        })
        menuItem.addEventListener('click', () => {
          item.action(data)
          this.hideContextMenu()
        })
      }

      menu.appendChild(menuItem)
    })

    document.body.appendChild(menu)
    this.contextMenuElement = menu
  }

  /**
   * 隐藏上下文菜单
   */
  private hideContextMenu(): void {
    if (this.contextMenuElement) {
      document.body.removeChild(this.contextMenuElement)
      this.contextMenuElement = null
    }
  }

  /**
   * 启用数据点选择
   */
  enableDataPointSelection(
    chart: ECharts,
    onSelect?: (selections: DataPointSelection[]) => void
  ): void {
    chart.on('click', (params: any) => {
      if (params.componentType === 'series') {
        const key = `${params.seriesName}-${params.dataIndex}`
        
        if (this.selectedDataPoints.has(key)) {
          this.selectedDataPoints.delete(key)
        } else {
          this.selectedDataPoints.add(key)
        }

        // 高亮选中的数据点
        this.highlightSelectedPoints(chart)

        // 触发回调
        if (onSelect) {
          const selections = Array.from(this.selectedDataPoints).map(k => {
            const [seriesName, dataIndex] = k.split('-')
            return {
              seriesName,
              dataIndex: parseInt(dataIndex),
              value: params.value,
              name: params.name
            }
          })
          onSelect(selections)
        }
      }
    })
  }

  /**
   * 高亮选中的数据点
   */
  private highlightSelectedPoints(chart: ECharts): void {
    const option = chart.getOption()
    // 这里可以添加高亮逻辑
    // 例如修改 series 的 emphasis 配置
  }

  /**
   * 清除所有选择
   */
  clearSelection(): void {
    this.selectedDataPoints.clear()
  }

  /**
   * 启用钻取功能
   */
  enableDrillDown(
    chart: ECharts,
    config: DrillDownConfig
  ): void {
    if (!config.enabled) return

    chart.on('click', (params: any) => {
      if (params.componentType === 'series' && config.onDrillDown) {
        const selection: DataPointSelection = {
          seriesName: params.seriesName,
          dataIndex: params.dataIndex,
          value: params.value,
          name: params.name
        }

        // 保存当前状态到钻取栈
        this.drillDownStack.push({
          option: chart.getOption(),
          data: selection
        })

        config.onDrillDown(selection)
      }
    })
  }

  /**
   * 钻取返回
   */
  drillUp(chart: ECharts, config: DrillDownConfig): void {
    if (this.drillDownStack.length > 0) {
      const previous = this.drillDownStack.pop()
      chart.setOption(previous.option, true)

      if (config.onDrillUp) {
        config.onDrillUp()
      }
    }
  }

  /**
   * 获取钻取深度
   */
  getDrillDownDepth(): number {
    return this.drillDownStack.length
  }

  /**
   * 启用图表联动
   */
  enableChartLinkage(
    chart: ECharts,
    config: ChartLinkageConfig
  ): void {
    if (!config.enabled) return

    // 将图表添加到联动组
    if (!this.linkageGroups.has(config.group)) {
      this.linkageGroups.set(config.group, new Set())
    }
    this.linkageGroups.get(config.group)!.add(chart)

    // 监听数据高亮事件
    chart.on('highlight', (params: any) => {
      this.syncHighlight(config.group, chart, params)
    })

    chart.on('downplay', (params: any) => {
      this.syncDownplay(config.group, chart, params)
    })

    // 监听数据缩放事件
    chart.on('datazoom', (params: any) => {
      this.syncDataZoom(config.group, chart, params)
    })
  }

  /**
   * 同步高亮
   */
  private syncHighlight(
    group: string,
    sourceChart: ECharts,
    params: any
  ): void {
    const charts = this.linkageGroups.get(group)
    if (!charts) return

    charts.forEach(chart => {
      if (chart !== sourceChart) {
        chart.dispatchAction({
          type: 'highlight',
          seriesIndex: params.seriesIndex,
          dataIndex: params.dataIndex
        })
      }
    })
  }

  /**
   * 同步取消高亮
   */
  private syncDownplay(
    group: string,
    sourceChart: ECharts,
    params: any
  ): void {
    const charts = this.linkageGroups.get(group)
    if (!charts) return

    charts.forEach(chart => {
      if (chart !== sourceChart) {
        chart.dispatchAction({
          type: 'downplay',
          seriesIndex: params.seriesIndex,
          dataIndex: params.dataIndex
        })
      }
    })
  }

  /**
   * 同步数据缩放
   */
  private syncDataZoom(
    group: string,
    sourceChart: ECharts,
    params: any
  ): void {
    const charts = this.linkageGroups.get(group)
    if (!charts) return

    charts.forEach(chart => {
      if (chart !== sourceChart) {
        chart.dispatchAction({
          type: 'dataZoom',
          start: params.start,
          end: params.end
        })
      }
    })
  }

  /**
   * 移除图表联动
   */
  disableChartLinkage(chart: ECharts, group: string): void {
    const charts = this.linkageGroups.get(group)
    if (charts) {
      charts.delete(chart)
      if (charts.size === 0) {
        this.linkageGroups.delete(group)
      }
    }
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    this.hideContextMenu()
    this.selectedDataPoints.clear()
    this.drillDownStack = []
    this.linkageGroups.clear()
  }
}

// 导出单例实例
export const chartInteractionService = new ChartInteractionService()
