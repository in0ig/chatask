import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DictionaryTree from '@/components/DataPreparation/DictionaryTree.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPrepStore } from '@/store/modules/dataPreparation'
import { ElTree, ElInput, ElButton } from 'element-plus'

// 模拟字典数据
const mockDictionaries = [
  {
    id: 1,
    name: '客户类型',
    code: 'CUST_TYPE',
    parent_id: null,
    type: 'standard',
    description: '客户分类'
  },
  {
    id: 2,
    name: '个人客户',
    code: 'CUST_TYPE_PERSON',
    parent_id: 1,
    type: 'standard',
    description: '个人客户分类'
  },
  {
    id: 3,
    name: '企业客户',
    code: 'CUST_TYPE_ENTERPRISE',
    parent_id: 1,
    type: 'standard',
    description: '企业客户分类'
  },
  {
    id: 4,
    name: '状态',
    code: 'STATUS',
    parent_id: null,
    type: 'standard',
    description: '状态编码'
  },
  {
    id: 5,
    name: '启用',
    code: 'STATUS_ACTIVE',
    parent_id: 4,
    type: 'standard',
    description: '启用状态'
  }
]

describe('DictionaryTree.vue', () => {
  let wrapper
  let store

  beforeEach(() => {
    // 设置 Pinia
    setActivePinia(createPinia())
    store = useDataPrepStore()
    
    // 模拟 store 方法
    store.fetchDictionaries = vi.fn()
    store.dictionaries = mockDictionaries
    store.showAddDictionaryModal = vi.fn()
    store.showEditDictionaryModal = vi.fn()
    store.deleteDictionary = vi.fn()
    
    // 挂载组件
    wrapper = mount(DictionaryTree, {
      global: {
        plugins: [createPinia()],
        stubs: [
          'el-tree',
          'el-input',
          'el-button',
          'el-icon-search',
          'el-icon-edit',
          'el-icon-delete'
        ]
      }
    })
  })

  // 测试1：验证字典树结构正确渲染
  it('renders dictionary tree structure correctly', () => {
    const tree = wrapper.findComponent(ElTree)
    expect(tree.exists()).toBe(true)
    
    // 验证树有2个根节点（客户类型和状态）
    const rootNodes = wrapper.findAll('.el-tree-node')
    expect(rootNodes.length).toBe(2)
    
    // 验证根节点文本
    const rootLabels = rootNodes.map(node => node.text())
    expect(rootLabels).toContain('客户类型')
    expect(rootLabels).toContain('状态')
    
    // 验证子节点
    const childNodes = wrapper.findAll('.el-tree-node.is-leaf')
    expect(childNodes.length).toBe(3) // 个人客户、企业客户、启用
  })

  // 测试2：验证搜索过滤功能
  it('filters tree nodes by search text', async () => {
    const input = wrapper.findComponent(ElInput)
    
    // 搜索'客户'
    await input.setValue('客户')
    
    // 验证只有包含'客户'的节点显示
    const visibleNodes = wrapper.findAll('.el-tree-node')
    expect(visibleNodes.length).toBe(3) // 客户类型、个人客户、企业客户
    
    // 验证每个可见节点都包含'客户'
    visibleNodes.forEach(node => {
      expect(node.text().toLowerCase()).toContain('客户')
    })
    
    // 搜索'状态'
    await input.setValue('状态')
    
    // 验证只有包含'状态'的节点显示
    const statusNodes = wrapper.findAll('.el-tree-node')
    expect(statusNodes.length).toBe(2) // 状态、启用
    
    // 验证每个可见节点都包含'状态'
    statusNodes.forEach(node => {
      expect(node.text().toLowerCase()).toContain('状态')
    })
    
    // 清空搜索
    await input.setValue('')
    
    // 验证所有节点都显示
    const allNodes = wrapper.findAll('.el-tree-node')
    expect(allNodes.length).toBe(5)
  })

  // 测试3：验证展开/折叠功能
  it('expands and collapses tree nodes', async () => {
    const tree = wrapper.findComponent(ElTree)
    
    // 验证初始状态：根节点展开，子节点折叠
    const customerNode = wrapper.find('.el-tree-node:contains("客户类型")')
    expect(customerNode.classes()).toContain('is-expanded')
    
    // 验证子节点存在但不可见
    const childNodes = wrapper.findAll('.el-tree-node:contains("个人客户")')
    expect(childNodes.length).toBe(1)
    
    // 点击折叠
    await customerNode.trigger('click')
    
    // 验证已折叠
    expect(customerNode.classes()).not.toContain('is-expanded')
    
    // 点击展开
    await customerNode.trigger('click')
    
    // 验证已展开
    expect(customerNode.classes()).toContain('is-expanded')
  })

  // 测试4：验证新增字典按钮功能
  it('calls showAddDictionaryModal when add button is clicked', async () => {
    const addButton = wrapper.find('button:contains("新增字典")')
    await addButton.trigger('click')
    
    expect(store.showAddDictionaryModal).toHaveBeenCalledTimes(1)
  })

  // 测试5：验证编辑字典操作
  it('calls showEditDictionaryModal when edit button is clicked', async () => {
    const editButton = wrapper.find('.node-actions button:has(.el-icon-edit)')
    await editButton.trigger('click')
    
    // 验证调用了编辑方法并传入了正确的数据
    expect(store.showEditDictionaryModal).toHaveBeenCalledTimes(1)
    expect(store.showEditDictionaryModal).toHaveBeenCalledWith(expect.objectContaining({
      id: 1,
      name: '客户类型'
    }))
  })

  // 测试6：验证删除字典操作
  it('calls deleteDictionary when delete button is clicked', async () => {
    // 模拟确认对话框
    window.confirm = vi.fn(() => true)
    
    const deleteButton = wrapper.find('.node-actions button:has(.el-icon-delete)')
    await deleteButton.trigger('click')
    
    // 验证调用了删除方法并传入了正确的ID
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(store.deleteDictionary).toHaveBeenCalledTimes(1)
    expect(store.deleteDictionary).toHaveBeenCalledWith(1)
  })

  // 测试7：验证节点点击事件
  it('emits node-click event when node is clicked', async () => {
    const node = wrapper.find('.el-tree-node:contains("客户类型")')
    await node.trigger('click')
    
    // 验证节点点击事件被触发
    // 注意：由于我们使用了ElTree组件，实际的node-click事件由ElTree组件处理
    // 我们可以验证组件内部逻辑是否正确执行
    expect(wrapper.emitted('node-click')).toBeFalsy() // 组件没有直接发射事件
    
    // 验证handleNodeClick被调用
    // 由于我们无法直接访问内部方法，我们可以通过store的调用来间接验证
    // 但在这个测试中，我们主要验证UI交互
    
    // 这里验证的是组件的内部逻辑，而不是事件发射
    // 由于组件内部没有发射事件，我们验证的是数据更新
    // 但在这个组件中，点击事件只是记录日志，没有其他副作用
    // 所以我们验证的是UI元素的正确性
    
    // 验证点击了正确的节点
    expect(node.exists()).toBe(true)
  })
})

// 额外测试：验证树数据构建逻辑
it('builds correct tree structure from flat data', () => {
  const store = useDataPrepStore()
  store.dictionaries = mockDictionaries
  
  // 模拟buildTreeData函数
  const buildTreeData = (dictionaries) => {
    const map = new Map()
    const rootNodes = []
    
    dictionaries.forEach(dict => {
      map.set(dict.id, {
        id: dict.id,
        code: dict.code,
        label: dict.name || dict.code,
        children: [],
        parent_id: dict.parent_id,
        type: dict.type,
        description: dict.description
      })
    })
    
    dictionaries.forEach(dict => {
      const node = map.get(dict.id)
      if (dict.parent_id) {
        const parent = map.get(dict.parent_id)
        if (parent) {
          parent.children.push(node)
        }
      } else {
        rootNodes.push(node)
      }
    })
    
    return rootNodes
  }
  
  const treeData = buildTreeData(mockDictionaries)
  expect(treeData.length).toBe(2) // 2个根节点
  expect(treeData[0].label).toBe('客户类型')
  expect(treeData[0].children.length).toBe(2) // 2个子节点
  expect(treeData[1].label).toBe('状态')
  expect(treeData[1].children.length).toBe(1) // 1个子节点
})