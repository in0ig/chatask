import { describe, test, expect } from 'vitest'
import { knowledgeBaseApi, knowledgeItemApi } from '@/services/api'

describe('API Path Correctness', () => {
  describe('Knowledge Base API Paths', () => {
    test('should use plural form for knowledge base endpoints', () => {
      // 测试获取知识库列表路径
      const getKnowledgeBasesPath = extractPath(knowledgeBaseApi.getKnowledgeBases)
      expect(getKnowledgeBasesPath).toBe('/knowledge-bases')
      
      // 测试创建知识库路径
      const createKnowledgeBasePath = extractPath(knowledgeBaseApi.createKnowledgeBase)
      expect(createKnowledgeBasePath).toBe('/knowledge-bases')
    })
    
    test('should use plural form for knowledge base item operations', () => {
      // 测试更新知识库路径模式
      const updatePath = extractPathPattern(knowledgeBaseApi.updateKnowledgeBase)
      expect(updatePath).toMatch(/^\/knowledge-bases\/\$\{.*\}$/)
      
      // 测试删除知识库路径模式
      const deletePath = extractPathPattern(knowledgeBaseApi.deleteKnowledgeBase)
      expect(deletePath).toMatch(/^\/knowledge-bases\/\$\{.*\}$/)
    })
    
    test('should follow RESTful conventions', () => {
      const paths = [
        extractPath(knowledgeBaseApi.getKnowledgeBases),
        extractPath(knowledgeBaseApi.createKnowledgeBase)
      ]
      
      paths.forEach(path => {
        // 应该使用 kebab-case
        expect(path).toMatch(/^\/[a-z-]+$/)
        // 不应该包含下划线
        expect(path).not.toContain('_')
        // 应该使用复数形式
        expect(path).toBe('/knowledge-bases')
      })
    })
  })
  
  describe('Knowledge Item API Paths', () => {
    test('should use plural form for knowledge item endpoints', () => {
      // 测试创建知识项路径
      const createKnowledgeItemPath = extractPath(knowledgeItemApi.createKnowledgeItem)
      expect(createKnowledgeItemPath).toBe('/knowledge-items')
    })
    
    test('should use plural form for knowledge item operations', () => {
      // 测试更新知识项路径模式
      const updatePath = extractPathPattern(knowledgeItemApi.updateKnowledgeItem)
      expect(updatePath).toMatch(/^\/knowledge-items\/\$\{.*\}$/)
      
      // 测试删除知识项路径模式
      const deletePath = extractPathPattern(knowledgeItemApi.deleteKnowledgeItem)
      expect(deletePath).toMatch(/^\/knowledge-items\/\$\{.*\}$/)
    })
    
    test('should use correct nested resource path for knowledge base items', () => {
      // 测试获取知识库相关知识项的路径模式
      const getItemsPath = extractPathPattern(knowledgeItemApi.getItemsByKnowledgeBase)
      expect(getItemsPath).toMatch(/^\/knowledge-items\/knowledge-base\/\$\{.*\}\/items$/)
    })
    
    test('should follow RESTful conventions', () => {
      const createPath = extractPath(knowledgeItemApi.createKnowledgeItem)
      
      // 应该使用 kebab-case
      expect(createPath).toMatch(/^\/[a-z-]+$/)
      // 不应该包含下划线
      expect(createPath).not.toContain('_')
      // 应该使用复数形式
      expect(createPath).toBe('/knowledge-items')
    })
  })
  
  describe('API Path Standards', () => {
    test('all API paths should not contain duplicate segments', () => {
      const allPaths = [
        extractPath(knowledgeBaseApi.getKnowledgeBases),
        extractPath(knowledgeBaseApi.createKnowledgeBase),
        extractPath(knowledgeItemApi.createKnowledgeItem)
      ]
      
      allPaths.forEach(path => {
        const segments = path.split('/').filter(segment => segment !== '')
        const uniqueSegments = [...new Set(segments)]
        expect(segments.length).toBe(uniqueSegments.length)
      })
    })
    
    test('all API paths should use consistent naming', () => {
      const resourcePaths = [
        extractPath(knowledgeBaseApi.getKnowledgeBases),
        extractPath(knowledgeItemApi.createKnowledgeItem)
      ]
      
      resourcePaths.forEach(path => {
        // 应该以斜杠开头
        expect(path).toMatch(/^\//)
        // 应该使用 kebab-case 而不是 camelCase 或 snake_case
        expect(path).toMatch(/^\/[a-z-]+$/)
        // 不应该包含大写字母
        expect(path).not.toMatch(/[A-Z]/)
      })
    })
  })
})

// 辅助函数：从 API 函数中提取路径
function extractPath(apiFunction: Function): string {
  const functionString = apiFunction.toString()
  const pathMatch = functionString.match(/service\.(get|post|put|delete)\(['"`]([^'"`]+)['"`]/)
  return pathMatch ? pathMatch[2] : ''
}

// 辅助函数：从带参数的 API 函数中提取路径模式
function extractPathPattern(apiFunction: Function): string {
  const functionString = apiFunction.toString()
  // 匹配模板字符串路径
  const pathMatch = functionString.match(/service\.(get|post|put|delete)\(`([^`]+)`/)
  return pathMatch ? pathMatch[2] : ''
}