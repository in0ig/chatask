/**
 * 图表配置管理服务
 * 支持图表配置的保存、加载和模板管理
 */

import type { ChartConfig, ChartTemplate } from '@/types/chart'

export class ChartConfigService {
  private readonly STORAGE_KEY_PREFIX = 'chatbi_chart_config_'
  private readonly TEMPLATE_KEY = 'chatbi_chart_templates'

  /**
   * 保存图表配置
   */
  saveConfig(config: ChartConfig): string {
    const id = config.id || this.generateId()
    const configWithMeta: ChartConfig = {
      ...config,
      id,
      createdAt: config.createdAt || new Date(),
      updatedAt: new Date()
    }

    const key = this.STORAGE_KEY_PREFIX + id
    localStorage.setItem(key, JSON.stringify(configWithMeta))

    return id
  }

  /**
   * 加载图表配置
   */
  loadConfig(id: string): ChartConfig | null {
    const key = this.STORAGE_KEY_PREFIX + id
    const data = localStorage.getItem(key)

    if (!data) {
      return null
    }

    try {
      const config = JSON.parse(data)
      // 转换日期字符串为Date对象
      if (config.createdAt) {
        config.createdAt = new Date(config.createdAt)
      }
      if (config.updatedAt) {
        config.updatedAt = new Date(config.updatedAt)
      }
      return config
    } catch (error) {
      console.error('Failed to parse chart config:', error)
      return null
    }
  }

  /**
   * 删除图表配置
   */
  deleteConfig(id: string): boolean {
    const key = this.STORAGE_KEY_PREFIX + id
    localStorage.removeItem(key)
    return true
  }

  /**
   * 获取所有保存的图表配置
   */
  getAllConfigs(): ChartConfig[] {
    const configs: ChartConfig[] = []

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(this.STORAGE_KEY_PREFIX)) {
        const id = key.replace(this.STORAGE_KEY_PREFIX, '')
        const config = this.loadConfig(id)
        if (config) {
          configs.push(config)
        }
      }
    }

    // 按更新时间倒序排序
    return configs.sort((a, b) => {
      const timeA = a.updatedAt?.getTime() || 0
      const timeB = b.updatedAt?.getTime() || 0
      return timeB - timeA
    })
  }

  /**
   * 导出配置为JSON文件
   */
  exportConfigAsJSON(config: ChartConfig, filename?: string): void {
    const json = JSON.stringify(config, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.download = filename || `chart-config-${config.id}.json`
    link.href = url
    link.click()

    URL.revokeObjectURL(url)
  }

  /**
   * 从JSON文件导入配置
   */
  async importConfigFromJSON(file: File): Promise<ChartConfig> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()

      reader.onload = (e) => {
        try {
          const config = JSON.parse(e.target?.result as string)
          // 生成新ID避免冲突
          config.id = this.generateId()
          config.createdAt = new Date()
          config.updatedAt = new Date()
          resolve(config)
        } catch (error) {
          reject(new Error('Invalid JSON file'))
        }
      }

      reader.onerror = () => reject(new Error('Failed to read file'))
      reader.readAsText(file)
    })
  }

  /**
   * 保存图表模板
   */
  saveTemplate(template: ChartTemplate): void {
    const templates = this.getAllTemplates()
    const existingIndex = templates.findIndex(t => t.id === template.id)

    if (existingIndex >= 0) {
      templates[existingIndex] = template
    } else {
      templates.push(template)
    }

    localStorage.setItem(this.TEMPLATE_KEY, JSON.stringify(templates))
  }

  /**
   * 获取所有模板
   */
  getAllTemplates(): ChartTemplate[] {
    const data = localStorage.getItem(this.TEMPLATE_KEY)
    if (!data) {
      return this.getDefaultTemplates()
    }

    try {
      return JSON.parse(data)
    } catch (error) {
      console.error('Failed to parse templates:', error)
      return this.getDefaultTemplates()
    }
  }

  /**
   * 根据ID获取模板
   */
  getTemplate(id: string): ChartTemplate | null {
    const templates = this.getAllTemplates()
    return templates.find(t => t.id === id) || null
  }

  /**
   * 删除模板
   */
  deleteTemplate(id: string): boolean {
    const templates = this.getAllTemplates()
    const filtered = templates.filter(t => t.id !== id)

    if (filtered.length === templates.length) {
      return false // 模板不存在
    }

    localStorage.setItem(this.TEMPLATE_KEY, JSON.stringify(filtered))
    return true
  }

  /**
   * 从模板创建图表配置
   */
  createConfigFromTemplate(template: ChartTemplate, data: any): ChartConfig {
    return {
      id: this.generateId(),
      name: `${template.name} - ${new Date().toLocaleDateString()}`,
      type: template.type,
      data,
      options: { ...template.options },
      theme: template.theme,
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }

  /**
   * 获取默认模板
   */
  private getDefaultTemplates(): ChartTemplate[] {
    return [
      {
        id: 'default-bar',
        name: '标准柱状图',
        description: '适用于分类数据对比',
        type: 'bar',
        options: {
          showToolbar: true,
          showLegend: true,
          showToolbox: true,
          enableDataZoom: true
        },
        theme: 'light',
        category: '基础图表',
        tags: ['柱状图', '对比', '分类']
      },
      {
        id: 'default-line',
        name: '标准折线图',
        description: '适用于趋势分析',
        type: 'line',
        options: {
          showToolbar: true,
          showLegend: true,
          showToolbox: true,
          enableDataZoom: true
        },
        theme: 'light',
        category: '基础图表',
        tags: ['折线图', '趋势', '时间序列']
      },
      {
        id: 'default-pie',
        name: '标准饼图',
        description: '适用于占比分析',
        type: 'pie',
        options: {
          showToolbar: true,
          showLegend: true
        },
        theme: 'light',
        category: '基础图表',
        tags: ['饼图', '占比', '百分比']
      },
      {
        id: 'business-bar',
        name: '商务柱状图',
        description: '商务风格的柱状图',
        type: 'bar',
        options: {
          showToolbar: true,
          showLegend: true,
          showToolbox: true
        },
        theme: 'business',
        category: '商务图表',
        tags: ['柱状图', '商务', '专业']
      }
    ]
  }

  /**
   * 生成唯一ID
   */
  private generateId(): string {
    return `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}

// 导出单例
export const chartConfigService = new ChartConfigService()
