<template>
  <div class="permission-section">
    <!-- 功能权限部分 -->
    <div class="permission-group">
      <h3 class="group-title">功能权限</h3>
      <div class="permission-item">
        <label class="permission-label">数据查询</label>
        <el-switch
          v-model="permissions.query"
          class="permission-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updatePermission('query', $event)"
        />
      </div>
      
      <div class="permission-item">
        <label class="permission-label">报告生成</label>
        <el-switch
          v-model="permissions.report"
          class="permission-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updatePermission('report', $event)"
        />
      </div>
      
      <div class="permission-item">
        <label class="permission-label">数据导出</label>
        <el-switch
          v-model="permissions.export"
          class="permission-switch"
          active-color="#1890ff"
          inactive-color="#ccc"
          @change="updatePermission('export', $event)"
        />
      </div>
    </div>
    
    <!-- 数据表权限部分 -->
    <div class="permission-group">
      <h3 class="group-title">数据表权限</h3>
      <div class="table-permission-container">
        <el-tree
          :data="tableOptions"
          :props="treeProps"
          :default-expanded-keys="expandedKeys"
          :default-checked-keys="checkedTableKeys"
          show-checkbox
          node-key="id"
          check-strictly
          @check-change="handleTableCheckChange"
          class="table-tree"
        >
          <!-- 移除 template slot，使用默认的节点显示 -->
        </el-tree>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { useUIStore } from '@/store/modules/ui'

// 定义权限类型
interface PermissionState {
  query: boolean
  report: boolean
  export: boolean
}

// 初始化权限状态
const permissions = ref<PermissionState>({
  query: true,
  report: true,
  export: true
})

// 数据表选项
const dataPrepStore = useDataPrepStore()
const tableOptions = computed(() => {
  return dataPrepStore.dataTables.map(table => ({
    id: table.id,
    label: table.name,
    source: table.dataSourceName,
    children: []
  }))
})

// 树形结构属性
const treeProps = {
  label: 'label',
  children: 'children'
}

// 展开的节点
const expandedKeys = ref<string[]>([])

// 已选中的数据表
const checkedTableKeys = ref<string[]>([])

// 更新功能权限
const updatePermission = (permission: keyof PermissionState, value: boolean) => {
  permissions.value[permission] = value
  // 将权限状态保存到 store
  dataPrepStore.updatePermission(permission, value)
}

// 处理数据表权限选择变化
const handleTableCheckChange = (checkedKeys: string[], checkedNodes: any[]) => {
  checkedTableKeys.value = checkedKeys
  // 将选中的数据表ID保存到 store
  dataPrepStore.updateTablePermissions(checkedKeys)
}

// 初始化权限状态
const initPermissions = () => {
  // 从 store 加载权限配置
  const storedPermissions = dataPrepStore.permissions
  if (storedPermissions) {
    permissions.value = { ...storedPermissions }
  }
  
  // 从 store 加载数据表权限
  checkedTableKeys.value = [...dataPrepStore.tablePermissions]
}

// 在组件挂载时初始化
initPermissions()
</script>

<style scoped>
.permission-section {
  padding: 20px;
}

.permission-group {
  margin-bottom: 30px;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e0e0e0;
}

.permission-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.permission-label {
  flex: 1;
  font-size: 14px;
  color: #333;
}

.permission-switch {
  margin-left: 10px;
}

.table-permission-container {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 10px;
}

.table-tree {
  width: 100%;
}

.tree-node-content {
  display: flex;
  align-items: center;
}

.table-source {
  font-size: 12px;
  color: #666;
  margin-left: 8px;
  padding: 2px 6px;
  background-color: #f5f5f5;
  border-radius: 12px;
}
</style>