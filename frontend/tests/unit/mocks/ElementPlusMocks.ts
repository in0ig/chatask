import { defineComponent } from 'vue'

// ElSwitch mock
export const MockElSwitch = defineComponent({
  template: '<label class="el-switch"><input type="checkbox" class="el-switch__input" :checked="modelValue" @change="onSwitchChange" /><span class="el-switch__core" /></label>',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: {
    onSwitchChange(event: Event) {
      const target = event.target as HTMLInputElement
      this.$emit('update:modelValue', target.checked)
    }
  }
})

// ElTree mock
export const MockElTree = defineComponent({
  template: `<div class="el-tree">
    <div 
      class="el-tree-node" 
      v-for="node in data" 
      :key="node.id"
      :class="{'is-checked': checkedNodes.includes(node.id)}"
    >
      <label class="el-checkbox">
        <input 
          type="checkbox" 
          class="el-checkbox__input" 
          :checked="checkedNodes.includes(node.id)"
          @change="onNodeCheckChange(node)"
        />
        <span class="el-checkbox__label">
          <span class="tree-node-content">
            {{ node.label }}
            <span class="table-source">({{ node.data.source }})</span>
          </span>
        </span>
      </label>
    </div>
  </div>`,
  props: ['data', 'props', 'defaultCheckedKeys'],
  emits: ['check-change'],
  data() {
    return {
      checkedNodes: this.defaultCheckedKeys || []
    }
  },
  methods: {
    onNodeCheckChange(node: any) {
      const index = this.checkedNodes.indexOf(node.id)
      if (index > -1) {
        this.checkedNodes.splice(index, 1)
      } else {
        this.checkedNodes.push(node.id)
      }
      this.$emit('check-change', this.checkedNodes, [
        this.data.find((n: any) => n.id === node.id)
      ])
    }
  }
})

// ElOption mock
export const MockElOption = defineComponent({
  template: '<option><slot /></option>'
})

// ElIcon mock
export const MockElIcon = defineComponent({
  template: '<span class="el-icon"><slot /></span>'
})

// ElCheckbox mock
export const MockElCheckbox = defineComponent({
  template: '<label class="el-checkbox"><input type="checkbox" class="el-checkbox__input" /><span class="el-checkbox__label"><slot /></span></label>'
})

// Icon mocks - for Document, Upload, ChartLine, Send, Plus, Setting
export const MockDocument = defineComponent({
  template: '<span class="el-icon-document"><slot /></span>'
})

export const MockUpload = defineComponent({
  template: '<span class="el-icon-upload"><slot /></span>'
})

export const MockChartLine = defineComponent({
  template: '<span class="el-icon-chart-line"><slot /></span>'
})

export const MockSend = defineComponent({
  template: '<span class="el-icon-send"><slot /></span>'
})

export const MockPlus = defineComponent({
  template: '<span class="el-icon-plus"><slot /></span>'
})

export const MockSetting = defineComponent({
  template: '<span class="el-icon-setting"><slot /></span>'
})