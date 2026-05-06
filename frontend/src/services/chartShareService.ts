/**
 * 图表分享服务
 * 支持生成分享链接和嵌入代码
 */

import type { ChartConfig, ShareConfig } from '@/types/chart'

export class ChartShareService {
  private readonly SHARE_BASE_URL = window.location.origin + '/share/chart/'

  /**
   * 生成分享链接
   */
  generateShareLink(config: ChartConfig, options?: {
    expiresInDays?: number
    password?: string
  }): ShareConfig {
    const chartId = config.id || this.generateId()

    // 保存图表配置到localStorage（实际应用中应该保存到服务器）
    const shareKey = `share_${chartId}`
    const shareData = {
      config,
      createdAt: new Date(),
      expiresAt: options?.expiresInDays
        ? new Date(Date.now() + options.expiresInDays * 24 * 60 * 60 * 1000)
        : undefined,
      password: options?.password,
      accessCount: 0
    }

    localStorage.setItem(shareKey, JSON.stringify(shareData))

    const shareUrl = `${this.SHARE_BASE_URL}${chartId}`

    return {
      chartId,
      shareUrl,
      embedCode: this.generateEmbedCode(chartId),
      expiresAt: shareData.expiresAt,
      accessCount: 0
    }
  }

  /**
   * 生成嵌入代码
   */
  generateEmbedCode(chartId: string, options?: {
    width?: string
    height?: string
    theme?: string
  }): string {
    const width = options?.width || '100%'
    const height = options?.height || '400px'
    const theme = options?.theme || 'light'

    const embedUrl = `${this.SHARE_BASE_URL}${chartId}?embed=true&theme=${theme}`

    return `<iframe 
  src="${embedUrl}" 
  width="${width}" 
  height="${height}" 
  frameborder="0" 
  scrolling="no"
  style="border: none;"
></iframe>`
  }

  /**
   * 获取分享的图表配置
   */
  getSharedChart(chartId: string, password?: string): ChartConfig | null {
    const shareKey = `share_${chartId}`
    const data = localStorage.getItem(shareKey)

    if (!data) {
      return null
    }

    try {
      const shareData = JSON.parse(data)

      // 检查是否过期
      if (shareData.expiresAt) {
        const expiresAt = new Date(shareData.expiresAt)
        if (expiresAt < new Date()) {
          localStorage.removeItem(shareKey)
          return null
        }
      }

      // 检查密码
      if (shareData.password && shareData.password !== password) {
        throw new Error('Invalid password')
      }

      // 增加访问计数
      shareData.accessCount = (shareData.accessCount || 0) + 1
      localStorage.setItem(shareKey, JSON.stringify(shareData))

      return shareData.config
    } catch (error) {
      console.error('Failed to get shared chart:', error)
      return null
    }
  }

  /**
   * 删除分享
   */
  deleteShare(chartId: string): boolean {
    const shareKey = `share_${chartId}`
    localStorage.removeItem(shareKey)
    return true
  }

  /**
   * 获取分享统计
   */
  getShareStats(chartId: string): {
    accessCount: number
    createdAt: Date
    expiresAt?: Date
  } | null {
    const shareKey = `share_${chartId}`
    const data = localStorage.getItem(shareKey)

    if (!data) {
      return null
    }

    try {
      const shareData = JSON.parse(data)
      return {
        accessCount: shareData.accessCount || 0,
        createdAt: new Date(shareData.createdAt),
        expiresAt: shareData.expiresAt ? new Date(shareData.expiresAt) : undefined
      }
    } catch (error) {
      console.error('Failed to get share stats:', error)
      return null
    }
  }

  /**
   * 复制到剪贴板
   */
  async copyToClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (error) {
      // 降级方案：使用传统方法
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()

      try {
        document.execCommand('copy')
        document.body.removeChild(textarea)
        return true
      } catch (err) {
        document.body.removeChild(textarea)
        return false
      }
    }
  }

  /**
   * 生成唯一ID
   */
  private generateId(): string {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}

// 导出单例
export const chartShareService = new ChartShareService()
