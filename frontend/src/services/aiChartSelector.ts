/**
 * AI驱动的图表类型智能选择服务
 * 基于本地OpenAI模型进行图表类型推荐
 */

import type { ChartData, ChartType } from '@/types/chart'

// 图表推荐结果接口
export interface ChartRecommendation {
  type: ChartType
  confidence: number // 置信度 0-1
  reason: string // 推荐理由
}

// 图表选择请求接口
export interface ChartSelectionRequest {
  data: ChartData
  userQuestion?: string // 用户的原始问题（可选）
  context?: string // 额外上下文信息
}

// 图表选择响应接口
export interface ChartSelectionResponse {
  primary: ChartRecommendation // 主要推荐
  alternatives: ChartRecommendation[] // 备选推荐
  dataAnalysis: {
    numericColumns: number
    categoricalColumns: number
    dateColumns: number
    rowCount: number
    hasTimeSeries: boolean
  }
}

/**
 * AI图表选择服务类
 */
export class AIChartSelectorService {
  private apiBaseUrl: string
  private enabled: boolean = true

  constructor(apiBaseUrl: string = '/api') {
    this.apiBaseUrl = apiBaseUrl
  }

  /**
   * 选择最优图表类型（AI驱动）
   */
  async selectChartType(request: ChartSelectionRequest): Promise<ChartSelectionResponse> {
    try {
      // 分析数据特征
      const dataAnalysis = this.analyzeDataFeatures(request.data)

      // 如果AI服务不可用，使用规则引擎降级
      if (!this.enabled) {
        return this.fallbackToRuleEngine(request, dataAnalysis)
      }

      // 调用后端AI服务
      const response = await fetch(`${this.apiBaseUrl}/chart/select-type`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          data_features: dataAnalysis,
          user_question: request.userQuestion,
          context: request.context,
          columns: request.data.columns,
          sample_rows: request.data.rows.slice(0, 5) // 只发送前5行作为样本
        })
      })

      if (!response.ok) {
        console.warn('AI chart selection failed, falling back to rule engine')
        return this.fallbackToRuleEngine(request, dataAnalysis)
      }

      const result = await response.json()
      return this.parseAIResponse(result, dataAnalysis)
    } catch (error) {
      console.error('Error in AI chart selection:', error)
      return this.fallbackToRuleEngine(request, this.analyzeDataFeatures(request.data))
    }
  }

  /**
   * 分析数据特征
   */
  private analyzeDataFeatures(data: ChartData) {
    const { columns, rows, metadata } = data

    let numericColumns = 0
    let categoricalColumns = 0
    let dateColumns = 0

    if (metadata?.columnTypes) {
      metadata.columnTypes.forEach(type => {
        if (type === 'number') numericColumns++
        else if (type === 'date') dateColumns++
        else if (type === 'string') categoricalColumns++
      })
    } else {
      // 从数据推断类型
      if (rows.length > 0) {
        columns.forEach((_, index) => {
          const sampleValue = rows[0][index]
          if (typeof sampleValue === 'number') {
            numericColumns++
          } else if (this.isDateString(sampleValue)) {
            dateColumns++
          } else {
            categoricalColumns++
          }
        })
      }
    }

    return {
      numericColumns,
      categoricalColumns,
      dateColumns,
      rowCount: rows.length,
      hasTimeSeries: dateColumns > 0 && numericColumns > 0
    }
  }

  /**
   * 解析AI响应
   */
  private parseAIResponse(aiResult: any, dataAnalysis: any): ChartSelectionResponse {
    return {
      primary: {
        type: aiResult.primary_type || 'bar',
        confidence: aiResult.primary_confidence || 0.8,
        reason: aiResult.primary_reason || '基于数据特征的推荐'
      },
      alternatives: (aiResult.alternatives || []).map((alt: any) => ({
        type: alt.type,
        confidence: alt.confidence,
        reason: alt.reason
      })),
      dataAnalysis
    }
  }

  /**
   * 降级到规则引擎
   */
  private fallbackToRuleEngine(
    request: ChartSelectionRequest,
    dataAnalysis: any
  ): ChartSelectionResponse {
    const { data } = request
    const { numericColumns, categoricalColumns, dateColumns, rowCount, hasTimeSeries } = dataAnalysis

    let primaryType: ChartType = 'bar'
    let primaryReason = '默认柱状图'
    let alternatives: ChartRecommendation[] = []

    // 规则1: 时间序列数据优先使用折线图
    if (hasTimeSeries) {
      primaryType = 'line'
      primaryReason = '检测到时间序列数据，折线图最适合展示趋势变化'
      alternatives.push({
        type: 'bar',
        confidence: 0.7,
        reason: '柱状图也可以展示时间序列数据'
      })
    }
    // 规则2: 单分类 + 单数值，少量数据用饼图
    else if (categoricalColumns === 1 && numericColumns === 1 && rowCount <= 10) {
      primaryType = 'pie'
      primaryReason = '数据量较少且为单一分类，饼图最适合展示占比关系'
      alternatives.push({
        type: 'bar',
        confidence: 0.75,
        reason: '柱状图可以更精确地比较数值大小'
      })
    }
    // 规则3: 多个数值字段使用散点图
    else if (numericColumns >= 2 && categoricalColumns === 0) {
      primaryType = 'scatter'
      primaryReason = '多个数值字段，散点图最适合展示相关性'
      alternatives.push({
        type: 'line',
        confidence: 0.6,
        reason: '折线图可以展示数值变化趋势'
      })
    }
    // 规则4: 多个数值指标使用雷达图
    else if (numericColumns >= 3 && categoricalColumns === 1) {
      primaryType = 'radar'
      primaryReason = '多个数值指标，雷达图最适合展示多维度对比'
      alternatives.push({
        type: 'bar',
        confidence: 0.7,
        reason: '柱状图可以更直观地比较各指标'
      })
    }
    // 规则5: 二维分类数据使用热力图
    else if (categoricalColumns >= 2 && numericColumns >= 1) {
      primaryType = 'heatmap'
      primaryReason = '二维分类数据，热力图最适合展示分布密度'
      alternatives.push({
        type: 'bar',
        confidence: 0.65,
        reason: '柱状图可以展示分类数据的数值对比'
      })
    }
    // 默认: 柱状图
    else {
      primaryType = 'bar'
      primaryReason = '通用数据展示，柱状图最适合进行数值对比'
      alternatives.push(
        {
          type: 'line',
          confidence: 0.7,
          reason: '折线图可以展示数据的连续性'
        },
        {
          type: 'pie',
          confidence: 0.5,
          reason: '如果关注占比关系，可以使用饼图'
        }
      )
    }

    // 基于用户问题语义调整推荐
    if (request.userQuestion) {
      const question = request.userQuestion.toLowerCase()
      
      if (question.includes('趋势') || question.includes('变化') || question.includes('增长')) {
        primaryType = 'line'
        primaryReason = '用户关注趋势变化，折线图最适合'
      } else if (question.includes('占比') || question.includes('比例') || question.includes('份额')) {
        primaryType = 'pie'
        primaryReason = '用户关注占比关系，饼图最适合'
      } else if (question.includes('对比') || question.includes('比较')) {
        primaryType = 'bar'
        primaryReason = '用户关注数值对比，柱状图最适合'
      } else if (question.includes('分布') || question.includes('密度')) {
        primaryType = 'heatmap'
        primaryReason = '用户关注数据分布，热力图最适合'
      } else if (question.includes('相关') || question.includes('关系')) {
        primaryType = 'scatter'
        primaryReason = '用户关注相关性，散点图最适合'
      }
    }

    return {
      primary: {
        type: primaryType,
        confidence: 0.85,
        reason: primaryReason
      },
      alternatives: alternatives.slice(0, 2), // 最多返回2个备选
      dataAnalysis
    }
  }

  /**
   * 判断是否为日期字符串
   */
  private isDateString(value: any): boolean {
    if (typeof value !== 'string') return false
    
    // 简单的日期格式检测
    const datePatterns = [
      /^\d{4}-\d{2}-\d{2}/, // YYYY-MM-DD
      /^\d{4}\/\d{2}\/\d{2}/, // YYYY/MM/DD
      /^\d{2}-\d{2}-\d{4}/, // DD-MM-YYYY
      /^\d{2}\/\d{2}\/\d{4}/ // DD/MM/YYYY
    ]
    
    return datePatterns.some(pattern => pattern.test(value))
  }

  /**
   * 启用/禁用AI服务
   */
  setEnabled(enabled: boolean) {
    this.enabled = enabled
  }

  /**
   * 检查AI服务是否可用
   */
  async checkAvailability(): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/chart/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      return response.ok
    } catch {
      return false
    }
  }
}

// 导出单例实例
export const aiChartSelector = new AIChartSelectorService()
