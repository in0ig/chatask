import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { chartThemeService } from '@/services/chartThemeService'
import type { ThemeConfig } from '@/services/chartThemeService'

describe('ChartThemeService', () => {
  // 清理localStorage
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('预定义主题', () => {
    it('应该返回浅色主题配置', () => {
      const theme = chartThemeService.getTheme('light')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('light')
      expect(theme.displayName).toBe('浅色主题')
      expect(theme.colors.primary).toBeInstanceOf(Array)
      expect(theme.colors.primary.length).toBeGreaterThan(0)
    })

    it('应该返回深色主题配置', () => {
      const theme = chartThemeService.getTheme('dark')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('dark')
      expect(theme.displayName).toBe('深色主题')
      expect(theme.colors.background).toBe('#1a1a1a')
    })

    it('应该返回商务主题配置', () => {
      const theme = chartThemeService.getTheme('business')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('business')
      expect(theme.displayName).toBe('商务主题')
    })

    it('应该返回科技主题配置', () => {
      const theme = chartThemeService.getTheme('tech')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('tech')
      expect(theme.displayName).toBe('科技主题')
    })

    it('应该返回优雅主题配置', () => {
      const theme = chartThemeService.getTheme('elegant')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('elegant')
      expect(theme.displayName).toBe('优雅主题')
    })

    it('应该返回活力主题配置', () => {
      const theme = chartThemeService.getTheme('vibrant')
      
      expect(theme).toBeDefined()
      expect(theme.name).toBe('vibrant')
      expect(theme.displayName).toBe('活力主题')
    })

    it('不存在的主题应该返回默认浅色主题', () => {
      const theme = chartThemeService.getTheme('nonexistent')
      
      expect(theme.name).toBe('light')
    })
  })

  describe('获取主题列表', () => {
    it('应该返回所有预定义主题', () => {
      const themes = chartThemeService.getPredefinedThemes()
      
      expect(themes.length).toBeGreaterThanOrEqual(6)
      expect(themes.some(t => t.name === 'light')).toBe(true)
      expect(themes.some(t => t.name === 'dark')).toBe(true)
      expect(themes.some(t => t.name === 'business')).toBe(true)
      expect(themes.some(t => t.name === 'tech')).toBe(true)
      expect(themes.some(t => t.name === 'elegant')).toBe(true)
      expect(themes.some(t => t.name === 'vibrant')).toBe(true)
    })

    it('应该返回所有主题（包括自定义）', () => {
      const customTheme: ThemeConfig = {
        name: 'custom1',
        displayName: '自定义主题1',
        colors: {
          primary: ['#ff0000', '#00ff00', '#0000ff'],
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
      }

      chartThemeService.createCustomTheme(customTheme)
      const allThemes = chartThemeService.getAllThemes()
      
      expect(allThemes.length).toBeGreaterThan(6)
      expect(allThemes.some(t => t.name === 'custom1')).toBe(true)
    })
  })

  describe('自定义主题管理', () => {
    it('应该能够创建自定义主题', () => {
      const customTheme: ThemeConfig = {
        name: 'myTheme',
        displayName: '我的主题',
        colors: {
          primary: ['#ff0000', '#00ff00', '#0000ff'],
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
      }

      chartThemeService.createCustomTheme(customTheme)
      const retrieved = chartThemeService.getTheme('myTheme')
      
      expect(retrieved.name).toBe('myTheme')
      expect(retrieved.displayName).toBe('我的主题')
      expect(retrieved.colors.primary).toEqual(['#ff0000', '#00ff00', '#0000ff'])
    })

    it('不应该允许创建与预定义主题同名的自定义主题', () => {
      const customTheme: ThemeConfig = {
        name: 'light',
        displayName: '自定义浅色',
        colors: {
          primary: ['#ff0000'],
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
      }

      expect(() => {
        chartThemeService.createCustomTheme(customTheme)
      }).toThrow('主题名称与预定义主题冲突')
    })

    it('应该能够更新自定义主题', () => {
      const customTheme: ThemeConfig = {
        name: 'updateTest',
        displayName: '更新测试',
        colors: {
          primary: ['#ff0000'],
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
      }

      chartThemeService.createCustomTheme(customTheme)
      chartThemeService.updateCustomTheme('updateTest', {
        displayName: '已更新的主题'
      })

      const updated = chartThemeService.getTheme('updateTest')
      expect(updated.displayName).toBe('已更新的主题')
      expect(updated.name).toBe('updateTest') // 名称不应改变
    })

    it('更新不存在的主题应该抛出错误', () => {
      expect(() => {
        chartThemeService.updateCustomTheme('nonexistent', {
          displayName: '测试'
        })
      }).toThrow('主题不存在')
    })

    it('应该能够删除自定义主题', () => {
      const customTheme: ThemeConfig = {
        name: 'deleteTest',
        displayName: '删除测试',
        colors: {
          primary: ['#ff0000'],
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
      }

      chartThemeService.createCustomTheme(customTheme)
      chartThemeService.deleteCustomTheme('deleteTest')

      const retrieved = chartThemeService.getTheme('deleteTest')
      expect(retrieved.name).toBe('light') // 应该返回默认主题
    })

    it('不应该允许删除预定义主题', () => {
      expect(() => {
        chartThemeService.deleteCustomTheme('light')
      }).toThrow('不能删除预定义主题')
    })
  })

  describe('从品牌色创建主题', () => {
    it('应该能够从品牌色创建浅色主题', () => {
      const brandColors = ['#ff0000', '#00ff00', '#0000ff']
      const theme = chartThemeService.createThemeFromBrandColors(
        'brandTheme',
        '品牌主题',
        brandColors,
        false
      )

      expect(theme.name).toBe('brandTheme')
      expect(theme.displayName).toBe('品牌主题')
      expect(theme.colors.primary.slice(0, 3)).toEqual(brandColors)
      expect(theme.colors.background).toBe('#ffffff') // 浅色背景
    })

    it('应该能够从品牌色创建深色主题', () => {
      const brandColors = ['#ff0000', '#00ff00', '#0000ff']
      const theme = chartThemeService.createThemeFromBrandColors(
        'brandDark',
        '品牌深色主题',
        brandColors,
        true
      )

      expect(theme.name).toBe('brandDark')
      expect(theme.colors.background).toBe('#1a1a1a') // 深色背景
    })

    it('品牌色不足时应该用基础主题颜色补充', () => {
      const brandColors = ['#ff0000']
      const theme = chartThemeService.createThemeFromBrandColors(
        'singleColor',
        '单色主题',
        brandColors
      )

      expect(theme.colors.primary.length).toBeGreaterThan(1)
      expect(theme.colors.primary[0]).toBe('#ff0000')
    })
  })

  describe('主题导入导出', () => {
    it('应该能够导出主题配置', () => {
      const exported = chartThemeService.exportTheme('light')
      const parsed = JSON.parse(exported)

      expect(parsed.name).toBe('light')
      expect(parsed.displayName).toBe('浅色主题')
      expect(parsed.colors).toBeDefined()
    })

    it('应该能够导入主题配置', () => {
      const themeConfig: ThemeConfig = {
        name: 'imported',
        displayName: '导入的主题',
        colors: {
          primary: ['#ff0000'],
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
      }

      const jsonString = JSON.stringify(themeConfig)
      chartThemeService.importTheme(jsonString)

      const retrieved = chartThemeService.getTheme('imported')
      expect(retrieved.name).toBe('imported')
      expect(retrieved.displayName).toBe('导入的主题')
    })

    it('导入无效的JSON应该抛出错误', () => {
      expect(() => {
        chartThemeService.importTheme('invalid json')
      }).toThrow()
    })

    it('导入格式不正确的主题应该抛出错误', () => {
      const invalidTheme = JSON.stringify({ name: 'test' })
      
      expect(() => {
        chartThemeService.importTheme(invalidTheme)
      }).toThrow('主题配置格式不正确')
    })
  })

  describe('生成ECharts主题', () => {
    it('应该能够生成ECharts主题对象', () => {
      const echartsTheme = chartThemeService.generateEChartsTheme('light')

      expect(echartsTheme).toBeDefined()
      expect(echartsTheme.color).toBeInstanceOf(Array)
      expect(echartsTheme.backgroundColor).toBeDefined()
      expect(echartsTheme.textStyle).toBeDefined()
      expect(echartsTheme.tooltip).toBeDefined()
    })

    it('生成的主题应该包含所有必要的组件配置', () => {
      const echartsTheme = chartThemeService.generateEChartsTheme('dark')

      expect(echartsTheme.line).toBeDefined()
      expect(echartsTheme.bar).toBeDefined()
      expect(echartsTheme.pie).toBeDefined()
      expect(echartsTheme.scatter).toBeDefined()
      expect(echartsTheme.categoryAxis).toBeDefined()
      expect(echartsTheme.valueAxis).toBeDefined()
      expect(echartsTheme.legend).toBeDefined()
      expect(echartsTheme.toolbox).toBeDefined()
    })
  })

  describe('持久化', () => {
    it('自定义主题应该持久化到localStorage', () => {
      const customTheme: ThemeConfig = {
        name: 'persistent',
        displayName: '持久化主题',
        colors: {
          primary: ['#ff0000'],
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
      }

      chartThemeService.createCustomTheme(customTheme)

      const stored = localStorage.getItem('chatbi_custom_themes')
      expect(stored).toBeTruthy()
      
      const parsed = JSON.parse(stored!)
      expect(parsed).toBeInstanceOf(Array)
      expect(parsed.some((t: ThemeConfig) => t.name === 'persistent')).toBe(true)
    })
  })
})
