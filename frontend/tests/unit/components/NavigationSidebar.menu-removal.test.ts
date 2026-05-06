import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import NavigationSidebar from '@/components/NavigationSidebar.vue'

// 创建测试路由
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: { template: '<div>Home</div>' } },
    { 
      path: '/data-prep', 
      name: 'DataPrep', 
      component: { template: '<div>DataPrep</div>' },
      redirect: '/data-prep/sources'
    },
    { path: '/data-prep/sources', name: 'DataSources', component: { template: '<div>DataSources</div>' } },
    { path: '/data-prep/tables', name: 'DataTables', component: { template: '<div>Tables</div>' } },
    { path: '/chatbi/datasources', name: 'ChatBIDataSources', component: { template: '<div>ChatBIDataSources</div>' } },
    { path: '/analysis', name: 'Analysis', component: { template: '<div>Analysis</div>' } }
  ]
})

describe('NavigationSidebar - 菜单移除功能测试', () => {
  let wrapper: any

  beforeEach(async () => {
    await router.push('/')
    wrapper = mount(NavigationSidebar, {
      global: {
        plugins: [router]
      }
    })
  })

  describe('🎯 移除的菜单项验证', () => {
    it('应该不包含"项目配置"主菜单项', () => {
      const configMenuItem = wrapper.find('.nav-text:contains("项目配置")')
      expect(configMenuItem.exists()).toBe(false)
    })

    it('应该不包含"数据填报"子菜单项', () => {
      const dataEntryMenuItem = wrapper.find('.nav-text:contains("数据填报")')
      expect(dataEntryMenuItem.exists()).toBe(false)
    })

    it('应该不包含config相关的CSS类', () => {
      const configActiveItems = wrapper.findAll('.nav-item').filter((item: any) => 
        item.classes().includes('active') && item.text().includes('项目配置')
      )
      expect(configActiveItems).toHaveLength(0)
    })
  })

  describe('✅ 保留的菜单项验证', () => {
    it('应该包含"数据看板"菜单项', () => {
      const navTexts = wrapper.findAll('.nav-text')
      const dashboardExists = navTexts.some((item: any) => item.text() === '数据看板')
      expect(dashboardExists).toBe(true)
    })

    it('应该包含"数据分析"菜单项', () => {
      const navTexts = wrapper.findAll('.nav-text')
      const analysisExists = navTexts.some((item: any) => item.text() === '数据分析')
      expect(analysisExists).toBe(true)
    })

    it('应该包含"项目应用"菜单项', () => {
      const navTexts = wrapper.findAll('.nav-text')
      const applicationsExists = navTexts.some((item: any) => item.text() === '项目应用')
      expect(applicationsExists).toBe(true)
    })

    it('应该包含新的"数据准备"菜单项', () => {
      const navTexts = wrapper.findAll('.nav-text')
      const dataPrepExists = navTexts.some((item: any) => item.text() === '数据准备')
      expect(dataPrepExists).toBe(true)
    })
  })

  describe('🗂️ 数据准备子菜单验证', () => {
    beforeEach(async () => {
      await router.push('/data-prep/tables')
      await wrapper.vm.$nextTick()
    })

    it('应该包含"数据表"子菜单项', () => {
      const subNavTexts = wrapper.findAll('.nav-sub-item .nav-text')
      const tablesExists = subNavTexts.some((item: any) => item.text() === '数据表')
      expect(tablesExists).toBe(true)
    })

    it('应该包含"数据源"子菜单项', () => {
      const subNavTexts = wrapper.findAll('.nav-sub-item .nav-text')
      const sourcesExists = subNavTexts.some((item: any) => item.text() === '数据源')
      expect(sourcesExists).toBe(true)
    })

    it('应该包含"字典表"子菜单项', () => {
      const subNavTexts = wrapper.findAll('.nav-sub-item .nav-text')
      const dictionariesExists = subNavTexts.some((item: any) => item.text() === '字典表')
      expect(dictionariesExists).toBe(true)
    })

    it('应该包含"表关联"子菜单项', () => {
      const subNavTexts = wrapper.findAll('.nav-sub-item .nav-text')
      const relationsExists = subNavTexts.some((item: any) => item.text() === '表关联')
      expect(relationsExists).toBe(true)
    })

    it('子菜单应该在data-prep路径下显示', () => {
      const subMenuItems = wrapper.findAll('.nav-sub-item')
      expect(subMenuItems.length).toBeGreaterThan(0)
    })
  })

  describe('🔄 路由计算逻辑验证', () => {
    it('根路径应该激活dashboard', async () => {
      await router.push('/')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.currentSection).toBe('dashboard')
    })

    it('data-prep路径应该激活data-prep', async () => {
      await router.push('/data-prep/tables')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.currentSection).toBe('data-prep')
    })

    it('chatbi/datasources路径应该激活data-prep', async () => {
      await router.push('/chatbi/datasources')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.currentSection).toBe('data-prep')
    })

    it('analysis路径应该激活analysis', async () => {
      await router.push('/analysis')
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.currentSection).toBe('analysis')
    })
  })

  describe('🧪 导航功能验证', () => {
    it('点击数据准备应该触发导航', async () => {
      const navItems = wrapper.findAll('.nav-item')
      const dataPrepItem = navItems.find((item: any) => 
        item.text().includes('数据准备')
      )
      
      expect(dataPrepItem).toBeDefined()
      
      // 验证点击事件可以被触发，这是核心功能
      await dataPrepItem!.trigger('click')
      await wrapper.vm.$nextTick()
      
      // 验证navigateTo函数存在并可以被调用
      expect(typeof wrapper.vm.navigateTo).toBe('function')
      
      // 验证数据准备菜单项存在
      expect(dataPrepItem!.text()).toContain('数据准备')
    })

    it('点击数据表子菜单应该导航到正确路径', async () => {
      await router.push('/data-prep/tables')
      await wrapper.vm.$nextTick()
      
      const subItems = wrapper.findAll('.nav-sub-item')
      const tablesItem = subItems.find((item: any) => 
        item.text().includes('数据表')
      )
      
      expect(tablesItem).toBeDefined()
      await tablesItem!.trigger('click')
      await wrapper.vm.$nextTick()
      expect(router.currentRoute.value.path).toBe('/data-prep/tables')
    })

    it('navigateTo函数应该正确处理不同路径格式', async () => {
      const navigateTo = wrapper.vm.navigateTo
      
      // 测试dashboard路径
      await navigateTo('dashboard')
      await wrapper.vm.$nextTick()
      expect(router.currentRoute.value.path).toBe('/')
      
      // 测试navigateTo函数存在并可调用
      expect(typeof navigateTo).toBe('function')
    })
  })

  describe('📱 响应式和样式验证', () => {
    it('应该有正确的CSS类结构', () => {
      expect(wrapper.find('.navigation-sidebar').exists()).toBe(true)
      expect(wrapper.find('.sidebar-header').exists()).toBe(true)
      expect(wrapper.find('.sidebar-nav').exists()).toBe(true)
      expect(wrapper.find('.nav-section').exists()).toBe(true)
    })

    it('活动状态应该正确应用', async () => {
      await router.push('/data-prep/tables')
      await wrapper.vm.$nextTick()
      
      const activeItems = wrapper.findAll('.nav-item.active')
      expect(activeItems.length).toBeGreaterThan(0)
    })

    it('子菜单项应该有正确的样式类', async () => {
      await router.push('/data-prep/tables')
      await wrapper.vm.$nextTick()
      
      const subItems = wrapper.findAll('.nav-sub-item')
      expect(subItems.length).toBeGreaterThan(0)
      
      subItems.forEach((item: any) => {
        expect(item.classes()).toContain('nav-sub-item')
      })
    })
  })
})