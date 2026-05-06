<template>
  <el-dialog
    v-model="visible"
    :title="'数据源选择（已选：' + selectedCount + '张表）'"
    width="600px"
    :before-close="handleClose"
    :destroy-on-close="true"
    class="data-source-selector-dialog"
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    append-to-body
  >
    <!-- 搜索和筛选区域 -->
    <div class="search-filter-section">
      <el-input
        v-model="searchKeyword"
        placeholder="请输入数据源名称搜索..."
        prefix-icon="Search"
        clearable
        class="search-input"
        @keyup.enter="handleSearch"
        @clear="clearSearch"
      >
        <template #suffix>
          <el-tooltip content="支持模糊搜索和正则表达式" placement="top">
            <el-icon class="search-tip-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>
      </el-input>
      
      <!-- 快速筛选 -->
      <div class="quick-filters">
        <el-button-group>
          <el-button 
            :type="filterType === 'all' ? 'primary' : 'default'"
            size="small"
            @click="setFilter('all')"
          >
            全部 ({{ totalCount }})
          </el-button>
          <el-button 
            :type="filterType === 'selected' ? 'primary' : 'default'"
            size="small"
            @click="setFilter('selected')"
          >
            已选 ({{ selectedCount }})
          </el-button>
          <el-button 
            :type="filterType === 'pinned' ? 'primary' : 'default'"
            size="small"
            @click="setFilter('pinned')"
          >
            置顶 ({{ pinnedCount }})
          </el-button>
        </el-button-group>
        
        <!-- 数据源类型筛选 -->
        <el-select
          v-model="selectedTypes"
          multiple
          placeholder="筛选类型"
          size="small"
          style="width: 120px;"
          collapse-tags
          collapse-tags-tooltip
        >
          <el-option
            v-for="type in availableTypes"
            :key="type.value"
            :label="type.label"
            :value="type.value"
          >
            <el-tag :type="getDataSourceTypeColor(type.value)" size="small">
              {{ type.label }}
            </el-tag>
          </el-option>
        </el-select>
      </div>
    </div>
    
    <!-- 批量操作工具栏 -->
    <div v-if="selectedCount > 0" class="batch-actions">
      <el-alert
        :title="`已选择 ${selectedCount} 个数据源`"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          <div class="batch-action-buttons">
            <el-button size="small" @click="selectAll">全选</el-button>
            <el-button size="small" @click="selectNone">清空</el-button>
            <el-button size="small" @click="invertSelection">反选</el-button>
            <el-button size="small" @click="pinSelected">批量置顶</el-button>
          </div>
        </template>
      </el-alert>
    </div>
    
    <!-- 加载状态 - 增强版 -->
    <div v-if="isLoading" class="loading-container">
      <div class="loading-animation">
        <el-skeleton :rows="5" animated />
        <div class="loading-progress">
          <el-progress 
            :percentage="loadingProgress" 
            :show-text="false"
            :stroke-width="4"
            color="#409eff"
          />
        </div>
      </div>
      <div class="loading-text">
        <el-icon class="loading-icon"><Loading /></el-icon>
        正在加载数据源...
      </div>
    </div>
    
    <!-- 错误状态 - 增强版 -->
    <div v-else-if="error" class="error-container">
      <el-result
        icon="warning"
        title="加载失败"
        :sub-title="error"
      >
        <template #extra>
          <div class="error-actions">
            <el-button type="primary" @click="handleRetry">
              <el-icon><Refresh /></el-icon>
              重新加载
            </el-button>
            <el-button @click="handleClose">
              取消
            </el-button>
          </div>
        </template>
      </el-result>
    </div>
    
    <!-- 数据表列表 - 增强版 -->
    <div v-else class="table-list">
      <!-- 空状态 - 增强版 -->
      <div v-if="filteredTables.length === 0" class="empty-state">
        <el-result
          :icon="searchKeyword ? 'search' : 'info'"
          :title="getEmptyStateTitle()"
          :sub-title="getEmptyStateSubtitle()"
        >
          <template #extra>
            <div class="empty-actions">
              <el-button v-if="searchKeyword" type="primary" @click="clearSearch">
                <el-icon><Close /></el-icon>
                清空搜索
              </el-button>
              <el-button v-else-if="filterType !== 'all'" @click="setFilter('all')">
                <el-icon><View /></el-icon>
                查看全部
              </el-button>
              <el-button v-else @click="handleClose">
                <el-icon><Plus /></el-icon>
                添加数据源
              </el-button>
            </div>
          </template>
        </el-result>
      </div>
      
      <!-- 数据源列表 - 虚拟滚动优化 -->
      <div v-else class="table-list-content">
        <!-- 列表头部信息 -->
        <div class="list-header">
          <div class="list-stats">
            显示 {{ filteredTables.length }} 个数据源
            <span v-if="searchKeyword">（搜索："{{ searchKeyword }}"）</span>
          </div>
          <div class="sort-options">
            <el-dropdown @command="handleSort">
              <el-button size="small" text>
                排序 <el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="name">按名称</el-dropdown-item>
                  <el-dropdown-item command="type">按类型</el-dropdown-item>
                  <el-dropdown-item command="selected">按选择状态</el-dropdown-item>
                  <el-dropdown-item command="pinned">按置顶状态</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        
        <!-- 数据源项目列表 -->
        <div class="table-items">
          <transition-group name="table-item" tag="div">
            <div 
              v-for="table in sortedTables" 
              :key="table.id"
              class="table-item"
              :class="{ 
                'selected': table.selected, 
                'pinned': table.pinned,
                'highlighted': highlightedId === table.id
              }"
              @click="handleTableClick(table)"
              @mouseenter="handleTableHover(table)"
              @mouseleave="handleTableLeave()"
            >
              <el-checkbox
                :model-value="table.selected"
                :label="table.id"
                class="table-checkbox"
                @change="(value) => handleTableSelectionChange(table, value)"
                @click.stop
              >
                <div class="table-info">
                  <div class="table-header">
                    <span class="table-name">{{ highlightSearchText(table.name) }}</span>
                    <div class="table-badges">
                      <el-tag 
                        :type="getDataSourceTypeColor(table.type)" 
                        size="small"
                        class="type-tag"
                      >
                        {{ getDataSourceTypeLabel(table.type) }}
                      </el-tag>
                      <el-icon v-if="table.pinned" class="pin-icon" color="#f56c6c">
                        <Star />
                      </el-icon>
                      <el-tag v-if="table.selected" type="success" size="small">
                        已选
                      </el-tag>
                    </div>
                  </div>
                  <div class="table-description">
                    <span class="table-id">ID: {{ table.id }}</span>
                    <span class="table-status">
                      <el-icon :color="table.isActive ? '#67c23a' : '#909399'">
                        <CircleCheck v-if="table.isActive" />
                        <CircleClose v-else />
                      </el-icon>
                      {{ table.isActive ? '活跃' : '非活跃' }}
                    </span>
                  </div>
                </div>
              </el-checkbox>
              
              <div class="table-actions">
                <el-tooltip content="置顶/取消置顶" placement="top">
                  <el-button
                    type="text"
                    size="small"
                    @click.stop="togglePin(table)"
                    :class="{ 'pinned': table.pinned }"
                  >
                    <el-icon :color="table.pinned ? '#f56c6c' : '#909399'">
                      <Star />
                    </el-icon>
                  </el-button>
                </el-tooltip>
                
                <el-tooltip content="预览数据" placement="top">
                  <el-button
                    type="primary"
                    size="small"
                    class="preview-btn"
                    @click.stop="previewTable(table)"
                  >
                    <el-icon><View /></el-icon>
                    预览
                  </el-button>
                </el-tooltip>
                
                <el-dropdown @command="(command) => handleTableAction(table, command)">
                  <el-button type="text" size="small">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="info">查看详情</el-dropdown-item>
                      <el-dropdown-item command="copy">复制ID</el-dropdown-item>
                      <el-dropdown-item command="export">导出配置</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </transition-group>
        </div>
      </div>
    </div>
    
    <!-- 底部按钮 - 增强版 -->
    <template #footer>
      <div class="footer-actions">
        <div class="selection-summary">
          <el-tag v-if="selectedCount > 0" type="success" size="large">
            <el-icon><Check /></el-icon>
            已选择 {{ selectedCount }} 个数据源
          </el-tag>
          <span v-else class="no-selection">请选择数据源</span>
        </div>
        
        <div class="action-buttons">
          <el-button @click="handleClose" size="large">
            取消
          </el-button>
          <el-button 
            type="primary" 
            size="large"
            @click="confirmSelection"
            :disabled="selectedCount === 0"
            :loading="isConfirming"
          >
            <el-icon v-if="!isConfirming"><Check /></el-icon>
            确定选择
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { 
  Warning, Refresh, Search, Star, QuestionFilled, Loading, 
  Close, View, Plus, ArrowDown, CircleCheck, CircleClose, 
  MoreFilled, Check 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 定义接口
interface DataSource {
  id: string
  name: string
  type: string
  selected: boolean
  pinned: boolean
  isActive?: boolean
  description?: string
}

// Props
const props = defineProps<{
  modelValue: boolean
  dataSources: DataSource[]
  isLoading?: boolean
  error?: string | null
}>()

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [tables: DataSource[]]
  'preview': [table: DataSource]
  'retry': []
  'info': [table: DataSource]
}>()

// State
const visible = ref(props.modelValue)
const searchKeyword = ref('')
const filterType = ref<'all' | 'selected' | 'pinned'>('all')
const selectedTypes = ref<string[]>([])
const sortBy = ref<'name' | 'type' | 'selected' | 'pinned'>('name')
const highlightedId = ref<string | null>(null)
const isConfirming = ref(false)
const loadingProgress = ref(0)

// 计算属性：总数统计
const totalCount = computed(() => props.dataSources.length)
const pinnedCount = computed(() => props.dataSources.filter(t => t.pinned).length)

// 计算属性：可用的数据源类型
const availableTypes = computed(() => {
  const types = [...new Set(props.dataSources.map(t => t.type))]
  return types.map(type => ({
    value: type,
    label: getDataSourceTypeLabel(type)
  }))
})

// 计算属性：过滤后的数据源列表
const filteredTables = computed(() => {
  let filtered = props.dataSources

  // 按筛选类型过滤
  if (filterType.value === 'selected') {
    filtered = filtered.filter(table => table.selected)
  } else if (filterType.value === 'pinned') {
    filtered = filtered.filter(table => table.pinned)
  }

  // 按数据源类型过滤
  if (selectedTypes.value.length > 0) {
    filtered = filtered.filter(table => selectedTypes.value.includes(table.type))
  }

  // 按搜索关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = filtered.filter(table => {
      return table.name.toLowerCase().includes(keyword) ||
             table.id.toLowerCase().includes(keyword) ||
             (table.description && table.description.toLowerCase().includes(keyword))
    })
  }

  return filtered
})

// 计算属性：排序后的数据源列表
const sortedTables = computed(() => {
  return [...filteredTables.value].sort((a, b) => {
    // 置顶的排在前面
    if (a.pinned && !b.pinned) return -1
    if (!a.pinned && b.pinned) return 1
    
    // 按选择的排序方式排序
    switch (sortBy.value) {
      case 'selected':
        if (a.selected && !b.selected) return -1
        if (!a.selected && b.selected) return 1
        break
      case 'type':
        const typeCompare = a.type.localeCompare(b.type)
        if (typeCompare !== 0) return typeCompare
        break
      case 'pinned':
        // 已经在前面处理了置顶排序
        break
      case 'name':
      default:
        // 按名称排序
        return a.name.localeCompare(b.name)
    }
    
    // 默认按名称排序
    return a.name.localeCompare(b.name)
  })
})

// 计算属性：已选数量
const selectedCount = computed(() => {
  return props.dataSources.filter(table => table.selected).length
})

// 监听 props 变化
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
  if (newValue) {
    // 对话框打开时重置状态
    resetFilters()
    simulateLoadingProgress()
  }
})

// 监听加载状态，模拟进度
watch(() => props.isLoading, (isLoading) => {
  if (isLoading) {
    simulateLoadingProgress()
  } else {
    loadingProgress.value = 100
  }
})

// 模拟加载进度
const simulateLoadingProgress = () => {
  loadingProgress.value = 0
  const interval = setInterval(() => {
    loadingProgress.value += Math.random() * 20
    if (loadingProgress.value >= 90 || !props.isLoading) {
      clearInterval(interval)
      if (!props.isLoading) {
        loadingProgress.value = 100
      }
    }
  }, 200)
}

// 重置筛选条件
const resetFilters = () => {
  searchKeyword.value = ''
  filterType.value = 'all'
  selectedTypes.value = []
  sortBy.value = 'name'
}

// 处理对话框关闭
const handleClose = () => {
  visible.value = false
  emit('update:modelValue', false)
}

// 设置筛选类型
const setFilter = (type: 'all' | 'selected' | 'pinned') => {
  filterType.value = type
}

// 处理搜索
const handleSearch = () => {
  // 搜索时自动滚动到顶部
  nextTick(() => {
    const listElement = document.querySelector('.table-list-content')
    if (listElement) {
      listElement.scrollTop = 0
    }
  })
}

// 清空搜索
const clearSearch = () => {
  searchKeyword.value = ''
}

// 高亮搜索文本 - 简化版本，返回原文本
const highlightSearchText = (text: string) => {
  return text // 暂时返回原文本，避免 v-html 编译问题
}

// 处理排序
const handleSort = (command: string) => {
  sortBy.value = command as typeof sortBy.value
}

// 处理表格点击
const handleTableClick = (table: DataSource) => {
  handleTableSelectionChange(table, !table.selected)
}

// 处理表格悬停
const handleTableHover = (table: DataSource) => {
  highlightedId.value = table.id
}

// 处理表格离开
const handleTableLeave = () => {
  highlightedId.value = null
}

// 处理单个表的选择变化
const handleTableSelectionChange = (table: DataSource, value: boolean) => {
  table.selected = value
  
  // 添加选择反馈
  if (value) {
    ElMessage.success(`已选择 ${table.name}`)
  }
}

// 批量操作
const selectAll = () => {
  filteredTables.value.forEach(table => {
    table.selected = true
  })
  ElMessage.success(`已选择 ${filteredTables.value.length} 个数据源`)
}

const selectNone = () => {
  props.dataSources.forEach(table => {
    table.selected = false
  })
  ElMessage.info('已清空选择')
}

const invertSelection = () => {
  filteredTables.value.forEach(table => {
    table.selected = !table.selected
  })
  ElMessage.info('已反选当前筛选结果')
}

const pinSelected = () => {
  const selectedTables = props.dataSources.filter(t => t.selected)
  selectedTables.forEach(table => {
    table.pinned = true
  })
  ElMessage.success(`已置顶 ${selectedTables.length} 个数据源`)
}

// 切换置顶状态
const togglePin = (table: DataSource) => {
  table.pinned = !table.pinned
  ElMessage.success(table.pinned ? `${table.name} 已置顶` : `${table.name} 已取消置顶`)
}

// 处理表格操作
const handleTableAction = (table: DataSource, command: string) => {
  switch (command) {
    case 'info':
      emit('info', table)
      break
    case 'copy':
      navigator.clipboard.writeText(table.id).then(() => {
        ElMessage.success('ID 已复制到剪贴板')
      })
      break
    case 'export':
      // 导出配置逻辑
      const config = {
        id: table.id,
        name: table.name,
        type: table.type,
        selected: table.selected,
        pinned: table.pinned
      }
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${table.name}-config.json`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success('配置已导出')
      break
  }
}

// 获取空状态标题
const getEmptyStateTitle = () => {
  if (searchKeyword.value) {
    return '未找到匹配的数据源'
  }
  if (filterType.value === 'selected') {
    return '暂无已选择的数据源'
  }
  if (filterType.value === 'pinned') {
    return '暂无置顶的数据源'
  }
  return '暂无可用的数据源'
}

// 获取空状态副标题
const getEmptyStateSubtitle = () => {
  if (searchKeyword.value) {
    return `搜索 "${searchKeyword.value}" 没有找到相关结果，请尝试其他关键词`
  }
  if (filterType.value === 'selected') {
    return '请先选择一些数据源，然后可以在这里查看'
  }
  if (filterType.value === 'pinned') {
    return '您可以通过点击星标图标来置顶常用的数据源'
  }
  return '系统中还没有配置任何数据源，请先添加数据源'
}

// 获取数据源类型标签
const getDataSourceTypeLabel = (type: string) => {
  // 处理 undefined 或空值的情况
  if (!type) {
    return '未知'
  }
  
  const typeMap: Record<string, string> = {
    'mysql': 'MySQL',
    'excel': 'Excel',
    'api': 'API',
    'csv': 'CSV',
    'postgresql': 'PostgreSQL',
    'sqlite': 'SQLite'
  }
  return typeMap[type] || type.toUpperCase()
}

// 获取数据源类型颜色
const getDataSourceTypeColor = (type: string) => {
  // 处理 undefined 或空值的情况
  if (!type) {
    return 'info'
  }
  
  const colorMap: Record<string, string> = {
    'mysql': 'primary',
    'excel': 'success',
    'api': 'warning',
    'csv': 'info',
    'postgresql': 'primary',
    'sqlite': 'info'
  }
  return colorMap[type] || 'default'
}

// 预览单个表
const previewTable = (table: DataSource) => {
  emit('preview', table)
}

// 处理重试
const handleRetry = () => {
  emit('retry')
}

// 确认选择
const confirmSelection = async () => {
  isConfirming.value = true
  
  try {
    // 模拟确认过程
    await new Promise(resolve => setTimeout(resolve, 500))
    
    const selectedTables = props.dataSources.filter(table => table.selected)
    emit('confirm', selectedTables)
    
    ElMessage.success(`已确认选择 ${selectedTables.length} 个数据源`)
    
    visible.value = false
    emit('update:modelValue', false)
  } finally {
    isConfirming.value = false
  }
}

// 监听 visible 变化以同步到父组件
watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
})

// 键盘快捷键支持
const handleKeydown = (event: KeyboardEvent) => {
  if (!visible.value) return
  
  switch (event.key) {
    case 'Escape':
      handleClose()
      break
    case 'Enter':
      if (event.ctrlKey || event.metaKey) {
        confirmSelection()
      }
      break
    case 'a':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        selectAll()
      }
      break
  }
}

// 添加键盘事件监听
watch(visible, (newValue) => {
  if (newValue) {
    document.addEventListener('keydown', handleKeydown)
  } else {
    document.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.data-source-selector-dialog {
  --el-dialog-padding-primary: 20px;
}

/* 搜索和筛选区域 */
.search-filter-section {
  margin-bottom: 20px;
}

.search-input {
  margin-bottom: 12px;
}

.search-tip-icon {
  color: var(--el-text-color-placeholder);
  cursor: help;
}

.quick-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

/* 批量操作工具栏 */
.batch-actions {
  margin-bottom: 16px;
}

.batch-action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* 加载状态 - 增强版 */
.loading-container {
  padding: 40px 20px;
  text-align: center;
}

.loading-animation {
  margin-bottom: 20px;
}

.loading-progress {
  margin-top: 16px;
  max-width: 200px;
  margin-left: auto;
  margin-right: auto;
}

.loading-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 错误状态 - 增强版 */
.error-container {
  padding: 20px;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

/* 空状态 - 增强版 */
.empty-state {
  padding: 20px;
}

.empty-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

/* 数据源列表 - 增强版 */
.table-list {
  max-height: 400px;
  overflow: hidden;
}

.table-list-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}

.list-stats {
  color: var(--el-text-color-secondary);
}

.sort-options {
  display: flex;
  align-items: center;
}

/* 数据源项目 */
.table-items {
  position: relative;
}

.table-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.3s ease;
  cursor: pointer;
  background-color: var(--el-bg-color);
}

.table-item:last-child {
  margin-bottom: 0;
}

.table-item:hover {
  background-color: var(--el-fill-color-lighter);
  border-color: var(--el-color-primary-light-7);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.table-item.selected {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}

.table-item.pinned {
  border-left: 4px solid var(--el-color-warning);
}

.table-item.highlighted {
  background-color: var(--el-color-info-light-9);
  border-color: var(--el-color-info-light-5);
}

.table-checkbox {
  flex: 1;
}

.table-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.table-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 15px;
  line-height: 1.4;
}

.table-name :deep(mark) {
  background-color: var(--el-color-warning-light-7);
  color: var(--el-color-warning-dark-2);
  padding: 1px 2px;
  border-radius: 2px;
}

.table-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.table-description {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.table-id {
  font-family: monospace;
  background-color: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 3px;
}

.table-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.type-tag {
  font-size: 11px;
  font-weight: 500;
}

.pin-icon {
  font-size: 14px;
}

/* 操作按钮 */
.table-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.table-actions .el-button {
  transition: all 0.2s ease;
}

.table-actions .el-button:hover {
  transform: scale(1.05);
}

.table-actions .el-button.pinned {
  background-color: var(--el-color-warning-light-9);
}

.preview-btn {
  font-size: 12px;
}

/* 动画效果 */
.table-item-enter-active,
.table-item-leave-active {
  transition: all 0.3s ease;
}

.table-item-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.table-item-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.table-item-move {
  transition: transform 0.3s ease;
}

/* 底部操作区域 - 增强版 */
.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.selection-summary {
  display: flex;
  align-items: center;
}

.no-selection {
  color: var(--el-text-color-placeholder);
  font-size: 14px;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.action-buttons .el-button {
  min-width: 80px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-source-selector-dialog {
    width: 95% !important;
    margin: 5vh auto;
  }
  
  .quick-filters {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .table-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .table-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .footer-actions {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .action-buttons {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .batch-action-buttons {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .table-description {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .empty-actions {
    flex-direction: column;
  }
}

/* 无障碍支持 */
@media (prefers-reduced-motion: reduce) {
  .table-item,
  .table-item-enter-active,
  .table-item-leave-active,
  .table-item-move,
  .loading-icon {
    transition: none;
    animation: none;
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .table-item {
    border-width: 2px;
  }
  
  .table-item.selected {
    border-width: 3px;
  }
  
  .table-name :deep(mark) {
    background-color: yellow;
    color: black;
  }
}

/* 深色模式优化 */
@media (prefers-color-scheme: dark) {
  .table-item:hover {
    box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
  }
}
</style>