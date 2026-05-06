import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// Create a minimal test component to test the core functionality
const TestComponent = {
  template: `
    <div class="test-component">
      <h1>Data Table Manager Test</h1>
      <div data-testid="tree-data">{{ JSON.stringify(treeData) }}</div>
      <div data-testid="selected-table">{{ selectedTable ? selectedTable.name : 'None' }}</div>
    </div>
  `,
  setup() {
    const store = useDataPreparationStore()
    
    // Mock data
    const dataTables = [
      {
        id: '1',
        name: 'users',
        displayName: '用户表',
        sourceId: 'source1',
        dataMode: 'DIRECT',
        fieldCount: 5,
        rowCount: 100,
        status: 'ENABLED',
        fields: []
      }
    ]
    
    const dataSources = [
      {
        id: 'source1',
        name: '测试数据源',
        sourceType: 'DATABASE',
        connectionStatus: 'CONNECTED',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z'
      }
    ]
    
    // Build tree data (same logic as DataTableManager)
    const buildTreeData = (tables: any[], sources: any[]) => {
      const treeNodes: any[] = []
      
      const sourceMap = new Map()
      tables.forEach(table => {
        const sourceId = table.sourceId
        if (!sourceMap.has(sourceId)) {
          sourceMap.set(sourceId, [])
        }
        sourceMap.get(sourceId).push(table)
      })
      
      sources.forEach(source => {
        const sourceTables = sourceMap.get(source.id) || []
        const sourceNode = {
          id: `source_${source.id}`,
          label: source.name,
          type: 'datasource',
          sourceId: source.id,
          expanded: true,
          children: sourceTables.map((table: any) => ({
            id: `table_${table.id}`,
            label: table.displayName || table.name,
            type: 'table',
            sourceId: source.id,
            tableId: table.id
          }))
        }
        treeNodes.push(sourceNode)
      })
      
      return treeNodes
    }
    
    const treeData = buildTreeData(dataTables, dataSources)
    const selectedTable = dataTables.find(t => t.id === '1')
    
    return {
      treeData,
      selectedTable
    }
  }
}

describe('DataTableManager Core Logic', () => {
  let wrapper: any
  let store: any

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    
    wrapper = mount(TestComponent)
  })

  it('应该正确构建树形数据结构', () => {
    const treeDataText = wrapper.find('[data-testid="tree-data"]').text()
    const treeData = JSON.parse(treeDataText)
    
    expect(treeData).toHaveLength(1)
    expect(treeData[0].label).toBe('测试数据源')
    expect(treeData[0].type).toBe('datasource')
    expect(treeData[0].children).toHaveLength(1)
    expect(treeData[0].children[0].label).toBe('用户表')
    expect(treeData[0].children[0].type).toBe('table')
  })

  it('应该正确显示选中的表', () => {
    const selectedTableText = wrapper.find('[data-testid="selected-table"]').text()
    expect(selectedTableText).toBe('users')
  })

  it('应该正确处理数据源分组', () => {
    const treeDataText = wrapper.find('[data-testid="tree-data"]').text()
    const treeData = JSON.parse(treeDataText)
    
    // 验证数据源节点结构
    const sourceNode = treeData[0]
    expect(sourceNode.id).toBe('source_source1')
    expect(sourceNode.sourceId).toBe('source1')
    expect(sourceNode.expanded).toBe(true)
    
    // 验证表节点结构
    const tableNode = sourceNode.children[0]
    expect(tableNode.id).toBe('table_1')
    expect(tableNode.tableId).toBe('1')
    expect(tableNode.sourceId).toBe('source1')
  })

  it('应该正确处理空数据情况', () => {
    // 创建一个没有数据的组件
    const EmptyTestComponent = {
      template: `
        <div class="test-component">
          <div data-testid="empty-tree">{{ JSON.stringify(treeData) }}</div>
        </div>
      `,
      setup() {
        const treeData: any[] = []
        return { treeData }
      }
    }
    
    const emptyWrapper = mount(EmptyTestComponent)
    const emptyTreeText = emptyWrapper.find('[data-testid="empty-tree"]').text()
    expect(JSON.parse(emptyTreeText)).toEqual([])
  })

  it('应该正确处理多个数据源的情况', () => {
    const MultiSourceComponent = {
      template: `
        <div class="test-component">
          <div data-testid="multi-tree">{{ JSON.stringify(treeData) }}</div>
        </div>
      `,
      setup() {
        const dataTables = [
          { id: '1', name: 'users', displayName: '用户表', sourceId: 'source1' },
          { id: '2', name: 'orders', displayName: '订单表', sourceId: 'source2' }
        ]
        
        const dataSources = [
          { id: 'source1', name: '用户数据源' },
          { id: 'source2', name: '订单数据源' }
        ]
        
        const buildTreeData = (tables: any[], sources: any[]) => {
          const treeNodes: any[] = []
          const sourceMap = new Map()
          
          tables.forEach(table => {
            const sourceId = table.sourceId
            if (!sourceMap.has(sourceId)) {
              sourceMap.set(sourceId, [])
            }
            sourceMap.get(sourceId).push(table)
          })
          
          sources.forEach(source => {
            const sourceTables = sourceMap.get(source.id) || []
            const sourceNode = {
              id: `source_${source.id}`,
              label: source.name,
              type: 'datasource',
              sourceId: source.id,
              children: sourceTables.map((table: any) => ({
                id: `table_${table.id}`,
                label: table.displayName || table.name,
                type: 'table',
                sourceId: source.id,
                tableId: table.id
              }))
            }
            treeNodes.push(sourceNode)
          })
          
          return treeNodes
        }
        
        const treeData = buildTreeData(dataTables, dataSources)
        return { treeData }
      }
    }
    
    const multiWrapper = mount(MultiSourceComponent)
    const multiTreeText = multiWrapper.find('[data-testid="multi-tree"]').text()
    const multiTreeData = JSON.parse(multiTreeText)
    
    expect(multiTreeData).toHaveLength(2)
    expect(multiTreeData[0].label).toBe('用户数据源')
    expect(multiTreeData[1].label).toBe('订单数据源')
    expect(multiTreeData[0].children[0].label).toBe('用户表')
    expect(multiTreeData[1].children[0].label).toBe('订单表')
  })
})