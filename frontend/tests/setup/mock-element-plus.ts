import { defineComponent } from 'vue'

// Mock all Element Plus components as simple div elements
// This prevents the "Failed to resolve component" errors in tests

// Define a simple mock component that renders as a div with the component name
const mockElementPlusComponent = (name: string) => {
  return defineComponent({
    name: name,
    template: `<div class="${name.toLowerCase()}" v-bind="$attrs"><slot /></div>`,
    inheritAttrs: false,
    props: {
      // Common props that Element Plus components might have
      loading: Boolean,
      disabled: Boolean,
      type: String,
      size: String,
      modelValue: [String, Number, Boolean, Array, Object],
      placeholder: String,
      width: [String, Number],
      title: String,
      visible: Boolean,
      'close-on-click-modal': Boolean,
      data: Array,
      'empty-text': String,
      prop: String,
      label: String,
      'min-width': [String, Number],
      align: String,
      'show-overflow-tooltip': Boolean,
      fixed: String,
      column: Number,
      border: Boolean,
      span: Number,
      closable: Boolean
    },
    emits: ['update:modelValue', 'change', 'click', 'close', 'confirm', 'cancel'],
    setup(props, { emit }) {
      return {
        handleClick: () => emit('click'),
        handleChange: (value: any) => emit('update:modelValue', value),
        handleClose: () => emit('close'),
        handleConfirm: () => emit('confirm'),
        handleCancel: () => emit('cancel')
      }
    }
  })
}

// List of all Element Plus components we need to mock
const elementPlusComponents = [
  'el-drawer',
  'el-menu',
  'el-menu-item',
  'el-icon',
  'el-switch',
  'el-tree',
  'el-option',
  'el-select',
  'el-input',
  'el-button',
  'el-card',
  'el-progress',
  'el-tag',
  'el-form',
  'el-form-item',
  'el-tabs',
  'el-tab-pane',
  'el-alert',
  'el-message',
  'el-notification',
  'el-table',
  'el-table-column',
  'el-dialog',
  'el-checkbox',
  'el-checkbox-group',
  'el-empty',
  'el-descriptions',
  'el-descriptions-item'
]

// Register all components as mocks
export function mockElementPlusComponents() {
  elementPlusComponents.forEach(component => {
    // Register as a global component using Vue Test Utils
    ;(global as any).component = (global as any).component || {}
    ;(global as any).component[component] = mockElementPlusComponent(component)
  })
}

// Also mock the icons as simple SVG elements
export function mockElementPlusIcons() {
  const mockIcon = defineComponent({
    name: 'MockIcon',
    template: `<svg class="el-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><slot /></svg>`
  })
  
  // List of icons we need to mock
  const icons = [
    'ChartLine',
    'Document',
    'Setting',
    'Language',
    'Bell',
    'Plus',
    'Search',
    'Connection',
    'Warning',
    'CircleCheck'
  ]
  
  icons.forEach(icon => {
    // Register as a global component
    ;(global as any).component = (global as any).component || {}
    ;(global as any).component[icon] = mockIcon
  })
}

// Export a function to set up all mocks
export function setupElementPlusMocks() {
  mockElementPlusComponents()
  mockElementPlusIcons()
}

// Call the setup function immediately to ensure mocks are registered
setupElementPlusMocks()