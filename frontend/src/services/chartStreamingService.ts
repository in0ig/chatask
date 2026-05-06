/**
 * 图表流式渲染服务
 * 
 * 功能：
 * 1. 流式数据渲染 - 数据逐步显示
 * 2. 增量更新 - 支持数据增量添加
 * 3. 性能优化 - 大数据量处理
 * 4. 加载动画 - 优雅的过渡效果
 */

import type { EChartsOption } from 'echarts'

/**
 * 流式渲染配置
 */
export interface StreamingConfig {
  /** 是否启用流式渲染 */
  enabled: boolean
  /** 每批次渲染的数据点数量 */
  batchSize: number
  /** 批次间隔时间（毫秒） */
  batchInterval: number
  /** 是否显示加载动画 */
  showLoadingAnimation: boolean
  /** 是否启用增量更新 */
  enableIncrementalUpdate: boolean
  /** 大数据量阈值（超过此值启用优化） */
  largeDataThreshold: number
}

/**
 * 流式渲染状态
 */
export interface StreamingState {
  /** 是否正在渲染 */
  isStreaming: boolean
  /** 当前已渲染的数据点数量 */
  renderedCount: number
  /** 总数据点数量 */
  totalCount: number
  /** 渲染进度（0-100） */
  progress: number
}

/**
 * 数据批次
 */
interface DataBatch {
  /** 批次索引 */
  index: number
  /** 批次数据 */
  data: any[]
  /** 是否为最后一批 */
  isLast: boolean
}

/**
 * 图表流式渲染服务类
 */
export class ChartStreamingService {
  private config: StreamingConfig
  private state: StreamingState
  private streamingTimers: Map<string, number>
  private dataBuffers: Map<string, any[]>

  constructor() {
    this.config = {
      enabled: true,
      batchSize: 50,
      batchInterval: 100,
      showLoadingAnimation: true,
      enableIncrementalUpdate: true,
      largeDataThreshold: 1000
    }

    this.state = {
      isStreaming: false,
      renderedCount: 0,
      totalCount: 0,
      progress: 0
    }

    this.streamingTimers = new Map()
    this.dataBuffers = new Map()
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<StreamingConfig>): void {
    this.config = { ...this.config, ...config }
  }

  /**
   * 获取当前配置
   */
  getConfig(): StreamingConfig {
    return { ...this.config }
  }

  /**
   * 获取当前状态
   */
  getState(): StreamingState {
    return { ...this.state }
  }

  /**
   * 判断是否需要流式渲染
   */
  shouldUseStreaming(dataCount: number): boolean {
    return this.config.enabled && dataCount > this.config.batchSize
  }

  /**
   * 判断是否为大数据量
   */
  isLargeDataset(dataCount: number): boolean {
    return dataCount > this.config.largeDataThreshold
  }

  /**
   * 将数据分批
   */
  private splitIntoBatches(data: any[]): DataBatch[] {
    const batches: DataBatch[] = []
    const batchSize = this.config.batchSize
    const totalBatches = Math.ceil(data.length / batchSize)

    for (let i = 0; i < totalBatches; i++) {
      const start = i * batchSize
      const end = Math.min(start + batchSize, data.length)
      batches.push({
        index: i,
        data: data.slice(start, end),
        isLast: i === totalBatches - 1
      })
    }

    return batches
  }

  /**
   * 流式渲染数据
   */
  async streamData(
    chartId: string,
    data: any[],
    onBatchRender: (batch: DataBatch, accumulatedData: any[]) => void,
    onComplete?: () => void
  ): Promise<void> {
    // 停止之前的流式渲染
    this.stopStreaming(chartId)

    // 更新状态
    this.state = {
      isStreaming: true,
      renderedCount: 0,
      totalCount: data.length,
      progress: 0
    }

    // 初始化数据缓冲区
    this.dataBuffers.set(chartId, [])

    // 分批数据
    const batches = this.splitIntoBatches(data)

    // 逐批渲染
    return new Promise((resolve) => {
      let currentBatchIndex = 0

      const renderNextBatch = () => {
        if (currentBatchIndex >= batches.length) {
          // 渲染完成
          this.state.isStreaming = false
          this.state.progress = 100
          this.streamingTimers.delete(chartId)
          onComplete?.()
          resolve()
          return
        }

        const batch = batches[currentBatchIndex]
        const buffer = this.dataBuffers.get(chartId) || []
        
        // 累积数据
        buffer.push(...batch.data)
        this.dataBuffers.set(chartId, buffer)

        // 更新状态
        this.state.renderedCount = buffer.length
        this.state.progress = Math.round((buffer.length / data.length) * 100)

        // 渲染当前批次
        onBatchRender(batch, [...buffer])

        currentBatchIndex++

        // 调度下一批次
        const timer = window.setTimeout(renderNextBatch, this.config.batchInterval)
        this.streamingTimers.set(chartId, timer)
      }

      // 开始渲染
      renderNextBatch()
    })
  }

  /**
   * 停止流式渲染
   */
  stopStreaming(chartId: string): void {
    const timer = this.streamingTimers.get(chartId)
    if (timer) {
      clearTimeout(timer)
      this.streamingTimers.delete(chartId)
    }
    this.dataBuffers.delete(chartId)
    this.state.isStreaming = false
  }

  /**
   * 增量更新数据
   */
  incrementalUpdate(
    chartId: string,
    newData: any[],
    existingData: any[]
  ): any[] {
    if (!this.config.enableIncrementalUpdate) {
      return newData
    }

    // 合并数据
    const merged = [...existingData, ...newData]

    // 更新缓冲区
    this.dataBuffers.set(chartId, merged)

    return merged
  }

  /**
   * 优化大数据量图表配置
   */
  optimizeForLargeDataset(option: EChartsOption, dataCount: number): EChartsOption {
    if (!this.isLargeDataset(dataCount)) {
      return option
    }

    // 优化配置
    const optimized: EChartsOption = {
      ...option,
      animation: false, // 禁用动画以提升性能
      progressive: 1000, // 渐进式渲染
      progressiveThreshold: 3000, // 渐进式渲染阈值
      progressiveChunkMode: 'sequential', // 渐进式渲染模式
      large: true, // 大数据量模式
      largeThreshold: this.config.largeDataThreshold // 大数据量阈值
    }

    // 优化系列配置
    if (Array.isArray(optimized.series)) {
      optimized.series = optimized.series.map((series: any) => ({
        ...series,
        large: true,
        largeThreshold: this.config.largeDataThreshold,
        progressive: 1000,
        progressiveThreshold: 3000,
        // 禁用标签以提升性能
        label: {
          ...series.label,
          show: false
        },
        // 简化线条样式
        lineStyle: {
          ...series.lineStyle,
          width: 1
        },
        // 简化符号
        symbol: 'none'
      }))
    }

    return optimized
  }

  /**
   * 数据采样（用于大数据量降采样）
   */
  sampleData(data: any[], targetSize: number): any[] {
    if (data.length <= targetSize) {
      return data
    }

    const step = data.length / targetSize
    const sampled: any[] = []

    for (let i = 0; i < targetSize; i++) {
      const index = Math.floor(i * step)
      sampled.push(data[index])
    }

    return sampled
  }

  /**
   * 获取加载动画配置
   */
  getLoadingAnimation(): {
    text: string
    color: string
    textColor: string
    maskColor: string
    zlevel: number
  } {
    return {
      text: '数据加载中...',
      color: '#409EFF',
      textColor: '#000',
      maskColor: 'rgba(255, 255, 255, 0.8)',
      zlevel: 0
    }
  }

  /**
   * 清理资源
   */
  cleanup(chartId?: string): void {
    if (chartId) {
      this.stopStreaming(chartId)
    } else {
      // 清理所有
      this.streamingTimers.forEach((timer) => clearTimeout(timer))
      this.streamingTimers.clear()
      this.dataBuffers.clear()
      this.state = {
        isStreaming: false,
        renderedCount: 0,
        totalCount: 0,
        progress: 0
      }
    }
  }
}

// 导出单例实例
export const chartStreamingService = new ChartStreamingService()
