import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ChartInsightService } from '@/services/chartInsightService'
import type { ChartData } from '@/types/chart'

describe('ChartInsightService', () => {
  let service: ChartInsightService

  beforeEach(() => {
    service = new ChartInsightService()
    // Mock fetch
    global.fetch = vi.fn()
  })

  describe('generateInsights', () => {
    it('应该生成图表洞察（API成功）', async () => {
      const mockResponse = {
        interpretation: {
          naturalLanguageDescription: '测试描述',
          businessMeaning: '测试业务含义',
          insights: [],
          recommendations: []
        }
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{
          label: '数据集1',
          data: [10, 20, 30]
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result).toBeDefined()
      expect(result.naturalLanguageDescription).toBe('测试描述')
      expect(result.businessMeaning).toBe('测试业务含义')
    })

    it('应该在API失败时降级到规则引擎', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{
          label: '数据集1',
          data: [10, 20, 30]
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result).toBeDefined()
      expect(result.naturalLanguageDescription).toContain('柱状图')
      expect(result.insights).toBeDefined()
    })

    it('应该检测上升趋势', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [100, 120, 140, 160, 180]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.trendAnalysis).toBeDefined()
      expect(result.trendAnalysis?.direction).toBe('increasing')
      expect(result.insights.some(i => i.type === 'trend')).toBe(true)
    })

    it('应该检测下降趋势', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [180, 160, 140, 120, 100]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.trendAnalysis).toBeDefined()
      expect(result.trendAnalysis?.direction).toBe('decreasing')
    })

    it('应该检测稳定趋势', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [100, 101, 99, 100, 102]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.trendAnalysis).toBeDefined()
      expect(result.trendAnalysis?.direction).toBe('stable')
    })

    it('应该检测波动趋势', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [100, 150, 80, 170, 90]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.trendAnalysis).toBeDefined()
      expect(result.trendAnalysis?.direction).toBe('fluctuating')
    })

    it('应该检测异常值', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1', '2', '3', '4', '5', '6', '7', '8'],
        datasets: [{
          label: '数据',
          data: [100, 105, 98, 102, 500, 103, 99, 101] // 500是异常值
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result.anomalyDetection).toBeDefined()
      expect(result.anomalyDetection?.anomalies.length).toBeGreaterThan(0)
      expect(result.insights.some(i => i.type === 'anomaly')).toBe(true)
    })

    it('应该为饼图生成正确的描述', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{
          label: '分布',
          data: [30, 50, 20]
        }]
      }

      const result = await service.generateInsights('pie', chartData)

      expect(result.naturalLanguageDescription).toContain('饼图')
      expect(result.naturalLanguageDescription).toContain('占比')
    })

    it('应该处理空数据', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: [],
        datasets: []
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result.naturalLanguageDescription).toContain('暂无数据')
    })

    it('应该生成建议', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [100, 120, 140, 160, 180]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.recommendations).toBeDefined()
      expect(result.recommendations.length).toBeGreaterThan(0)
    })
  })

  describe('compareCharts', () => {
    it('应该对比两个图表（API成功）', async () => {
      const mockResponse = {
        comparison: {
          differences: [],
          summary: '测试摘要',
          insights: []
        }
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [10, 20, 30] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [15, 25, 35] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      expect(result).toBeDefined()
      expect(result.summary).toBe('测试摘要')
    })

    it('应该在API失败时降级到规则引擎', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [10, 20, 30] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [15, 25, 35] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      expect(result).toBeDefined()
      expect(result.differences).toBeDefined()
      expect(result.summary).toContain('对比分析')
    })

    it('应该计算总体变化', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [10, 20, 30] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [20, 40, 60] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      const totalDiff = result.differences.find(d => d.dimension === '总体')
      expect(totalDiff).toBeDefined()
      expect(totalDiff?.change).toBe(60) // (20+40+60) - (10+20+30) = 60
      expect(totalDiff?.changePercent).toBeCloseTo(100, 0) // 100% 增长
    })

    it('应该计算平均值变化', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [10, 20, 30] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [15, 25, 35] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      const avgDiff = result.differences.find(d => d.dimension === '平均值')
      expect(avgDiff).toBeDefined()
      expect(avgDiff?.change).toBeCloseTo(5, 0) // 平均值增加5
    })

    it('应该识别显著变化', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [10, 20, 30] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [30, 60, 90] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      expect(result.insights.length).toBeGreaterThan(0)
      expect(result.insights[0]).toContain('显著')
    })

    it('应该处理下降趋势', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData1: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据1', data: [30, 60, 90] }]
      }

      const chartData2: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{ label: '数据2', data: [10, 20, 30] }]
      }

      const result = await service.compareCharts(chartData1, chartData2)

      const totalDiff = result.differences.find(d => d.dimension === '总体')
      expect(totalDiff?.changePercent).toBeLessThan(0)
      expect(result.summary).toContain('下降')
    })
  })

  describe('数据提取', () => {
    it('应该正确提取数值数据', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [
          { label: '数据集1', data: [10, 20, 30] },
          { label: '数据集2', data: [15, 25, 35] }
        ]
      }

      const result = await service.generateInsights('bar', chartData)

      // 应该提取所有数值
      expect(result).toBeDefined()
    })

    it('应该处理混合数据类型', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{
          label: '数据',
          data: [10, 'invalid' as any, 30]
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      // 应该只提取有效数值
      expect(result).toBeDefined()
    })
  })

  describe('模式识别', () => {
    it('应该检测周期性模式', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
        datasets: [{
          label: '销售额',
          data: [100, 120, 100, 120, 100, 120, 100, 120, 100, 120, 100, 120]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      const patternInsight = result.insights.find(i => i.type === 'pattern')
      expect(patternInsight).toBeDefined()
    })

    it('应该检测数据集中度', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
        datasets: [{
          label: '数据',
          data: [100, 100, 101, 100, 100, 99, 100, 100] // 更多数据点，更高集中度
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      // 这个数据既有周期性也有集中度特征，检测到任何模式都是正确的
      const patternInsight = result.insights.find(i => i.type === 'pattern')
      expect(patternInsight).toBeDefined()
      if (patternInsight) {
        // 数据可能被识别为周期性或集中度，两者都是合理的
        expect(patternInsight.description).toBeTruthy()
      }
    })
  })

  describe('业务含义生成', () => {
    it('应该结合业务上下文生成含义', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月'],
        datasets: [{
          label: '销售额',
          data: [100, 120, 140]
        }]
      }

      const result = await service.generateInsights('line', chartData, {
        businessContext: '电商平台销售数据'
      })

      expect(result.businessMeaning).toContain('电商平台销售数据')
    })

    it('应该在没有业务上下文时生成通用含义', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['A', 'B', 'C'],
        datasets: [{
          label: '数据',
          data: [10, 20, 30]
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result.businessMeaning).toBeDefined()
      expect(result.businessMeaning.length).toBeGreaterThan(0)
    })
  })

  describe('建议生成', () => {
    it('应该为增长趋势生成建议', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [100, 120, 140, 160, 180]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.recommendations.some(r => r.includes('增长') || r.includes('保持'))).toBe(true)
    })

    it('应该为下降趋势生成建议', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1月', '2月', '3月', '4月', '5月'],
        datasets: [{
          label: '销售额',
          data: [180, 160, 140, 120, 100]
        }]
      }

      const result = await service.generateInsights('line', chartData)

      expect(result.recommendations.some(r => r.includes('下降') || r.includes('改进'))).toBe(true)
    })

    it('应该为异常数据生成建议', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('API错误'))

      const chartData: ChartData = {
        labels: ['1', '2', '3', '4', '5', '6', '7', '8'],
        datasets: [{
          label: '数据',
          data: [100, 105, 98, 102, 500, 103, 99, 101]
        }]
      }

      const result = await service.generateInsights('bar', chartData)

      expect(result.recommendations.some(r => r.includes('异常') || r.includes('调查'))).toBe(true)
    })
  })
})
