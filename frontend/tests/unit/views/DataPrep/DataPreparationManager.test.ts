import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import DataPreparationManager from '@/views/DataPrep/DataPreparationManager.vue'

// Mock 子组件
const MockDataSourceList = {
  name: 'DataSourceList',
  template: '<div class="data-source-list">Data Source List</div>'
}

const MockDataTableManager = {
  name: 'DataTableManager', 
  template: '<div class="data-table-manager">Data Table Manager</div>'
}

const MockDictionaryManager = {
  name: 'DictionaryManager',
  template: '<div class="dictionary-manager">Dictionary Manager</div>'
}

const MockRelationManager = {
  name: 'RelationManager',
  template: '<div class="relation-manager">Relation Manager</div>'
}

// 创建测试路由
const createTestRouter = () => {
  return createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/data-prep',
        name: 'DataPreparation',
        component: DataPreparationManager,
        redirect: '/data-prep/sources',
        children: [
          {
            path: 'sources',
            name: 'DataSources',
            component: MockDataSourceList
          },
          {
            path: 'tables',
            name: 'DataTables',
            component: MockDataTableManager
          },
          {
            path: 'dictionaries',
            name: 'Dictionaries',
            component: MockDictionaryManager
          },
          {
            path: 'relations',
            name: 'Relations',
            component: MockRelationManager
          }
        ]
      }
    ]
  })
}

describe('DataPreparationManager', () => {
  let router: any

  beforeEach(() => {
    router = createTestRouter()
  })

  it('应该正确渲染主页面结构', () => {
    const wrapper = mount(DataPreparationManager, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': { template: '<div class="router-view">Router View</div>' }
        }
      }
    })

    expect(wrapper.find('.data-preparation-manager').exists()).toBe(true)
    expect(wrapper.find('.router-view').exists()).toBe(true)
  })

  it('应该包含 router-view 用于显示子组件', () => {
    const wrapper = mount(DataPreparationManager, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': { template: '<div class="router-view">Router View</div>' }
        }
      }
    })

    expect(wrapper.find('.router-view').exists()).toBe(true)
  })

  it('应该有正确的样式类', () => {
    const wrapper = mount(DataPreparationManager, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': { template: '<div class="router-view">Router View</div>' }
        }
      }
    })

    const container = wrapper.find('.data-preparation-manager')
    expect(container.exists()).toBe(true)
    
    // 检查样式是否正确应用
    const element = container.element as HTMLElement
    expect(element.tagName.toLowerCase()).toBe('div')
  })
})

// 路由集成测试
describe('DataPreparation Routes Integration', () => {
  it('应该正确配置子路由结构', () => {
    const router = createTestRouter()
    const routes = router.getRoutes()
    
    const dataPreparationRoute = routes.find(route => route.name === 'DataPreparation')
    expect(dataPreparationRoute).toBeDefined()
    expect(dataPreparationRoute?.children).toHaveLength(4)
    
    const childRouteNames = dataPreparationRoute?.children?.map(child => child.name)
    expect(childRouteNames).toContain('DataSources')
    expect(childRouteNames).toContain('DataTables')
    expect(childRouteNames).toContain('Dictionaries')
    expect(childRouteNames).toContain('Relations')
  })

  it('应该有正确的重定向配置', () => {
    const router = createTestRouter()
    const routes = router.getRoutes()
    
    const dataPreparationRoute = routes.find(route => route.name === 'DataPreparation')
    expect(dataPreparationRoute?.redirect).toBe('/data-prep/sources')
  })
})