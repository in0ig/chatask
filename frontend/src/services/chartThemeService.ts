/**
 * 图表主题服务
 * 提供多套预定义主题和自定义主题管理
 */

import type { ChartTheme } from '@/types/chart'

// 主题颜色配置
export interface ThemeColors {
  primary: string[]
  background: string
  text: string
  axisLine: string
  splitLine: string
  tooltip: {
    background: string
    border: string
    text: string
  }
}

// 主题配置
export interface ThemeConfig {
  name: string
  displayName: string
  colors: ThemeColors
  animation: {
    duration: number
    easing: string
  }
}

// 预定义主题
const PREDEFINED_THEMES: Record<string, ThemeConfig> = {
  light: {
    name: 'light',
    displayName: '浅色主题',
    colors: {
      primary: [
        '#188df0', '#83bff6', '#2378f7', '#5470c6', '#91cc75',
        '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452'
      ],
      background: '#ffffff',
      text: '#333333',
      axisLine: '#cccccc',
      splitLine: '#e4e7ed',
      tooltip: {
        background: 'rgba(50, 50, 50, 0.9)',
        border: '#333',
        text: '#fff'
      }
    },
    animation: {
      duration: 1000,
      easing: 'cubicOut'
    }
  },
  dark: {
    name: 'dark',
    displayName: '深色主题',
    colors: {
      primary: [
        '#4992ff', '#7cffb2', '#fddd60', '#ff6e76', '#58d9f9',
        '#05c091', '#ff8a45', '#8d48e3', '#dd79ff', '#ffb980'
      ],
      background: '#1a1a1a',
      text: '#eeeeee',
      axisLine: '#555555',
      splitLine: '#333333',
      tooltip: {
        background: 'rgba(30, 30, 30, 0.95)',
        border: '#555',
        text: '#eee'
      }
    },
    animation: {
      duration: 1000,
      easing: 'cubicOut'
    }
  },
  business: {
    name: 'business',
    displayName: '商务主题',
    colors: {
      primary: [
        '#2c3e50', '#34495e', '#7f8c8d', '#95a5a6', '#bdc3c7',
        '#3498db', '#2980b9', '#1abc9c', '#16a085', '#27ae60'
      ],
      background: '#f8f9fa',
      text: '#2c3e50',
      axisLine: '#95a5a6',
      splitLine: '#ecf0f1',
      tooltip: {
        background: 'rgba(44, 62, 80, 0.95)',
        border: '#34495e',
        text: '#ecf0f1'
      }
    },
    animation: {
      duration: 800,
      easing: 'cubicInOut'
    }
  },
  tech: {
    name: 'tech',
    displayName: '科技主题',
    colors: {
      primary: [
        '#00d4ff', '#00ffff', '#00ff9f', '#00ff00', '#9fff00',
        '#ffff00', '#ff9f00', '#ff00ff', '#9f00ff', '#0000ff'
      ],
      background: '#0a0e27',
      text: '#00d4ff',
      axisLine: '#1a2332',
      splitLine: '#1a2332',
      tooltip: {
        background: 'rgba(10, 14, 39, 0.95)',
        border: '#00d4ff',
        text: '#00ffff'
      }
    },
    animation: {
      duration: 1200,
      easing: 'elasticOut'
    }
  },
  elegant: {
    name: 'elegant',
    displayName: '优雅主题',
    colors: {
      primary: [
        '#c9a0dc', '#b8a0dc', '#a0b8dc', '#a0c9dc', '#a0dcb8',
        '#b8dca0', '#c9dca0', '#dcc9a0', '#dcb8a0', '#dca0b8'
      ],
      background: '#fafafa',
      text: '#666666',
      axisLine: '#d0d0d0',
      splitLine: '#f0f0f0',
      tooltip: {
        background: 'rgba(102, 102, 102, 0.9)',
        border: '#999',
        text: '#fff'
      }
    },
    animation: {
      duration: 1500,
      easing: 'quadraticInOut'
    }
  },
  vibrant: {
    name: 'vibrant',
    displayName: '活力主题',
    colors: {
      primary: [
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6c5ce7',
        '#fd79a8', '#fdcb6e', '#00b894', '#e17055', '#74b9ff'
      ],
      background: '#ffffff',
      text: '#2d3436',
      axisLine: '#b2bec3',
      splitLine: '#dfe6e9',
      tooltip: {
        background: 'rgba(45, 52, 54, 0.9)',
        border: '#636e72',
        text: '#fff'
      }
    },
    animation: {
      duration: 800,
      easing: 'bounceOut'
    }
  }
}

// 自定义主题存储键
const CUSTOM_THEMES_KEY = 'chatbi_custom_themes'

class ChartThemeService {
  private customThemes: Map<string, ThemeConfig> = new Map()

  constructor() {
    this.loadCustomThemes()
  }

  /**
   * 获取主题配置
   */
  getTheme(themeName: string): ThemeConfig {
    // 先查找预定义主题
    if (PREDEFINED_THEMES[themeName]) {
      return PREDEFINED_THEMES[themeName]
    }

    // 再查找自定义主题
    const customTheme = this.customThemes.get(themeName)
    if (customTheme) {
      return customTheme
    }

    // 默认返回浅色主题
    return PREDEFINED_THEMES.light
  }

  /**
   * 获取所有可用主题
   */
  getAllThemes(): ThemeConfig[] {
    const predefined = Object.values(PREDEFINED_THEMES)
    const custom = Array.from(this.customThemes.values())
    return [...predefined, ...custom]
  }

  /**
   * 获取预定义主题列表
   */
  getPredefinedThemes(): ThemeConfig[] {
    return Object.values(PREDEFINED_THEMES)
  }

  /**
   * 获取自定义主题列表
   */
  getCustomThemes(): ThemeConfig[] {
    return Array.from(this.customThemes.values())
  }

  /**
   * 创建自定义主题
   */
  createCustomTheme(config: ThemeConfig): void {
    if (PREDEFINED_THEMES[config.name]) {
      throw new Error('主题名称与预定义主题冲突')
    }

    this.customThemes.set(config.name, config)
    this.saveCustomThemes()
  }

  /**
   * 更新自定义主题
   */
  updateCustomTheme(name: string, config: Partial<ThemeConfig>): void {
    const existingTheme = this.customThemes.get(name)
    if (!existingTheme) {
      throw new Error('主题不存在')
    }

    const updatedTheme = {
      ...existingTheme,
      ...config,
      name // 保持名称不变
    }

    this.customThemes.set(name, updatedTheme)
    this.saveCustomThemes()
  }

  /**
   * 删除自定义主题
   */
  deleteCustomTheme(name: string): void {
    if (PREDEFINED_THEMES[name]) {
      throw new Error('不能删除预定义主题')
    }

    this.customThemes.delete(name)
    this.saveCustomThemes()
  }

  /**
   * 从企业品牌色创建主题
   */
  createThemeFromBrandColors(
    name: string,
    displayName: string,
    brandColors: string[],
    isDark: boolean = false
  ): ThemeConfig {
    const baseTheme = isDark ? PREDEFINED_THEMES.dark : PREDEFINED_THEMES.light

    const theme: ThemeConfig = {
      name,
      displayName,
      colors: {
        ...baseTheme.colors,
        primary: brandColors.length >= 3 ? brandColors : [
          ...brandColors,
          ...baseTheme.colors.primary.slice(brandColors.length)
        ]
      },
      animation: baseTheme.animation
    }

    return theme
  }

  /**
   * 导出主题配置
   */
  exportTheme(name: string): string {
    const theme = this.getTheme(name)
    return JSON.stringify(theme, null, 2)
  }

  /**
   * 导入主题配置
   */
  importTheme(jsonString: string): void {
    try {
      const theme = JSON.parse(jsonString) as ThemeConfig
      
      // 验证主题配置
      if (!theme.name || !theme.displayName || !theme.colors) {
        throw new Error('主题配置格式不正确')
      }

      this.createCustomTheme(theme)
    } catch (error) {
      throw new Error('导入主题失败: ' + (error as Error).message)
    }
  }

  /**
   * 加载自定义主题
   */
  private loadCustomThemes(): void {
    try {
      const stored = localStorage.getItem(CUSTOM_THEMES_KEY)
      if (stored) {
        const themes = JSON.parse(stored) as ThemeConfig[]
        themes.forEach(theme => {
          this.customThemes.set(theme.name, theme)
        })
      }
    } catch (error) {
      console.error('Failed to load custom themes:', error)
    }
  }

  /**
   * 保存自定义主题
   */
  private saveCustomThemes(): void {
    try {
      const themes = Array.from(this.customThemes.values())
      localStorage.setItem(CUSTOM_THEMES_KEY, JSON.stringify(themes))
    } catch (error) {
      console.error('Failed to save custom themes:', error)
    }
  }

  /**
   * 生成ECharts主题对象
   */
  generateEChartsTheme(themeName: string): any {
    const theme = this.getTheme(themeName)

    return {
      color: theme.colors.primary,
      backgroundColor: theme.colors.background,
      textStyle: {
        color: theme.colors.text
      },
      title: {
        textStyle: {
          color: theme.colors.text
        },
        subtextStyle: {
          color: theme.colors.text
        }
      },
      line: {
        itemStyle: {
          borderWidth: 1
        },
        lineStyle: {
          width: 2
        },
        symbolSize: 4,
        symbol: 'circle',
        smooth: false
      },
      radar: {
        itemStyle: {
          borderWidth: 1
        },
        lineStyle: {
          width: 2
        },
        symbolSize: 4,
        symbol: 'circle',
        smooth: false
      },
      bar: {
        itemStyle: {
          barBorderWidth: 0,
          barBorderColor: theme.colors.axisLine
        }
      },
      pie: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      scatter: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      boxplot: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      parallel: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      sankey: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      funnel: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      gauge: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        }
      },
      candlestick: {
        itemStyle: {
          color: theme.colors.primary[0],
          color0: theme.colors.primary[1],
          borderColor: theme.colors.primary[0],
          borderColor0: theme.colors.primary[1],
          borderWidth: 1
        }
      },
      graph: {
        itemStyle: {
          borderWidth: 0,
          borderColor: theme.colors.axisLine
        },
        lineStyle: {
          width: 1,
          color: theme.colors.axisLine
        },
        symbolSize: 4,
        symbol: 'circle',
        smooth: false,
        color: theme.colors.primary,
        label: {
          color: theme.colors.text
        }
      },
      map: {
        itemStyle: {
          areaColor: '#eee',
          borderColor: '#444',
          borderWidth: 0.5
        },
        label: {
          color: '#000'
        },
        emphasis: {
          itemStyle: {
            areaColor: 'rgba(255,215,0,0.8)',
            borderColor: '#444',
            borderWidth: 1
          },
          label: {
            color: 'rgb(100,0,0)'
          }
        }
      },
      geo: {
        itemStyle: {
          areaColor: '#eee',
          borderColor: '#444',
          borderWidth: 0.5
        },
        label: {
          color: '#000'
        },
        emphasis: {
          itemStyle: {
            areaColor: 'rgba(255,215,0,0.8)',
            borderColor: '#444',
            borderWidth: 1
          },
          label: {
            color: 'rgb(100,0,0)'
          }
        }
      },
      categoryAxis: {
        axisLine: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisTick: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisLabel: {
          show: true,
          color: theme.colors.text
        },
        splitLine: {
          show: false,
          lineStyle: {
            color: [theme.colors.splitLine]
          }
        },
        splitArea: {
          show: false,
          areaStyle: {
            color: [
              'rgba(250,250,250,0.3)',
              'rgba(200,200,200,0.3)'
            ]
          }
        }
      },
      valueAxis: {
        axisLine: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisTick: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisLabel: {
          show: true,
          color: theme.colors.text
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: [theme.colors.splitLine]
          }
        },
        splitArea: {
          show: false,
          areaStyle: {
            color: [
              'rgba(250,250,250,0.3)',
              'rgba(200,200,200,0.3)'
            ]
          }
        }
      },
      logAxis: {
        axisLine: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisTick: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisLabel: {
          show: true,
          color: theme.colors.text
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: [theme.colors.splitLine]
          }
        },
        splitArea: {
          show: false,
          areaStyle: {
            color: [
              'rgba(250,250,250,0.3)',
              'rgba(200,200,200,0.3)'
            ]
          }
        }
      },
      timeAxis: {
        axisLine: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisTick: {
          show: true,
          lineStyle: {
            color: theme.colors.axisLine
          }
        },
        axisLabel: {
          show: true,
          color: theme.colors.text
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: [theme.colors.splitLine]
          }
        },
        splitArea: {
          show: false,
          areaStyle: {
            color: [
              'rgba(250,250,250,0.3)',
              'rgba(200,200,200,0.3)'
            ]
          }
        }
      },
      toolbox: {
        iconStyle: {
          borderColor: theme.colors.text
        },
        emphasis: {
          iconStyle: {
            borderColor: theme.colors.primary[0]
          }
        }
      },
      legend: {
        textStyle: {
          color: theme.colors.text
        }
      },
      tooltip: {
        axisPointer: {
          lineStyle: {
            color: theme.colors.axisLine,
            width: 1
          },
          crossStyle: {
            color: theme.colors.axisLine,
            width: 1
          }
        },
        backgroundColor: theme.colors.tooltip.background,
        borderColor: theme.colors.tooltip.border,
        textStyle: {
          color: theme.colors.tooltip.text
        }
      },
      timeline: {
        lineStyle: {
          color: theme.colors.axisLine,
          width: 1
        },
        itemStyle: {
          color: theme.colors.primary[0],
          borderWidth: 1
        },
        controlStyle: {
          color: theme.colors.primary[0],
          borderColor: theme.colors.primary[0],
          borderWidth: 0.5
        },
        checkpointStyle: {
          color: theme.colors.primary[1],
          borderColor: 'rgba(194,53,49,0.5)'
        },
        label: {
          color: theme.colors.text
        },
        emphasis: {
          itemStyle: {
            color: theme.colors.primary[1]
          },
          controlStyle: {
            color: theme.colors.primary[0],
            borderColor: theme.colors.primary[0],
            borderWidth: 0.5
          },
          label: {
            color: theme.colors.text
          }
        }
      },
      visualMap: {
        color: [theme.colors.primary[0], theme.colors.primary[1]]
      },
      dataZoom: {
        backgroundColor: 'rgba(47,69,84,0)',
        dataBackgroundColor: 'rgba(47,69,84,0.3)',
        fillerColor: 'rgba(167,183,204,0.4)',
        handleColor: theme.colors.primary[0],
        handleSize: '100%',
        textStyle: {
          color: theme.colors.text
        }
      },
      markPoint: {
        label: {
          color: theme.colors.text
        },
        emphasis: {
          label: {
            color: theme.colors.text
          }
        }
      }
    }
  }
}

// 导出单例
export const chartThemeService = new ChartThemeService()
