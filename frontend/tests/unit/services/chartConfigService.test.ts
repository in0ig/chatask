/**
 * ChartConfigService 测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChartConfigService } from '@/services/chartConfigService'
import type { ChartConfig, ChartTemplate } from '@/types/chart'

describe('ChartConfigService', () => {
  let service: ChartConfigService

  const mockConfig: ChartConfig = {
    name: '测试配置',
    type: 'bar',
    data: {
      columns: ['类别', '数值'],
      rows: [['A', 100], ['B', 200]]
    },
    options: { showToolbar: true },
    theme: 'light'
  }

  beforeEach(() => {
    service = new ChartConfigService()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('saveConfig', () => {
    it('应该能够保存图表配置', () => {
      const id = service.saveConfig(mockConfig)

      expect(id).toBeTruthy()
      expect(typeof id).toBe('string')
    })

    it('保存的配置应该包含ID和时间戳', () => {
      const id = service.saveConfig(mockConfig)
      const loaded = service.loadConfig(id)

      expect(loaded).toBeTruthy()
      expect(loaded?.id).toBe(id)
      expect(loaded?.createdAt).toBeInstanceOf(Date)
      expect(loaded?.updatedAt).toBeInstanceOf(Date)
    })

    it('应该能够更新已存在的配置', () => {
      const id = service.saveConfig(mockConfig)
      
      const updatedConfig = { ...mockConfig, id, name: '更新后的配置' }
      service.saveConfig(updatedConfig)

      const loaded = service.loadConfig(id)
      expect(loaded?.name).toBe('更新后的配置')
    })
  })

  describe('loadConfig', () => {
    it('应该能够加载已保存的配置', () => {
      const id = service.saveConfig(mockConfig)
      const loaded = service.loadConfig(id)

      expect(loaded).toBeTruthy()
      expect(loaded?.name).toBe(mockConfig.name)
      expect(loaded?.type).toBe(mockConfig.type)
    })

    it('加载不存在的配置应该返回null', () => {
      const loaded = service.loadConfig('non-existent-id')
      expect(loaded).toBeNull()
    })
  })

  describe('deleteConfig', () => {
    it('应该能够删除配置', () => {
      const id = service.saveConfig(mockConfig)
      const deleted = service.deleteConfig(id)

      expect(deleted).toBe(true)
      expect(service.loadConfig(id)).toBeNull()
    })
  })

  describe('getAllConfigs', () => {
    it('应该返回所有保存的配置', () => {
      service.saveConfig({ ...mockConfig, name: '配置1' })
      service.saveConfig({ ...mockConfig, name: '配置2' })
      service.saveConfig({ ...mockConfig, name: '配置3' })

      const configs = service.getAllConfigs()
      expect(configs).toHaveLength(3)
    })

    it('返回的配置应该按更新时间倒序排列', async () => {
      const id1 = service.saveConfig({ ...mockConfig, name: '配置1' })
      
      // 等待一小段时间确保时间戳不同
      await new Promise(resolve => setTimeout(resolve, 10))
      
      const id2 = service.saveConfig({ ...mockConfig, name: '配置2' })

      const configs = service.getAllConfigs()
      expect(configs[0].name).toBe('配置2')
      expect(configs[1].name).toBe('配置1')
    })
  })

  describe('模板管理', () => {
    const mockTemplate: ChartTemplate = {
      id: 'test-template',
      name: '测试模板',
      type: 'bar',
      options: { showToolbar: true },
      theme: 'light'
    }

    it('应该能够保存模板', () => {
      service.saveTemplate(mockTemplate)
      const templates = service.getAllTemplates()

      const saved = templates.find(t => t.id === mockTemplate.id)
      expect(saved).toBeTruthy()
      expect(saved?.name).toBe(mockTemplate.name)
    })

    it('应该能够获取模板', () => {
      service.saveTemplate(mockTemplate)
      const template = service.getTemplate(mockTemplate.id)

      expect(template).toBeTruthy()
      expect(template?.id).toBe(mockTemplate.id)
    })

    it('应该能够删除模板', () => {
      service.saveTemplate(mockTemplate)
      const deleted = service.deleteTemplate(mockTemplate.id)

      expect(deleted).toBe(true)
      expect(service.getTemplate(mockTemplate.id)).toBeNull()
    })

    it('应该返回默认模板', () => {
      const templates = service.getAllTemplates()
      expect(templates.length).toBeGreaterThan(0)
    })

    it('应该能够从模板创建配置', () => {
      const config = service.createConfigFromTemplate(mockTemplate, mockConfig.data)

      expect(config.type).toBe(mockTemplate.type)
      expect(config.theme).toBe(mockTemplate.theme)
      expect(config.data).toBe(mockConfig.data)
    })
  })

  describe('导入导出', () => {
    it('应该能够导出配置为JSON', () => {
      const id = service.saveConfig(mockConfig)
      const config = service.loadConfig(id)!

      // Mock URL.createObjectURL
      global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
      global.URL.revokeObjectURL = vi.fn()

      const mockLink = {
        click: vi.fn(),
        download: '',
        href: ''
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)

      service.exportConfigAsJSON(config)

      expect(mockLink.click).toHaveBeenCalled()
    })

    it('应该能够从JSON导入配置', async () => {
      const jsonContent = JSON.stringify(mockConfig)
      const file = new File([jsonContent], 'config.json', { type: 'application/json' })

      const imported = await service.importConfigFromJSON(file)

      expect(imported.name).toBe(mockConfig.name)
      expect(imported.type).toBe(mockConfig.type)
      expect(imported.id).toBeTruthy()
    })
  })
})
