/**
 * SmartChart 双Y轴属性测试
 *
 * Property 8: 当任意 series 含 yAxisIndex:1 时，生成的 ECharts option 的 yAxis 数组长度为 2
 * Property 9: 次轴（index 1）的 axisLabel.formatter 包含 %
 *
 * Validates: Requirements 5.5, 5.6
 *
 * Feature: chatbi-prompt-engine-v2, Property 8 & 9
 */

import { describe, it, expect } from 'vitest'
import { buildEChartsOption, formatPrimaryAxisValue } from '@/utils/buildEChartsOption'
import type { SeriesConfig } from '@/utils/buildEChartsOption'

// ─── 辅助生成器 ────────────────────────────────────────────────────────────────

/**
 * 生成含 yAxisIndex:1 的 series 集合（模拟 combo chart 场景）
 * 至少包含一个主轴 series 和一个次轴 series
 */
function makeComboSeries(
  primaryCount: number,
  secondaryCount: number
): SeriesConfig[] {
  const series: SeriesConfig[] = []
  for (let i = 0; i < primaryCount; i++) {
    series.push({ name: `bar_${i}`, type: 'bar', yAxisIndex: 0, data: [100, 200, 300] })
  }
  for (let i = 0; i < secondaryCount; i++) {
    series.push({ name: `line_${i}`, type: 'line', yAxisIndex: 1, data: [10.5, 20.3, -5.2] })
  }
  return series
}

/**
 * 生成不含 yAxisIndex:1 的 series 集合（单Y轴场景）
 */
function makeSingleAxisSeries(count: number): SeriesConfig[] {
  return Array.from({ length: count }, (_, i) => ({
    name: `series_${i}`,
    type: 'bar' as const,
    yAxisIndex: 0,
    data: [100 * (i + 1), 200 * (i + 1)]
  }))
}

// ─── Property 8 ────────────────────────────────────────────────────────────────

describe('Property 8: 双Y轴渲染 - yAxis 数组长度为 2', () => {
  /**
   * Feature: chatbi-prompt-engine-v2, Property 8
   * For any chart series configuration where at least one series has yAxisIndex:1,
   * the ECharts option generated should contain a yAxis array with exactly 2 entries.
   * Validates: Requirements 5.5
   */

  it('1个主轴 + 1个次轴 series → yAxis 长度为 2', () => {
    const series = makeComboSeries(1, 1)
    const option = buildEChartsOption(series)
    expect(Array.isArray(option.yAxis)).toBe(true)
    expect((option.yAxis as any[]).length).toBe(2)
  })

  it('2个主轴 + 1个次轴 series → yAxis 长度为 2', () => {
    const series = makeComboSeries(2, 1)
    const option = buildEChartsOption(series)
    expect(Array.isArray(option.yAxis)).toBe(true)
    expect((option.yAxis as any[]).length).toBe(2)
  })

  it('1个主轴 + 3个次轴 series → yAxis 长度为 2', () => {
    const series = makeComboSeries(1, 3)
    const option = buildEChartsOption(series)
    expect(Array.isArray(option.yAxis)).toBe(true)
    expect((option.yAxis as any[]).length).toBe(2)
  })

  it('5个主轴 + 2个次轴 series → yAxis 长度为 2', () => {
    const series = makeComboSeries(5, 2)
    const option = buildEChartsOption(series)
    expect(Array.isArray(option.yAxis)).toBe(true)
    expect((option.yAxis as any[]).length).toBe(2)
  })

  it('仅次轴 series（yAxisIndex:1）→ yAxis 长度为 2', () => {
    const series: SeriesConfig[] = [
      { name: 'yoy', type: 'line', yAxisIndex: 1, data: [5.2, -3.1, 8.0] }
    ]
    const option = buildEChartsOption(series)
    expect(Array.isArray(option.yAxis)).toBe(true)
    expect((option.yAxis as any[]).length).toBe(2)
  })

  // 反例：无次轴时不应生成双Y轴
  it('无 yAxisIndex:1 的 series → yAxis 不是长度为 2 的数组（单Y轴）', () => {
    const series = makeSingleAxisSeries(3)
    const option = buildEChartsOption(series)
    // 单Y轴时 yAxis 是对象而非数组，或数组长度不为 2
    const isArray = Array.isArray(option.yAxis)
    if (isArray) {
      expect((option.yAxis as any[]).length).not.toBe(2)
    } else {
      expect(isArray).toBe(false)
    }
  })

  it('yAxisIndex 为 undefined 的 series → 单Y轴', () => {
    const series: SeriesConfig[] = [
      { name: 'attendance', type: 'bar', data: [100, 200] }
    ]
    const option = buildEChartsOption(series)
    const isArray = Array.isArray(option.yAxis)
    if (isArray) {
      expect((option.yAxis as any[]).length).not.toBe(2)
    } else {
      expect(isArray).toBe(false)
    }
  })
})

// ─── Property 9 ────────────────────────────────────────────────────────────────

describe('Property 9: 次轴百分比格式化 - axisLabel.formatter 包含 %', () => {
  /**
   * Feature: chatbi-prompt-engine-v2, Property 9
   * For any Combo Chart rendering, the secondary Y-axis (index 1) in the ECharts option
   * should have an axisLabel.formatter that appends % to values.
   * Validates: Requirements 5.6
   */

  it('次轴 axisLabel.formatter 字符串包含 %', () => {
    const series = makeComboSeries(1, 1)
    const option = buildEChartsOption(series)
    const yAxisArr = option.yAxis as any[]
    const secondaryAxis = yAxisArr[1]
    const formatter = secondaryAxis.axisLabel?.formatter
    expect(formatter).toBeDefined()
    // formatter 可以是字符串模板或函数
    if (typeof formatter === 'string') {
      expect(formatter).toContain('%')
    } else if (typeof formatter === 'function') {
      const result = formatter(50)
      expect(String(result)).toContain('%')
    }
  })

  it('次轴 formatter 对正数值追加 %', () => {
    const series = makeComboSeries(1, 1)
    const option = buildEChartsOption(series)
    const yAxisArr = option.yAxis as any[]
    const secondaryAxis = yAxisArr[1]
    const formatter = secondaryAxis.axisLabel?.formatter
    if (typeof formatter === 'function') {
      expect(String(formatter(15.5))).toContain('%')
      expect(String(formatter(0))).toContain('%')
      expect(String(formatter(-8.3))).toContain('%')
    } else {
      // 字符串模板如 '{value}%' 也满足
      expect(String(formatter)).toContain('%')
    }
  })

  it('主轴（index 0）formatter 不追加 %', () => {
    const series = makeComboSeries(1, 1)
    const option = buildEChartsOption(series)
    const yAxisArr = option.yAxis as any[]
    const primaryAxis = yAxisArr[0]
    const formatter = primaryAxis.axisLabel?.formatter
    if (typeof formatter === 'function') {
      // 主轴格式化大数字为 K/M，不含 %
      const result = String(formatter(1_500_000))
      expect(result).not.toContain('%')
      expect(result).toContain('M')
    } else if (typeof formatter === 'string') {
      expect(formatter).not.toContain('%')
    }
  })

  it('多个次轴 series 时，次轴配置仍只有一个且含 %', () => {
    const series = makeComboSeries(2, 3)
    const option = buildEChartsOption(series)
    const yAxisArr = option.yAxis as any[]
    expect(yAxisArr.length).toBe(2)
    const secondaryFormatter = yAxisArr[1].axisLabel?.formatter
    if (typeof secondaryFormatter === 'string') {
      expect(secondaryFormatter).toContain('%')
    } else if (typeof secondaryFormatter === 'function') {
      expect(String(secondaryFormatter(25))).toContain('%')
    }
  })
})

// ─── 主轴格式化辅助测试 ─────────────────────────────────────────────────────────

describe('formatPrimaryAxisValue - 主轴数值格式化', () => {
  it('百万级数字格式化为 M', () => {
    expect(formatPrimaryAxisValue(1_500_000)).toBe('1.5M')
    expect(formatPrimaryAxisValue(2_000_000)).toBe('2M')
  })

  it('千级数字格式化为 K', () => {
    expect(formatPrimaryAxisValue(15_000)).toBe('15K')
    expect(formatPrimaryAxisValue(1_500)).toBe('1.5K')
  })

  it('小数字保持原样', () => {
    expect(formatPrimaryAxisValue(500)).toBe('500')
    expect(formatPrimaryAxisValue(0)).toBe('0')
  })

  it('负数正确格式化', () => {
    expect(formatPrimaryAxisValue(-1_500_000)).toBe('-1.5M')
    expect(formatPrimaryAxisValue(-15_000)).toBe('-15K')
  })
})
