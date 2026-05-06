/**
 * 图表类型智能选择器
 * 根据数据特征自动选择最佳图表类型
 * 支持AI驱动和规则引擎两种模式
 */

import type { ChartData, ChartType, ColumnType } from '@/types/chart'
import { aiChartSelector, type ChartSelectionResponse } from '@/services/aiChartSelector'

export class ChartTypeSelector {
  private useAI: boolean = true
  private userQuestion?: string

  /**
   * 设置是否使用AI模式
   */
  setUseAI(useAI: boolean) {
    this.useAI = useAI
  }

  /**
   * 设置用户问题（用于语义分析）
   */
  setUserQuestion(question: string) {
    this.userQuestion = question
  }

  /**
   * 选择最优图表类型（同步方法，用于向后兼容）
   */
  selectOptimalChart(data: ChartData): ChartType {
    const { columns, rows, metadata } = data
    
    if (!rows || rows.length === 0) {
      return 'bar' // 默认柱状图
    }

    const numericColumns = this.getNumericColumns(columns, metadata)
    const categoricalColumns = this.getCategoricalColumns(columns, metadata)
    const dateColumns = this.getDateColumns(columns, metadata)

    // 时间序列数据优先使用折线图
    if (dateColumns.length > 0 && numericColumns.length > 0) {
      return 'line'
    }

    // 单分类 + 单数值：少量数据用饼图，多数据用柱状图
    if (categoricalColumns.length === 1 && numericColumns.length === 1) {
      if (rows.length <= 10) {
        return 'pie'
      } else {
        return 'bar'
      }
    }

    // 多个数值字段使用散点图
    if (numericColumns.length >= 2 && categoricalColumns.length === 0) {
      return 'scatter'
    }

    // 默认使用柱状图
    return 'bar'
  }

  /**
   * 选择最优图表类型（异步方法，支持AI）
   */
  async selectOptimalChartAsync(data: ChartData, userQuestion?: string): Promise<ChartSelectionResponse> {
    if (this.useAI) {
      try {
        const response = await aiChartSelector.selectChartType({
          data,
          userQuestion: userQuestion || this.userQuestion
        })
        return response
      } catch (error) {
        console.warn('AI chart selection failed, falling back to rule engine:', error)
        // AI失败时降级到规则引擎
        return this.getRuleBasedSelection(data, userQuestion)
      }
    } else {
      // 直接使用规则引擎
      return this.getRuleBasedSelection(data, userQuestion)
    }
  }

  /**
   * 获取基于规则的选择结果
   */
  private getRuleBasedSelection(data: ChartData, userQuestion?: string): ChartSelectionResponse {
    const primaryType = this.selectOptimalChart(data)
    const alternatives = this.getAvailableTypes(data)
      .filter(type => type !== primaryType)
      .slice(0, 2)
      .map(type => ({
        type,
        confidence: 0.7,
        reason: this.getChartTypeReason(type, data)
      }))

    return {
      primary: {
        type: primaryType,
        confidence: 0.85,
        reason: this.getChartTypeReason(primaryType, data)
      },
      alternatives,
      dataAnalysis: {
        numericColumns: this.getNumericColumns(data.columns, data.metadata).length,
        categoricalColumns: this.getCategoricalColumns(data.columns, data.metadata).length,
        dateColumns: this.getDateColumns(data.columns, data.metadata).length,
        rowCount: data.rows.length,
        hasTimeSeries: this.getDateColumns(data.columns, data.metadata).length > 0 &&
                      this.getNumericColumns(data.columns, data.metadata).length > 0
      }
    }
  }

  /**
   * 获取图表类型的推荐理由
   */
  private getChartTypeReason(type: ChartType, data: ChartData): string {
    const reasons: Record<ChartType, string> = {
      bar: '柱状图适合进行数值对比和分类数据展示',
      line: '折线图适合展示趋势变化和时间序列数据',
      pie: '饼图适合展示占比关系和数据分布',
      scatter: '散点图适合展示两个变量之间的相关性',
      heatmap: '热力图适合展示二维数据的分布密度',
      radar: '雷达图适合展示多维度指标的综合对比'
    }
    return reasons[type] || '适合当前数据展示'
  }

  /**
   * 获取可用的图表类型列表
   */
  getAvailableTypes(data: ChartData): ChartType[] {
    const { columns, rows, metadata } = data
    
    if (!rows || rows.length === 0) {
      return ['bar']
    }

    const available: ChartType[] = []
    const numericColumns = this.getNumericColumns(columns, metadata)
    const categoricalColumns = this.getCategoricalColumns(columns, metadata)

    // 柱状图：至少有一个分类列和一个数值列
    if (categoricalColumns.length >= 1 && numericColumns.length >= 1) {
      available.push('bar')
      available.push('line')
    }

    // 饼图：单分类 + 单数值
    if (categoricalColumns.length === 1 && numericColumns.length === 1) {
      available.push('pie')
    }

    // 散点图：至少两个数值列
    if (numericColumns.length >= 2) {
      available.push('scatter')
    }

    // 雷达图：多个数值指标
    if (numericColumns.length >= 3) {
      available.push('radar')
    }

    // 热力图：二维数据
    if (categoricalColumns.length >= 2 && numericColumns.length >= 1) {
      available.push('heatmap')
    }

    return available.length > 0 ? available : ['bar']
  }

  /**
   * 获取数值类型的列索引
   */
  private getNumericColumns(columns: string[], metadata?: ChartData['metadata']): number[] {
    const indices: number[] = []
    
    if (metadata?.columnTypes) {
      metadata.columnTypes.forEach((type, index) => {
        if (type === 'number') {
          indices.push(index)
        }
      })
    } else {
      // 如果没有元数据，尝试从第一行数据推断
      columns.forEach((_, index) => {
        if (index > 0) { // 假设第一列是分类列
          indices.push(index)
        }
      })
    }
    
    return indices
  }

  /**
   * 获取分类类型的列索引
   */
  private getCategoricalColumns(columns: string[], metadata?: ChartData['metadata']): number[] {
    const indices: number[] = []
    
    if (metadata?.columnTypes) {
      metadata.columnTypes.forEach((type, index) => {
        if (type === 'string') {
          indices.push(index)
        }
      })
    } else {
      // 默认第一列是分类列
      if (columns.length > 0) {
        indices.push(0)
      }
    }
    
    return indices
  }

  /**
   * 获取日期类型的列索引
   */
  private getDateColumns(columns: string[], metadata?: ChartData['metadata']): number[] {
    const indices: number[] = []
    
    if (metadata?.columnTypes) {
      metadata.columnTypes.forEach((type, index) => {
        if (type === 'date') {
          indices.push(index)
        }
      })
    }
    
    return indices
  }
}
