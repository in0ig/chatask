/**
 * ChartShareService 测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChartShareService } from '@/services/chartShareService'
import type { ChartConfig } from '@/types/chart'

describe('ChartShareService', () => {
  let service: ChartShareService

  const mockConfig: ChartConfig = {
    id: 'test-chart',
    name: '测试图表',
    type: 'bar',
    data: {
      columns: ['类别', '数值'],
      rows: [['A', 100], ['B', 200]]
    },
    options: {},
    theme: 'light'
  }

  beforeEach(() => {
    service = new ChartShareService()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('generateShareLink', () => {
    it('应该能够生成分享链接', () => {
      const shareConfig = service.generateShareLink(mockConfig)

      expect(shareConfig.chartId).toBeTruthy()
      expect(shareConfig.shareUrl).toContain('/share/chart/')
      expect(shareConfig.embedCode).toContain('<iframe')
    })

    it('应该支持设置过期时间', () => {
      const shareConfig = service.generateShareLink(mockConfig, {
        expiresInDays: 7
      })

      expect(shareConfig.expiresAt).toBeInstanceOf(Date)
      
      const now = new Date()
      const expiresAt = shareConfig.expiresAt!
      const diffDays = Math.floor((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
      
      expect(diffDays).toBeGreaterThanOrEqual(6)
      expect(diffDays).toBeLessThanOrEqual(7)
    })

    it('生成的分享链接应该可以访问', () => {
      const shareConfig = service.generateShareLink(mockConfig)
      const retrieved = service.getSharedChart(shareConfig.chartId)

      expect(retrieved).toBeTruthy()
      expect(retrieved?.name).toBe(mockConfig.name)
    })
  })

  describe('generateEmbedCode', () => {
    it('应该生成正确的嵌入代码', () => {
      const embedCode = service.generateEmbedCode('test-id')

      expect(embedCode).toContain('<iframe')
      expect(embedCode).toContain('test-id')
      expect(embedCode).toContain('width=')
      expect(embedCode).toContain('height=')
    })

    it('应该支持自定义尺寸', () => {
      const embedCode = service.generateEmbedCode('test-id', {
        width: '800px',
        height: '600px'
      })

      expect(embedCode).toContain('width="800px"')
      expect(embedCode).toContain('height="600px"')
    })

    it('应该支持自定义主题', () => {
      const embedCode = service.generateEmbedCode('test-id', {
        theme: 'dark'
      })

      expect(embedCode).toContain('theme=dark')
    })
  })

  describe('getSharedChart', () => {
    it('应该能够获取分享的图表', () => {
      const shareConfig = service.generateShareLink(mockConfig)
      const chart = service.getSharedChart(shareConfig.chartId)

      expect(chart).toBeTruthy()
      expect(chart?.name).toBe(mockConfig.name)
    })

    it('获取不存在的分享应该返回null', () => {
      const chart = service.getSharedChart('non-existent-id')
      expect(chart).toBeNull()
    })

    it('获取过期的分享应该返回null', () => {
      // 创建一个已过期的分享
      const shareConfig = service.generateShareLink(mockConfig, {
        expiresInDays: -1 // 负数表示已过期
      })

      const chart = service.getSharedChart(shareConfig.chartId)
      expect(chart).toBeNull()
    })

    it('应该增加访问计数', () => {
      const shareConfig = service.generateShareLink(mockConfig)
      
      service.getSharedChart(shareConfig.chartId)
      service.getSharedChart(shareConfig.chartId)
      
      const stats = service.getShareStats(shareConfig.chartId)
      expect(stats?.accessCount).toBe(2)
    })
  })

  describe('deleteShare', () => {
    it('应该能够删除分享', () => {
      const shareConfig = service.generateShareLink(mockConfig)
      const deleted = service.deleteShare(shareConfig.chartId)

      expect(deleted).toBe(true)
      expect(service.getSharedChart(shareConfig.chartId)).toBeNull()
    })
  })

  describe('getShareStats', () => {
    it('应该能够获取分享统计', () => {
      const shareConfig = service.generateShareLink(mockConfig)
      const stats = service.getShareStats(shareConfig.chartId)

      expect(stats).toBeTruthy()
      expect(stats?.accessCount).toBe(0)
      expect(stats?.createdAt).toBeInstanceOf(Date)
    })

    it('不存在的分享应该返回null', () => {
      const stats = service.getShareStats('non-existent-id')
      expect(stats).toBeNull()
    })
  })

  describe('copyToClipboard', () => {
    it('应该能够复制文本到剪贴板', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn(() => Promise.resolve())
        }
      })

      const success = await service.copyToClipboard('test text')
      expect(success).toBe(true)
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text')
    })

    it('clipboard API失败时应该使用降级方案', async () => {
      // Mock clipboard API failure
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn(() => Promise.reject(new Error('Not allowed')))
        }
      })

      // Mock document.execCommand
      document.execCommand = vi.fn(() => true)

      const mockTextarea = {
        value: '',
        style: {},
        select: vi.fn()
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockTextarea as any)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockTextarea as any)
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockTextarea as any)

      const success = await service.copyToClipboard('test text')
      expect(success).toBe(true)
    })
  })
})
