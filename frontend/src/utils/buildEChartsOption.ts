/**
 * buildEChartsOption - 双Y轴 Combo Chart 配置构建工具
 *
 * 根据 series 配置生成 ECharts option，支持：
 * - 单Y轴（向后兼容，当所有 series 均无 yAxisIndex:1 时）
 * - 双Y轴（当任意 series 含 yAxisIndex:1 时）
 *   - 主轴（左，index 0）：数值格式，大数字用 K/M 缩写
 *   - 次轴（右，index 1）：百分比格式，追加 %
 */

export interface SeriesConfig {
  name: string
  type: 'bar' | 'line'
  yAxisIndex?: number
  data: (number | null)[]
  [key: string]: unknown
}

export interface EChartsOptionResult {
  yAxis: YAxisConfig | YAxisConfig[]
  series: SeriesConfig[]
  [key: string]: unknown
}

export interface YAxisConfig {
  type: 'value'
  name?: string
  position?: 'left' | 'right'
  axisLabel?: {
    formatter: string | ((value: number) => string)
  }
}

/**
 * 将大数字格式化为简短形式，支持语言：
 * - 中文(zh)：万、百万
 * - 英文(en) 或未传 locale：K、M
 */
export function formatPrimaryAxisValue(value: number, locale?: string): string {
  const isZh = !!locale && locale.startsWith('zh')
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1_000_000) {
    const v = abs / 1_000_000
    const num = v % 1 === 0 ? v : parseFloat(v.toFixed(1))
    return isZh ? `${sign}${num}百万` : `${sign}${num}M`
  }
  if (abs >= 10_000 || (!isZh && abs >= 1_000)) {
    if (isZh) {
      const v = abs / 10_000
      const num = v % 1 === 0 ? v : parseFloat(v.toFixed(1))
      return `${sign}${num}万`
    }
    const v = abs / 1_000
    return sign + (v % 1 === 0 ? v : parseFloat(v.toFixed(1))) + 'K'
  }
  return String(value)
}

export interface BuildEChartsOptionOptions {
  locale?: string
}

/**
 * 根据 series 配置构建 ECharts option（含 yAxis 和 series）
 *
 * Property 8: 当任意 series 含 yAxisIndex:1 时，yAxis 数组长度为 2
 * Property 9: 次轴（index 1）的 axisLabel.formatter 包含 %
 */
export function buildEChartsOption(
  series: SeriesConfig[],
  options?: BuildEChartsOptionOptions
): EChartsOptionResult {
  const locale = options?.locale
  const axisFormatter = (value: number) => formatPrimaryAxisValue(value, locale)

  // 检测是否需要双Y轴
  const hasDualAxis = series.some(s => s.yAxisIndex === 1)

  if (!hasDualAxis) {
    // 单Y轴（向后兼容）
    return {
      yAxis: {
        type: 'value',
        axisLabel: { formatter: axisFormatter }
      },
      series
    }
  }

  // 双Y轴配置
  const primaryAxis: YAxisConfig = {
    type: 'value',
    position: 'left',
    axisLabel: { formatter: axisFormatter }
  }

  const secondaryAxis: YAxisConfig = {
    type: 'value',
    position: 'right',
    axisLabel: {
      formatter: (value: number) => {
        const abs = Math.abs(value)
        if (abs >= 1000) return formatPrimaryAxisValue(value, locale)
        return `${value}%`
      }
    }
  }

  return {
    yAxis: [primaryAxis, secondaryAxis],
    series
  }
}
