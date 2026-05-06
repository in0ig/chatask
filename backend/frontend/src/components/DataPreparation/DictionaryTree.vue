<template>
  <div class="dictionary-tree-container">
    <div class="tree-header">
      <h3>字典管理</h3>
      <el-button type="primary" @click="handleAddDictionary">新增字典</el-button>
    </div>
    
    <el-input
      v-model="searchText"
      placeholder="按字典名称或编码搜索..."
      prefix-icon="el-icon-search"
      class="search-input"
    />
    
    <el-tree
      :data="treeData"
      :props="defaultProps"
      :filter-node-method="filterNode"
      :expand-on-click-node="false"
      @node-click="handleNodeClick"
      class="dictionary-tree"
      ref="tree"
    >
      <template #default="{ node, data }">
        <span class="custom-tree-node">
          <span>{{ node.label }}</span>
          <span class="node-actions">
            <el-button
              type="text"
              size="small"
              @click.stop="handleEdit(node, data)"
              icon="el-icon-edit"
            />
            <el-button
              type="text"
              size="small"
              @click.stop="handleDelete(node, data)"
              icon="el-icon-delete"
              :disabled="data.children && data.children.length > 0"
            />
          </span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElTree } from 'element-plus'
import { useDataPrepStore } from '@/store/modules/dataPreparation'

const tree = ref(null)
const searchText = ref('')
const store = useDataPrepStore()

// 字典树数据
const treeData = ref([])

// 树节点属性配置
const defaultProps = reactive({
  children: 'children',
  label: 'label'
})

// 搜索过滤方法
const filterNode = (value, data) => {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase()) || 
         data.code.toLowerCase().includes(value.toLowerCase())
}

// 处理节点点击
const handleNodeClick = (data, node) => {
  // 触发详情查看事件
  console.log('Node clicked:', data)
}

// 新增字典
const handleAddDictionary = () => {
  // 触发新增字典对话框
  store.showAddDictionaryModal()
}

// 编辑字典
const handleEdit = (node, data) => {
  store.showEditDictionaryModal(data)
}

// 删除字典
const handleDelete = (node, data) => {
  if (window.confirm('确定要删除这个字典吗？')) {
    store.deleteDictionary(data.id)
  }
}

// 监听字典数据变化
watch(() => store.dictionaries, (newDictionaries) => {
  treeData.value = buildTreeData(newDictionaries)
}, { deep: true })

// 构建树形数据结构
const buildTreeData = (dictionaries) => {
  const map = new Map()
  const rootNodes = []
  
  // 先创建所有节点
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
  
  // 构建父子关系
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

// 初始化数据
const init = () => {
  // 确保字典数据已加载
  if (store.dictionaries.length === 0) {
    store.fetchDictionaries()
  }
}

// 初始化
init()
</script>

<style scoped>
.dictionary-tree-container {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.search-input {
  margin-bottom: 16px;
}

.dictionary-tree {
  flex: 1;
  overflow-y: auto;
}

.custom-tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.node-actions {
  display: flex;
  gap: 4px;
}

.node-actions button {
  opacity: 0.7;
  transition: opacity 0.2s;
}

.node-actions button:hover {
  opacity: 1;
}
</style>