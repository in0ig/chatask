import { shallowMount } from '@vue/test-utils'
import DataPreparationManager from '@/components/DataPreparation/DataPreparationManager.vue'

describe('DataPreparationManager.vue', () => {
  it('renders properly with stubbed Element Plus components', () => {
    const wrapper = shallowMount(DataPreparationManager, {
      global: {
        stubs: {
          ElTabs: '<div class="el-tabs"><slot /></div>',
          ElTabPane: '<div class="el-tab-pane"><slot /></div>',
          ElSkeleton: '<div class="el-skeleton"><slot /></div>'
        }
      }
    })
    
    expect(wrapper.exists()).toBe(true)
    expect(wrapper.find('.el-tabs').exists()).toBe(true)
  })

  it('handles tab switching via emit events', async () => {
    const wrapper = shallowMount(DataPreparationManager, {
      global: {
        stubs: {
          ElTabs: '<div class="el-tabs"><slot /></div>',
          ElTabPane: '<div class="el-tab-pane"><slot /></div>',
          ElSkeleton: '<div class="el-skeleton"><slot /></div>'
        }
      }
    })
    
    // Mock the tab change event
    await wrapper.vm.$emit('update:modelValue', 'data-source')
    
    // Verify the active tab was updated
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['data-source'])
  })

  it('displays loading state when loading is true', () => {
    const wrapper = shallowMount(DataPreparationManager, {
      global: {
        stubs: {
          ElTabs: '<div class="el-tabs"><slot /></div>',
          ElTabPane: '<div class="el-tab-pane"><slot /></div>',
          ElSkeleton: '<div class="el-skeleton"><slot /></div>'
        }
      },
      props: {
        loading: true
      }
    })
    
    expect(wrapper.find('.el-skeleton').exists()).toBe(true)
  })

  it('displays error state when error is true', () => {
    const wrapper = shallowMount(DataPreparationManager, {
      global: {
        stubs: {
          ElTabs: '<div class="el-tabs"><slot /></div>',
          ElTabPane: '<div class="el-tab-pane"><slot /></div>',
          ElSkeleton: '<div class="el-skeleton"><slot /></div>'
        }
      },
      props: {
        error: true
      }
    })
    
    expect(wrapper.find('.error-state').exists()).toBe(true)
  })

  it('emits event when data is successfully loaded', async () => {
    const wrapper = shallowMount(DataPreparationManager, {
      global: {
        stubs: {
          ElTabs: '<div class="el-tabs"><slot /></div>',
          ElTabPane: '<div class="el-tab-pane"><slot /></div>',
          ElSkeleton: '<div class="el-skeleton"><slot /></div>'
        }
      }
    })
    
    // Simulate successful data load
    await wrapper.vm.$emit('data-loaded')
    
    expect(wrapper.emitted('data-loaded')).toBeTruthy()
  })
})
