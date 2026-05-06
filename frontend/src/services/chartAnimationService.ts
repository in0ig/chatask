/**
 * 图表动画服务
 * 提供丰富的图表动画效果和过渡动画
 */

import type { ECharts, EChartsOption } from 'echarts'

// 动画配置
export interface AnimationConfig {
  enabled: boolean
  duration: number
  easing: string
  delay?: number
  delayUpdate?: number
}

// 动画预设
export type AnimationPreset = 'smooth' | 'bounce' | 'elastic' | 'fade' | 'zoom' | 'slide'

// 预定义动画配置
const ANIMATION_PRESETS: Record<AnimationPreset, AnimationConfig> = {
  smooth: {
    enabled: true,
    duration: 1000,
    easing: 'cubicOut',
    delay: 0,
    delayUpdate: 300
  },
  bounce: {
    enabled: true,
    duration: 1200,
    easing: 'bounceOut',
    delay: 0,
    delayUpdate: 300
  },
  elastic: {
    enabled: true,
    duration: 1500,
    easing: 'elasticOut',
    delay: 0,
    delayUpdate: 300
  },
  fade: {
    enabled: true,
    duration: 800,
    easing: 'linear',
    delay: 0,
    delayUpdate: 200
  },
  zoom: {
    enabled: true,
    duration: 1000,
    easing: 'cubicInOut',
    delay: 0,
    delayUpdate: 300
  },
  slide: {
    enabled: true,
    duration: 1000,
    easing: 'quadraticOut',
    delay: 0,
    delayUpdate: 300
  }
}

class ChartAnimationService {
  /**
   * 获取动画配置
   */
  getAnimationConfig(preset: AnimationPreset): AnimationConfig {
    return { ...ANIMATION_PRESETS[preset] }
  }

  /**
   * 应用动画配置到图表选项
   */
  applyAnimation(option: EChartsOption, config: AnimationConfig): EChartsOption {
    return {
      ...option,
      animation: config.enabled,
      animationDuration: config.duration,
      animationEasing: config.easing,
      animationDelay: config.delay,
      animationDurationUpdate: config.duration,
      animationEasingUpdate: config.easing,
      animationDelayUpdate: config.delayUpdate
    }
  }

  /**
   * 创建渐进式加载动画
   */
  createProgressiveAnimation(option: EChartsOption, itemCount: number): EChartsOption {
    const delayPerItem = 50 // 每个数据项延迟50ms
    
    return {
      ...option,
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      animationDelay: (idx: number) => idx * delayPerItem,
      animationDurationUpdate: 500,
      animationEasingUpdate: 'cubicOut',
      animationDelayUpdate: (idx: number) => idx * delayPerItem
    }
  }

  /**
   * 创建波浪式加载动画
   */
  createWaveAnimation(option: EChartsOption): EChartsOption {
    return {
      ...option,
      animation: true,
      animationDuration: 1000,
      animationEasing: 'elasticOut',
      animationDelay: (idx: number) => Math.sin(idx * 0.5) * 100,
      animationDurationUpdate: 500,
      animationEasingUpdate: 'elasticOut',
      animationDelayUpdate: (idx: number) => Math.sin(idx * 0.5) * 50
    }
  }

  /**
   * 创建随机延迟动画
   */
  createRandomAnimation(option: EChartsOption, maxDelay: number = 500): EChartsOption {
    return {
      ...option,
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      animationDelay: () => Math.random() * maxDelay,
      animationDurationUpdate: 500,
      animationEasingUpdate: 'cubicOut',
      animationDelayUpdate: () => Math.random() * (maxDelay / 2)
    }
  }

  /**
   * 创建分组动画
   */
  createGroupAnimation(option: EChartsOption, groupSize: number): EChartsOption {
    return {
      ...option,
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      animationDelay: (idx: number) => Math.floor(idx / groupSize) * 200,
      animationDurationUpdate: 500,
      animationEasingUpdate: 'cubicOut',
      animationDelayUpdate: (idx: number) => Math.floor(idx / groupSize) * 100
    }
  }

  /**
   * 创建缩放进入动画
   */
  createZoomInAnimation(chart: ECharts): void {
    const option = chart.getOption()
    
    // 临时设置缩放为0
    chart.setOption({
      ...option,
      series: (option.series as any[])?.map(series => ({
        ...series,
        animation: false,
        data: series.data?.map((item: any) => ({
          ...item,
          symbolSize: 0,
          itemStyle: {
            ...item.itemStyle,
            opacity: 0
          }
        }))
      }))
    }, true)

    // 延迟后恢复正常大小
    setTimeout(() => {
      chart.setOption({
        ...option,
        animation: true,
        animationDuration: 800,
        animationEasing: 'elasticOut'
      }, true)
    }, 50)
  }

  /**
   * 创建淡入动画
   */
  createFadeInAnimation(chart: ECharts): void {
    const option = chart.getOption()
    
    // 临时设置透明度为0
    chart.setOption({
      ...option,
      series: (option.series as any[])?.map(series => ({
        ...series,
        animation: false,
        itemStyle: {
          ...series.itemStyle,
          opacity: 0
        }
      }))
    }, true)

    // 延迟后恢复正常透明度
    setTimeout(() => {
      chart.setOption({
        ...option,
        animation: true,
        animationDuration: 1000,
        animationEasing: 'linear',
        series: (option.series as any[])?.map(series => ({
          ...series,
          itemStyle: {
            ...series.itemStyle,
            opacity: 1
          }
        }))
      }, true)
    }, 50)
  }

  /**
   * 创建滑入动画
   */
  createSlideInAnimation(chart: ECharts, direction: 'left' | 'right' | 'top' | 'bottom' = 'bottom'): void {
    const option = chart.getOption()
    const offset = 1000

    let transformConfig: any = {}
    switch (direction) {
      case 'left':
        transformConfig = { x: -offset }
        break
      case 'right':
        transformConfig = { x: offset }
        break
      case 'top':
        transformConfig = { y: -offset }
        break
      case 'bottom':
        transformConfig = { y: offset }
        break
    }

    // 临时设置偏移
    chart.setOption({
      ...option,
      series: (option.series as any[])?.map(series => ({
        ...series,
        animation: false,
        ...transformConfig
      }))
    }, true)

    // 延迟后恢复正常位置
    setTimeout(() => {
      chart.setOption({
        ...option,
        animation: true,
        animationDuration: 1000,
        animationEasing: 'cubicOut',
        series: (option.series as any[])?.map(series => ({
          ...series,
          x: 0,
          y: 0
        }))
      }, true)
    }, 50)
  }

  /**
   * 创建数据更新动画
   */
  createUpdateAnimation(chart: ECharts, newOption: EChartsOption, preset: AnimationPreset = 'smooth'): void {
    const config = this.getAnimationConfig(preset)
    const animatedOption = this.applyAnimation(newOption, config)
    
    chart.setOption(animatedOption, {
      notMerge: false,
      lazyUpdate: false,
      silent: false
    })
  }

  /**
   * 创建高亮动画
   */
  createHighlightAnimation(chart: ECharts, dataIndex: number, seriesIndex: number = 0): void {
    // 高亮指定数据点
    chart.dispatchAction({
      type: 'highlight',
      seriesIndex,
      dataIndex
    })

    // 2秒后取消高亮
    setTimeout(() => {
      chart.dispatchAction({
        type: 'downplay',
        seriesIndex,
        dataIndex
      })
    }, 2000)
  }

  /**
   * 创建循环高亮动画
   */
  createLoopHighlightAnimation(chart: ECharts, interval: number = 2000): () => void {
    const option = chart.getOption()
    const seriesData = (option.series as any[])?.[0]?.data || []
    let currentIndex = 0
    let isRunning = true

    const loop = () => {
      if (!isRunning) return

      // 取消上一个高亮
      if (currentIndex > 0) {
        chart.dispatchAction({
          type: 'downplay',
          seriesIndex: 0,
          dataIndex: currentIndex - 1
        })
      }

      // 高亮当前数据点
      chart.dispatchAction({
        type: 'highlight',
        seriesIndex: 0,
        dataIndex: currentIndex
      })

      // 显示tooltip
      chart.dispatchAction({
        type: 'showTip',
        seriesIndex: 0,
        dataIndex: currentIndex
      })

      currentIndex = (currentIndex + 1) % seriesData.length

      setTimeout(loop, interval)
    }

    loop()

    // 返回停止函数
    return () => {
      isRunning = false
      chart.dispatchAction({
        type: 'downplay',
        seriesIndex: 0,
        dataIndex: currentIndex
      })
      chart.dispatchAction({
        type: 'hideTip'
      })
    }
  }

  /**
   * 创建加载动画
   */
  showLoading(chart: ECharts, text: string = '加载中...'): void {
    chart.showLoading('default', {
      text,
      color: '#188df0',
      textColor: '#333',
      maskColor: 'rgba(255, 255, 255, 0.8)',
      zlevel: 0,
      fontSize: 14,
      showSpinner: true,
      spinnerRadius: 10,
      lineWidth: 3,
      fontWeight: 'normal',
      fontStyle: 'normal',
      fontFamily: 'sans-serif'
    })
  }

  /**
   * 隐藏加载动画
   */
  hideLoading(chart: ECharts): void {
    chart.hideLoading()
  }

  /**
   * 创建过渡动画
   */
  createTransitionAnimation(
    chart: ECharts,
    fromOption: EChartsOption,
    toOption: EChartsOption,
    duration: number = 1000
  ): void {
    // 先设置起始状态
    chart.setOption(fromOption, true)

    // 延迟后过渡到目标状态
    setTimeout(() => {
      chart.setOption({
        ...toOption,
        animation: true,
        animationDuration: duration,
        animationEasing: 'cubicInOut'
      }, false)
    }, 50)
  }

  /**
   * 获取所有可用的动画预设
   */
  getAvailablePresets(): AnimationPreset[] {
    return Object.keys(ANIMATION_PRESETS) as AnimationPreset[]
  }

  /**
   * 获取动画预设的显示名称
   */
  getPresetDisplayName(preset: AnimationPreset): string {
    const names: Record<AnimationPreset, string> = {
      smooth: '平滑',
      bounce: '弹跳',
      elastic: '弹性',
      fade: '淡入淡出',
      zoom: '缩放',
      slide: '滑动'
    }
    return names[preset]
  }
}

// 导出单例
export const chartAnimationService = new ChartAnimationService()
