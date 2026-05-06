/**
 * 图表智能解读服务
 * 基于本地OpenAI模型实现图表数据的智能解读和洞察生成
 */

import type { ChartData, ChartType } from '@/types/chart'

/**
 * 数据洞察类型
 */
export interface DataInsight {
  type: 'trend' | 'anomaly' | 'pattern' | 'correlation' | 'summary'
  title: string
  description: string
  confidence: number // 0-1
  data?: any
}

/**
 * 趋势分析结果
 */
export interface TrendAnalysis {
  direction: 'increasing' | 'decreasing' | 'stable' | 'fluctuating'
  strength: number // 0-1
  description: string
  predictions?: number[]
}

/**
 * 异常检测结果
 */
export interface AnomalyDetection {
  anomalies: Array<{
    index: number
    value: number
    severity: 'low' | 'medium' | 'high'
    reason: string
  }>
  summary: string
}

/**
 * 对比分析结果
 */
export interface ComparisonAnalysis {
  differences: Array<{
    dimension: string
    change: number
    changePercent: number
    significance: 'low' | 'medium' | 'high'
  }>
  summary: string
  insights: string[]
}

/**
 * 图表解读结果
 */
export interface ChartInterpretation {
  naturalLanguageDescription: string
  businessMeaning: string
  insights: DataInsight[]
  trendAnalysis?: TrendAnalysis
  anomalyDetection?: AnomalyDetection
  recommendations: string[]
}

/**
 * 图表智能解读服务类
 */
export class ChartInsightService {
  private apiEndpoint: string

  constructor(apiEndpoint: string = '/api/local-data-analyzer') {
    this.apiEndpoint = apiEndpoint
  }

  /**
   * 生成图表的智能解读
   */
  async generateInsights(
    chartType: ChartType,
    chartData: ChartData,
    context?: {
      question?: string
      previousData?: ChartData
      businessContext?: string
    }
  ): Promise<ChartInterpretation> {
    try {
      // 调用本地OpenAI模型API进行智能解读
      const response = await fetch(`${this.apiEndpoint}/analyze-chart`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chart_type: chartType,
          chart_data: chartData,
          context
        })
      })

      if (!response.ok) {
        throw new Error(`API请求失败: ${response.statusText}`)
      }

      const result = await response.json()
      return result.interpretation
    } catch (error) {
      console.error('生成图表洞察失败:', error)
      // 降级到规则引擎
      return this.generateInsightsWithRules(chartType, chartData, context)
    }
  }

  /**
   * 基于规则引擎生成图表洞察（降级方案）
   */
  private generateInsightsWithRules(
    chartType: ChartType,
    chartData: ChartData,
    context?: {
      question?: string
      previousData?: ChartData
      businessContext?: string
    }
  ): ChartInterpretation {
    const insights: DataInsight[] = []
    let trendAnalysis: TrendAnalysis | undefined
    let anomalyDetection: AnomalyDetection | undefined

    // 提取数值数据
    const numericValues = this.extractNumericValues(chartData)

    // 趋势分析
    if (numericValues.length > 2) {
      trendAnalysis = this.analyzeTrend(numericValues)
      insights.push({
        type: 'trend',
        title: '趋势分析',
        description: trendAnalysis.description,
        confidence: trendAnalysis.strength
      })
    }

    // 异常检测
    if (numericValues.length > 5) {
      anomalyDetection = this.detectAnomalies(numericValues)
      if (anomalyDetection.anomalies.length > 0) {
        insights.push({
          type: 'anomaly',
          title: '异常检测',
          description: anomalyDetection.summary,
          confidence: 0.8,
          data: anomalyDetection.anomalies
        })
      }
    }

    // 模式识别
    const patterns = this.detectPatterns(numericValues)
    if (patterns.length > 0) {
      patterns.forEach(pattern => {
        insights.push({
          type: 'pattern',
          title: '数据模式',
          description: pattern,
          confidence: 0.7
        })
      })
    }

    // 生成自然语言描述
    const naturalLanguageDescription = this.generateNaturalLanguageDescription(
      chartType,
      chartData,
      numericValues
    )

    // 生成业务含义
    const businessMeaning = this.generateBusinessMeaning(
      chartType,
      insights,
      context?.businessContext
    )

    // 生成建议
    const recommendations = this.generateRecommendations(insights, trendAnalysis)

    return {
      naturalLanguageDescription,
      businessMeaning,
      insights,
      trendAnalysis,
      anomalyDetection,
      recommendations
    }
  }

  /**
   * 分析两个图表数据的对比
   */
  async compareCharts(
    chartData1: ChartData,
    chartData2: ChartData,
    context?: {
      dimension?: string
      businessContext?: string
    }
  ): Promise<ComparisonAnalysis> {
    try {
      const response = await fetch(`${this.apiEndpoint}/compare-charts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chart_data_1: chartData1,
          chart_data_2: chartData2,
          context
        })
      })

      if (!response.ok) {
        throw new Error(`API请求失败: ${response.statusText}`)
      }

      const result = await response.json()
      return result.comparison
    } catch (error) {
      console.error('对比分析失败:', error)
      // 降级到规则引擎
      return this.compareChartsWithRules(chartData1, chartData2, context)
    }
  }

  /**
   * 基于规则引擎进行对比分析（降级方案）
   */
  private compareChartsWithRules(
    chartData1: ChartData,
    chartData2: ChartData,
    context?: {
      dimension?: string
      businessContext?: string
    }
  ): ComparisonAnalysis {
    const values1 = this.extractNumericValues(chartData1)
    const values2 = this.extractNumericValues(chartData2)

    const differences: ComparisonAnalysis['differences'] = []
    const insights: string[] = []

    // 计算总体变化
    const sum1 = values1.reduce((a, b) => a + b, 0)
    const sum2 = values2.reduce((a, b) => a + b, 0)
    const totalChange = sum2 - sum1
    const totalChangePercent = sum1 !== 0 ? (totalChange / sum1) * 100 : 0

    differences.push({
      dimension: '总体',
      change: totalChange,
      changePercent: totalChangePercent,
      significance: Math.abs(totalChangePercent) > 20 ? 'high' : Math.abs(totalChangePercent) > 10 ? 'medium' : 'low'
    })

    // 生成洞察
    if (Math.abs(totalChangePercent) > 20) {
      insights.push(`数据整体${totalChangePercent > 0 ? '增长' : '下降'}显著，变化幅度达到${Math.abs(totalChangePercent).toFixed(1)}%`)
    }

    // 计算平均值变化
    const avg1 = sum1 / values1.length
    const avg2 = sum2 / values2.length
    const avgChange = avg2 - avg1
    const avgChangePercent = avg1 !== 0 ? (avgChange / avg1) * 100 : 0

    differences.push({
      dimension: '平均值',
      change: avgChange,
      changePercent: avgChangePercent,
      significance: Math.abs(avgChangePercent) > 15 ? 'high' : Math.abs(avgChangePercent) > 5 ? 'medium' : 'low'
    })

    // 生成摘要
    const summary = `对比分析显示，数据整体${totalChangePercent > 0 ? '增长' : '下降'}${Math.abs(totalChangePercent).toFixed(1)}%，平均值${avgChangePercent > 0 ? '上升' : '下降'}${Math.abs(avgChangePercent).toFixed(1)}%。`

    return {
      differences,
      summary,
      insights
    }
  }

  /**
   * 提取数值数据
   */
  private extractNumericValues(chartData: ChartData): number[] {
    const values: number[] = []

    if (chartData.datasets && chartData.datasets.length > 0) {
      chartData.datasets.forEach(dataset => {
        if (Array.isArray(dataset.data)) {
          dataset.data.forEach(value => {
            if (typeof value === 'number') {
              values.push(value)
            }
          })
        }
      })
    }

    return values
  }

  /**
   * 趋势分析
   */
  private analyzeTrend(values: number[]): TrendAnalysis {
    if (values.length < 2) {
      return {
        direction: 'stable',
        strength: 0,
        description: '数据点不足，无法分析趋势'
      }
    }

    // 计算线性回归
    const n = values.length
    const sumX = (n * (n - 1)) / 2
    const sumY = values.reduce((a, b) => a + b, 0)
    const sumXY = values.reduce((sum, y, x) => sum + x * y, 0)
    const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
    const intercept = (sumY - slope * sumX) / n

    // 计算R²
    const yMean = sumY / n
    const ssTotal = values.reduce((sum, y) => sum + Math.pow(y - yMean, 2), 0)
    const ssResidual = values.reduce((sum, y, x) => sum + Math.pow(y - (slope * x + intercept), 2), 0)
    const r2 = 1 - ssResidual / ssTotal

    // 判断波动性
    const volatility = Math.sqrt(values.reduce((sum, v, i) => {
      if (i === 0) return 0
      return sum + Math.pow(v - values[i - 1], 2)
    }, 0) / (n - 1))

    // 判断趋势方向
    let direction: TrendAnalysis['direction']
    
    // 如果波动性很大，标记为波动
    if (volatility > yMean * 0.2) {
      direction = 'fluctuating'
    } else if (Math.abs(slope) < yMean * 0.02) {
      // 斜率很小，标记为稳定
      direction = 'stable'
    } else if (slope > 0) {
      direction = 'increasing'
    } else {
      direction = 'decreasing'
    }

    // 生成描述
    let description = ''
    if (direction === 'increasing') {
      description = `数据呈现上升趋势，增长率约为${(slope / yMean * 100).toFixed(1)}%`
    } else if (direction === 'decreasing') {
      description = `数据呈现下降趋势，下降率约为${Math.abs(slope / yMean * 100).toFixed(1)}%`
    } else if (direction === 'fluctuating') {
      description = '数据波动较大，未呈现明显趋势'
    } else {
      description = '数据保持相对稳定'
    }

    return {
      direction,
      strength: Math.abs(r2),
      description
    }
  }

  /**
   * 异常检测（基于Z-score）
   */
  private detectAnomalies(values: number[]): AnomalyDetection {
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const stdDev = Math.sqrt(
      values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length
    )

    const anomalies: AnomalyDetection['anomalies'] = []

    values.forEach((value, index) => {
      const zScore = Math.abs((value - mean) / stdDev)

      if (zScore > 3) {
        anomalies.push({
          index,
          value,
          severity: 'high',
          reason: `数值偏离平均值${zScore.toFixed(1)}个标准差`
        })
      } else if (zScore > 2) {
        anomalies.push({
          index,
          value,
          severity: 'medium',
          reason: `数值偏离平均值${zScore.toFixed(1)}个标准差`
        })
      }
    })

    const summary = anomalies.length > 0
      ? `检测到${anomalies.length}个异常数据点`
      : '未检测到明显异常'

    return {
      anomalies,
      summary
    }
  }

  /**
   * 模式识别
   */
  private detectPatterns(values: number[]): string[] {
    const patterns: string[] = []

    if (values.length < 3) return patterns

    // 检测周期性
    const isPeriodic = this.checkPeriodicity(values)
    if (isPeriodic) {
      patterns.push('数据呈现周期性变化模式')
    }

    // 检测季节性
    if (values.length >= 12) {
      const isSeasonality = this.checkSeasonality(values)
      if (isSeasonality) {
        patterns.push('数据可能存在季节性特征')
      }
    }

    // 检测集中度（降低阈值）
    const concentration = this.checkConcentration(values)
    if (concentration > 0.6) {
      patterns.push('数据高度集中在某些值附近')
    }

    return patterns
  }

  /**
   * 检测周期性
   */
  private checkPeriodicity(values: number[]): boolean {
    // 简化的周期性检测
    const n = values.length
    if (n < 6) return false

    // 检测是否存在重复模式
    for (let period = 2; period <= Math.floor(n / 2); period++) {
      let matches = 0
      for (let i = 0; i < n - period; i++) {
        if (Math.abs(values[i] - values[i + period]) < values[i] * 0.1) {
          matches++
        }
      }
      if (matches / (n - period) > 0.7) {
        return true
      }
    }

    return false
  }

  /**
   * 检测季节性
   */
  private checkSeasonality(values: number[]): boolean {
    // 简化的季节性检测（假设月度数据）
    const n = values.length
    if (n < 12) return false

    const quarters = [0, 0, 0, 0]
    const counts = [0, 0, 0, 0]

    values.forEach((value, index) => {
      const quarter = Math.floor((index % 12) / 3)
      quarters[quarter] += value
      counts[quarter]++
    })

    const avgQuarters = quarters.map((sum, i) => sum / counts[i])
    const overallAvg = values.reduce((a, b) => a + b, 0) / n

    // 检查季度平均值是否有显著差异
    const maxDiff = Math.max(...avgQuarters.map(avg => Math.abs(avg - overallAvg)))
    return maxDiff > overallAvg * 0.2
  }

  /**
   * 检测数据集中度
   */
  private checkConcentration(values: number[]): number {
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const stdDev = Math.sqrt(
      values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length
    )

    const withinOneStdDev = values.filter(v => Math.abs(v - mean) <= stdDev).length
    return withinOneStdDev / values.length
  }

  /**
   * 生成自然语言描述
   */
  private generateNaturalLanguageDescription(
    chartType: ChartType,
    chartData: ChartData,
    values: number[]
  ): string {
    if (values.length === 0) {
      return '图表暂无数据'
    }

    const sum = values.reduce((a, b) => a + b, 0)
    const avg = sum / values.length
    const max = Math.max(...values)
    const min = Math.min(...values)

    let description = ''

    switch (chartType) {
      case 'bar':
      case 'line':
        description = `该${chartType === 'bar' ? '柱状' : '折线'}图展示了${chartData.labels?.length || values.length}个数据点，`
        description += `数值范围从${min.toFixed(2)}到${max.toFixed(2)}，平均值为${avg.toFixed(2)}。`
        break
      case 'pie':
        description = `该饼图展示了数据的分布情况，共${values.length}个类别，`
        description += `最大占比为${((max / sum) * 100).toFixed(1)}%，最小占比为${((min / sum) * 100).toFixed(1)}%。`
        break
      case 'scatter':
        description = `该散点图展示了${values.length}个数据点的分布，`
        description += `数值范围从${min.toFixed(2)}到${max.toFixed(2)}。`
        break
      default:
        description = `该图表展示了${values.length}个数据点，平均值为${avg.toFixed(2)}。`
    }

    return description
  }

  /**
   * 生成业务含义
   */
  private generateBusinessMeaning(
    chartType: ChartType,
    insights: DataInsight[],
    businessContext?: string
  ): string {
    let meaning = ''

    if (businessContext) {
      meaning += `在${businessContext}的背景下，`
    }

    const trendInsight = insights.find(i => i.type === 'trend')
    const anomalyInsight = insights.find(i => i.type === 'anomaly')

    if (trendInsight) {
      meaning += trendInsight.description + '。'
    }

    if (anomalyInsight) {
      meaning += anomalyInsight.description + '，需要关注。'
    }

    if (!trendInsight && !anomalyInsight) {
      meaning += '数据整体表现正常，未发现明显异常。'
    }

    return meaning
  }

  /**
   * 生成建议
   */
  private generateRecommendations(
    insights: DataInsight[],
    trendAnalysis?: TrendAnalysis
  ): string[] {
    const recommendations: string[] = []

    // 基于趋势的建议
    if (trendAnalysis) {
      if (trendAnalysis.direction === 'increasing' && trendAnalysis.strength > 0.7) {
        recommendations.push('数据呈现强劲增长趋势，建议继续保持当前策略')
      } else if (trendAnalysis.direction === 'decreasing' && trendAnalysis.strength > 0.7) {
        recommendations.push('数据呈现下降趋势，建议分析原因并采取改进措施')
      } else if (trendAnalysis.direction === 'fluctuating') {
        recommendations.push('数据波动较大，建议进一步分析波动原因，寻找稳定因素')
      }
    }

    // 基于异常的建议
    const anomalyInsight = insights.find(i => i.type === 'anomaly')
    if (anomalyInsight) {
      if (anomalyInsight.data && Array.isArray(anomalyInsight.data)) {
        const highSeverityCount = anomalyInsight.data.filter((a: any) => a.severity === 'high').length
        if (highSeverityCount > 0) {
          recommendations.push(`发现${highSeverityCount}个高严重性异常，建议优先调查这些数据点`)
        } else if (anomalyInsight.data.length > 0) {
          recommendations.push(`发现${anomalyInsight.data.length}个异常数据点，建议进行调查`)
        }
      }
    }

    // 基于模式的建议
    const patternInsight = insights.find(i => i.type === 'pattern')
    if (patternInsight) {
      recommendations.push('数据呈现特定模式，建议利用这些模式进行预测和优化')
    }

    if (recommendations.length === 0) {
      recommendations.push('数据表现正常，建议持续监控关键指标')
    }

    return recommendations
  }
}

// 导出单例实例
export const chartInsightService = new ChartInsightService()
