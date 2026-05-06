/**
 * 图表类型定义
 */

// 支持的图表类型
export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'radar' | 'combo'

// 图表主题
export type ChartTheme = 'light' | 'dark' | 'business' | 'tech' | 'elegant' | 'vibrant' | string

// 导出格式
export type ExportFormat = 'png' | 'jpg' | 'pdf' | 'svg' | 'excel'

// 列数据类型
export type ColumnType = 'string' | 'number' | 'date'

// 图表数据接口
export interface ChartData {
  columns: string[] // 列名
  rows: any[][] // 数据行
  metadata?: {
    columnTypes?: ColumnType[] // 列类型
    aggregations?: Record<string, 'sum' | 'avg' | 'count' | 'max' | 'min'>
  }
  title?: string // 图表标题
}

// 图表配置选项
export interface ChartOptions {
  width?: string | number
  height?: string | number
  showToolbar?: boolean
  showLegend?: boolean
  showTooltip?: boolean
  showToolbox?: boolean // 是否显示ECharts工具栏
  enableDataZoom?: boolean // 是否启用数据缩放
  animation?: boolean
  animationPreset?: 'smooth' | 'bounce' | 'elastic' | 'fade' | 'zoom' | 'slide' // 动画预设
  animationDuration?: number // 动画持续时间
  animationEasing?: string // 动画缓动函数
  // 交互功能配置
  enableContextMenu?: boolean // 是否启用上下文菜单
  enableDataPointSelection?: boolean // 是否启用数据点选择
  enableDrillDown?: boolean // 是否启用钻取
  enableChartLinkage?: boolean // 是否启用图表联动
  linkageGroup?: string // 联动组名称
  // 流式渲染配置
  enableStreamingUpdate?: boolean // 是否启用流式更新
  streamChunkSize?: number // 流式更新块大小
  streamInterval?: number // 流式更新间隔(ms)
  // 性能优化配置
  enablePerformanceOptimization?: boolean // 是否启用性能优化
  maxDataPoints?: number // 最大数据点数
  samplingStrategy?: 'none' | 'uniform' | 'lttb' | 'adaptive' // 采样策略
  showLoadingOnUpdate?: boolean // 更新时是否显示加载动画
  [key: string]: any
}

// SmartChart 组件属性
export interface SmartChartProps {
  type?: ChartType | 'auto' // 图表类型，auto 为自动识别
  data: ChartData // 图表数据
  options?: ChartOptions // 自定义配置
  theme?: ChartTheme // 主题
  responsive?: boolean // 是否响应式
  exportable?: boolean // 是否支持导出
}

// 图表配置保存/加载
export interface ChartConfig {
  id?: string
  name: string
  type: ChartType
  data: ChartData
  options: ChartOptions
  theme: ChartTheme
  createdAt?: Date
  updatedAt?: Date
}

// 图表模板
export interface ChartTemplate {
  id: string
  name: string
  description?: string
  type: ChartType
  options: ChartOptions
  theme: ChartTheme
  preview?: string // 预览图URL
  category?: string
  tags?: string[]
}

// 分享配置
export interface ShareConfig {
  chartId: string
  shareUrl: string
  embedCode: string
  expiresAt?: Date
  accessCount?: number
}

// 批量导出配置
export interface BatchExportConfig {
  charts: ChartConfig[]
  format: ExportFormat
  filename?: string
  includeData?: boolean
}
