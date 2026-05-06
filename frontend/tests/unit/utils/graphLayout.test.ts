import { describe, it, expect } from 'vitest'
import { simpleForceLayout, type Node, type Link } from '@/utils/graphLayout'

describe('graphLayout', () => {
  describe('simpleForceLayout', () => {
    it('应该正确处理空节点数组', () => {
      const nodes: Node[] = []
      const links: Link[] = []
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      expect(result).toEqual([])
    })

    it('应该为节点分配位置', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' },
        { id: 'node3' }
      ]
      const links: Link[] = []
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      expect(result.length).toBe(3)
      result.forEach(node => {
        expect(node.x).toBeDefined()
        expect(node.y).toBeDefined()
        expect(node.vx).toBeDefined()
        expect(node.vy).toBeDefined()
        expect(typeof node.x).toBe('number')
        expect(typeof node.y).toBe('number')
      })
    })

    it('应该将节点位置限制在边界内', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' }
      ]
      const links: Link[] = []
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      result.forEach(node => {
        expect(node.x!).toBeGreaterThanOrEqual(0)
        expect(node.x!).toBeLessThanOrEqual(800)
        expect(node.y!).toBeGreaterThanOrEqual(0)
        expect(node.y!).toBeLessThanOrEqual(600)
      })
    })

    it('应该处理带有连接的节点', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' },
        { id: 'node3' }
      ]
      const links: Link[] = [
        { source: 'node1', target: 'node2' },
        { source: 'node2', target: 'node3' }
      ]
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      expect(result.length).toBe(3)
      result.forEach(node => {
        expect(node.x).toBeDefined()
        expect(node.y).toBeDefined()
      })
    })

    it('应该处理 Node 对象作为连接源和目标', () => {
      const node1: Node = { id: 'node1' }
      const node2: Node = { id: 'node2' }
      const nodes: Node[] = [node1, node2]
      const links: Link[] = [
        { source: node1, target: node2 }
      ]
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      expect(result.length).toBe(2)
      result.forEach(node => {
        expect(node.x).toBeDefined()
        expect(node.y).toBeDefined()
      })
    })

    it('应该使用自定义选项', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' }
      ]
      const links: Link[] = []
      const options = {
        width: 400,
        height: 300,
        iterations: 50,
        chargeStrength: -50,
        linkDistance: 100
      }
      
      const result = simpleForceLayout(nodes, links, options)
      
      result.forEach(node => {
        expect(node.x!).toBeGreaterThanOrEqual(0)
        expect(node.x!).toBeLessThanOrEqual(400)
        expect(node.y!).toBeGreaterThanOrEqual(0)
        expect(node.y!).toBeLessThanOrEqual(300)
      })
    })

    it('应该保留现有的节点位置', () => {
      const nodes: Node[] = [
        { id: 'node1', x: 100, y: 200 },
        { id: 'node2', x: 300, y: 400 }
      ]
      const links: Link[] = []
      const options = { width: 800, height: 600, iterations: 1 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      // 由于迭代次数很少，位置应该接近原始位置
      expect(result[0].x).toBeCloseTo(100, 0)
      expect(result[0].y).toBeCloseTo(200, 0)
    })

    it('应该处理不存在的连接节点', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' }
      ]
      const links: Link[] = [
        { source: 'node1', target: 'nonexistent' },
        { source: 'node2', target: 'node1' }
      ]
      const options = { width: 800, height: 600 }
      
      // 应该不抛出错误
      expect(() => {
        simpleForceLayout(nodes, links, options)
      }).not.toThrow()
    })

    it('应该应用阻尼效果', () => {
      const nodes: Node[] = [
        { id: 'node1', vx: 10, vy: 10 }
      ]
      const links: Link[] = []
      const options = { width: 800, height: 600, iterations: 1 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      // 速度应该被阻尼减小
      expect(Math.abs(result[0].vx!)).toBeLessThan(10)
      expect(Math.abs(result[0].vy!)).toBeLessThan(10)
    })

    it('应该处理单个节点', () => {
      const nodes: Node[] = [{ id: 'single' }]
      const links: Link[] = []
      const options = { width: 800, height: 600 }
      
      const result = simpleForceLayout(nodes, links, options)
      
      expect(result.length).toBe(1)
      expect(result[0].x).toBeDefined()
      expect(result[0].y).toBeDefined()
    })

    it('应该使用默认选项值', () => {
      const nodes: Node[] = [
        { id: 'node1' },
        { id: 'node2' }
      ]
      const links: Link[] = []
      const options = { width: 800, height: 600 }
      
      // 应该不抛出错误，使用默认的 iterations, chargeStrength, linkDistance
      expect(() => {
        simpleForceLayout(nodes, links, options)
      }).not.toThrow()
    })
  })
})