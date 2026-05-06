/**
 * AI图表选择服务单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { AIChartSelectorService } from '@/services/aiChartSelector'
import type { ChartData } from '@/types/chart'

describe('AIChartSelectorService', () => {
  let service: AIChartSelectorService
  
  beforeEach(() => {
    service = new AIChartSelectorService('http://localhost:8000/api')
    // 默认禁用AI，使用规则引擎进行测试
    service.setEnabled(false)
  })

  describe('数据特征分析', () => {
    it('应该正确分析时间序列数据', async () => {
      const data: ChartData = {
        columns: ['日期', '销售额'],
        rows: [
          ['2024-01-01', 1000],
          ['2024-01-02', 1200],
          ['2024-01-03', 1100]
        ],
        metadata: {
          columnTypes: ['date', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.dataAnalysis.hasTimeSeries).toBe(true)
      expect(result.dataAnalysis.dateColumns).toBe(1)
      expect(result.dataAnalysis.numericColumns).toBe(1)
      expect(result.primary.type).toBe('line')
      expect(result.primary.reason).toContain('时间序列')
    })

    it('应该正确分析分类数据', async () => {
      const data: ChartData = {
        columns: ['产品', '销量'],
        rows: [
          ['产品A', 100],
          ['产品B', 200],
          ['产品C', 150]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.dataAnalysis.categoricalColumns).toBe(1)
      expect(result.dataAnalysis.numericColumns).toBe(1)
      expect(result.dataAnalysis.rowCount).toBe(3)
    })

    it('应该正确分析多维数值数据', async () => {
      const data: ChartData = {
        columns: ['X', 'Y', 'Z'],
        rows: [
          [10, 20, 30],
          [15, 25, 35],
          [20, 30, 40]
        ],
        metadata: {
          columnTypes: ['number', 'number', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.dataAnalysis.numericColumns).toBe(3)
      expect(result.dataAnalysis.categoricalColumns).toBe(0)
    })
  })

  describe('基于数据特征的图表推荐', () => {
    it('时间序列数据应推荐折线图', async () => {
      const data: ChartData = {
        columns: ['日期', '访问量'],
        rows: [
          ['2024-01-01', 1000],
          ['2024-01-02', 1200]
        ],
        metadata: {
          columnTypes: ['date', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('line')
      expect(result.primary.confidence).toBeGreaterThan(0.8)
      expect(result.primary.reason).toBeTruthy()
    })

    it('少量分类数据应推荐饼图', async () => {
      const data: ChartData = {
        columns: ['类别', '数量'],
        rows: [
          ['A', 30],
          ['B', 40],
          ['C', 30]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('pie')
      expect(result.primary.reason).toContain('占比')
    })

    it('多数值字段应推荐散点图', async () => {
      const data: ChartData = {
        columns: ['X', 'Y'],
        rows: [
          [10, 20],
          [15, 25],
          [20, 30]
        ],
        metadata: {
          columnTypes: ['number', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('scatter')
      expect(result.primary.reason).toContain('相关性')
    })

    it('多指标数据应推荐雷达图', async () => {
      const data: ChartData = {
        columns: ['产品', '质量', '价格', '服务', '口碑'],
        rows: [
          ['产品A', 80, 70, 90, 85]
        ],
        metadata: {
          columnTypes: ['string', 'number', 'number', 'number', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('radar')
      expect(result.primary.reason).toContain('多维度')
    })

    it('二维分类数据应推荐热力图', async () => {
      const data: ChartData = {
        columns: ['行', '列', '值'],
        rows: [
          ['A', 'X', 10],
          ['A', 'Y', 20],
          ['B', 'X', 15]
        ],
        metadata: {
          columnTypes: ['string', 'string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('heatmap')
      expect(result.primary.reason).toContain('分布')
    })
  })

  describe('基于用户问题语义的推荐', () => {
    it('用户问"趋势"应推荐折线图', async () => {
      const data: ChartData = {
        columns: ['月份', '销售额'],
        rows: [
          ['1月', 1000],
          ['2月', 1200]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({
        data,
        userQuestion: '显示销售额的趋势'
      })
      
      expect(result.primary.type).toBe('line')
      expect(result.primary.reason).toContain('趋势')
    })

    it('用户问"占比"应推荐饼图', async () => {
      const data: ChartData = {
        columns: ['类别', '数量'],
        rows: [
          ['A', 30],
          ['B', 70]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({
        data,
        userQuestion: '各类别的占比是多少'
      })
      
      expect(result.primary.type).toBe('pie')
      expect(result.primary.reason).toContain('占比')
    })

    it('用户问"对比"应推荐柱状图', async () => {
      const data: ChartData = {
        columns: ['产品', '销量'],
        rows: [
          ['产品A', 100],
          ['产品B', 200]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({
        data,
        userQuestion: '对比各产品的销量'
      })
      
      expect(result.primary.type).toBe('bar')
      expect(result.primary.reason).toContain('对比')
    })

    it('用户问"分布"应推荐热力图', async () => {
      const data: ChartData = {
        columns: ['X', 'Y', 'Z'],
        rows: [
          ['A', 'M', 10],
          ['B', 'N', 20]
        ],
        metadata: {
          columnTypes: ['string', 'string', 'number']
        }
      }

      const result = await service.selectChartType({
        data,
        userQuestion: '数据的分布情况'
      })
      
      expect(result.primary.type).toBe('heatmap')
      expect(result.primary.reason).toContain('分布')
    })

    it('用户问"相关"应推荐散点图', async () => {
      const data: ChartData = {
        columns: ['X', 'Y'],
        rows: [
          [10, 20],
          [15, 25]
        ],
        metadata: {
          columnTypes: ['number', 'number']
        }
      }

      const result = await service.selectChartType({
        data,
        userQuestion: 'X和Y的相关性'
      })
      
      expect(result.primary.type).toBe('scatter')
      expect(result.primary.reason).toContain('相关性')
    })
  })

  describe('置信度评分和备选推荐', () => {
    it('应该提供置信度评分', async () => {
      const data: ChartData = {
        columns: ['日期', '销售额'],
        rows: [
          ['2024-01-01', 1000]
        ],
        metadata: {
          columnTypes: ['date', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.confidence).toBeGreaterThan(0)
      expect(result.primary.confidence).toBeLessThanOrEqual(1)
    })

    it('应该提供备选推荐', async () => {
      const data: ChartData = {
        columns: ['类别', '数量'],
        rows: [
          ['A', 100],
          ['B', 200]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.alternatives).toBeDefined()
      expect(result.alternatives.length).toBeGreaterThan(0)
      expect(result.alternatives.length).toBeLessThanOrEqual(2)
      
      result.alternatives.forEach(alt => {
        expect(alt.type).toBeTruthy()
        expect(alt.confidence).toBeGreaterThan(0)
        expect(alt.reason).toBeTruthy()
      })
    })

    it('备选推荐应该与主推荐不同', async () => {
      const data: ChartData = {
        columns: ['类别', '数量'],
        rows: [
          ['A', 100]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      result.alternatives.forEach(alt => {
        expect(alt.type).not.toBe(result.primary.type)
      })
    })
  })

  describe('推荐理由生成', () => {
    it('应该为每个推荐提供清晰的理由', async () => {
      const data: ChartData = {
        columns: ['日期', '销售额'],
        rows: [
          ['2024-01-01', 1000]
        ],
        metadata: {
          columnTypes: ['date', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.reason).toBeTruthy()
      expect(result.primary.reason.length).toBeGreaterThan(10)
      
      result.alternatives.forEach(alt => {
        expect(alt.reason).toBeTruthy()
        expect(alt.reason.length).toBeGreaterThan(10)
      })
    })

    it('理由应该与图表类型相关', async () => {
      const data: ChartData = {
        columns: ['日期', '销售额'],
        rows: [
          ['2024-01-01', 1000]
        ],
        metadata: {
          columnTypes: ['date', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      if (result.primary.type === 'line') {
        expect(result.primary.reason.toLowerCase()).toMatch(/趋势|变化|时间/)
      } else if (result.primary.type === 'pie') {
        expect(result.primary.reason.toLowerCase()).toMatch(/占比|比例|份额/)
      } else if (result.primary.type === 'bar') {
        expect(result.primary.reason.toLowerCase()).toMatch(/对比|比较/)
      }
    })
  })

  describe('降级策略', () => {
    it('AI不可用时应使用规则引擎', async () => {
      service.setEnabled(false)
      
      const data: ChartData = {
        columns: ['类别', '数量'],
        rows: [
          ['A', 100]
        ],
        metadata: {
          columnTypes: ['string', 'number']
        }
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBeTruthy()
      expect(result.primary.confidence).toBeGreaterThan(0)
      expect(result.primary.reason).toBeTruthy()
    })

    it('空数据应返回默认柱状图', async () => {
      const data: ChartData = {
        columns: [],
        rows: []
      }

      const result = await service.selectChartType({ data })
      
      expect(result.primary.type).toBe('bar')
    })
  })

  describe('日期识别', () => {
    it('应该识别YYYY-MM-DD格式', async () => {
      const data: ChartData = {
        columns: ['日期', '值'],
        rows: [
          ['2024-01-01', 100]
        ]
      }

      const result = await service.selectChartType({ data })
      
      expect(result.dataAnalysis.dateColumns).toBeGreaterThan(0)
    })

    it('应该识别YYYY/MM/DD格式', async () => {
      const data: ChartData = {
        columns: ['日期', '值'],
        rows: [
          ['2024/01/01', 100]
        ]
      }

      const result = await service.selectChartType({ data })
      
      expect(result.dataAnalysis.dateColumns).toBeGreaterThan(0)
    })
  })

  describe('服务可用性检查', () => {
    it('应该能够检查服务可用性', async () => {
      // Mock fetch
      global.fetch = vi.fn().mockResolvedValue({
        ok: true
      })

      const available = await service.checkAvailability()
      
      expect(available).toBe(true)
    })

    it('服务不可用时应返回false', async () => {
      // Mock fetch to fail
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const available = await service.checkAvailability()
      
      expect(available).toBe(false)
    })
  })
})
