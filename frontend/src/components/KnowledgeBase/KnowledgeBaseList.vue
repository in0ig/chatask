<template>
  <div class="knowledge-base-list">
    <!-- Tab 切换和搜索 -->
    <div class="list-header">
      <!-- 第一行：搜索框 + 新增知识库按钮（右对齐） -->
      <div class="actions-row-1">
        <el-input
          v-model="searchKeyword"
          :placeholder="$t('knowledgeBase.search')"
          prefix-icon="Search"
          clearable
          style="width: 200px; margin-left: 10px;"
        />
        <el-button type="primary" @click="addKnowledgeBase">{{ $t('knowledgeBase.add') }}</el-button>
      </div>
      
      <!-- 第二行：分类标签 -->
      <div class="actions-row-2">
        <el-tabs v-model="activeTab" @tab-click="handleTabClick">
          <el-tab-pane :label="$t('knowledgeBase.tabAll')" name="all" />
          <el-tab-pane :label="$t('knowledgeBase.tabTerm')" name="TERM" />
          <el-tab-pane :label="$t('knowledgeBase.tabLogic')" name="LOGIC" />
          <el-tab-pane :label="$t('knowledgeBase.tabEvent')" name="EVENT" />
        </el-tabs>
      </div>
    </div>
    
    <!-- 知识库列表 -->
    <el-scrollbar style="height: calc(100% - 60px);">
      <div class="knowledge-base-cards">
        <div
          v-for="kb in filteredKnowledgeBases"
          :key="kb.id"
          :class="['knowledge-base-card', { 'selected': selectedKbId === kb.id }]"
          class="knowledge-base-card"
          @click="selectKnowledgeBase(kb.id)"
        >
          <div class="card-header">
            <h4 class="card-title">{{ kb.name }}</h4>
            <el-button
              type="danger"
              plain
              size="small"
              icon="Delete"
              @click.stop="confirmDelete(kb.id, kb.name)"
            />
          </div>
          <div class="card-body">
            <div class="body-row">
              <div class="tags-container">
                <span class="type-tag" :class="getTagClass(kb.type)">{{ getTagLabel(kb.type) }}</span>
                <span class="scope-tag" :class="getScopeClass(kb.scope)">{{ getScopeLabel(kb.scope) }}</span>
              </div>
              <el-switch
                v-model="kb.status"
                @click.stop
                @change="handleStatusChange(kb)"
                :active-text="$t('knowledgeBase.statusEnable')"
                :inactive-text="$t('knowledgeBase.statusDisable')"
              />
            </div>
            <div class="tables-info" v-if="kb.table_id">
              {{ $t('knowledgeBase.relatedTable') }}{{ kb.table_id }}
            </div>
            <div class="tables-info" v-else>
              <em>{{ $t('knowledgeBase.globalEffect') }}</em>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>
    
    <!-- 新增知识库弹窗 -->
    <AddKnowledgeBaseModal
      v-model:visible="isAddModalVisible"
      @submit="handleAddSuccess"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AddKnowledgeBaseModal from './AddKnowledgeBaseModal.vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { knowledgeBaseApi } from '@/services/api'

const { t } = useI18n()

// 初始化为空数组，将从API加载数据
const knowledgeBases = ref([])

const activeTab = ref('all')
const searchKeyword = ref('')
const selectedKbId = ref<string | null>(null)
const isAddModalVisible = ref(false)

// Tab 切换处理
const handleTabClick = (tab: any) => {
  activeTab.value = tab.name
}

// 过滤搜索结果和Tab筛选
const filteredKnowledgeBases = computed(() => {
  return knowledgeBases.value.filter(kb => {
    // Tab 筛选
    if (activeTab.value !== 'all' && kb.type !== activeTab.value) {
      return false
    }
    
    // 搜索筛选
    if (searchKeyword.value && 
        !kb.name.toLowerCase().includes(searchKeyword.value.toLowerCase())) {
      return false
    }
    
    return true
  })
})

// 选中知识库
const selectKnowledgeBase = (id: string) => {
  selectedKbId.value = id
  emit('select', id)
}

// 新增知识库
const addKnowledgeBase = () => {
  // 打开新增知识库弹窗
  isAddModalVisible.value = true
}

// 删除知识库（带确认）
const confirmDelete = (id: string, name: string) => {
  ElMessageBox.confirm(
    t('knowledgeBase.deleteConfirmMsg', { name }),
    t('knowledgeBase.deleteConfirmTitle'),
    {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    }
  ).then(() => {
    deleteKnowledgeBase(id)
  }).catch(() => {})
}

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    const response = await knowledgeBaseApi.getKnowledgeBases()
    knowledgeBases.value = response || []
  } catch (error) {
    console.error('Failed to load knowledge bases:', error)
    ElMessage.error(t('knowledgeBase.loadFail'))
  }
}

// 执行删除
const deleteKnowledgeBase = async (id: string) => {
  try {
    await knowledgeBaseApi.deleteKnowledgeBase(id)
    const index = knowledgeBases.value.findIndex(kb => kb.id === id)
    if (index !== -1) {
      knowledgeBases.value.splice(index, 1)
      if (selectedKbId.value === id) {
        selectedKbId.value = null
        emit('select', null)
      }
      emit('delete', id)
    }
    ElMessage.success(t('knowledgeBase.deleteSuccess'))
  } catch (error) {
    console.error('Failed to delete knowledge base:', error)
    ElMessage.error(t('knowledgeBase.deleteFail'))
  }
}

// 处理新增成功
const handleAddSuccess = async (newKnowledgeBase: any) => {
  try {
    const response = await knowledgeBaseApi.createKnowledgeBase(newKnowledgeBase)
    knowledgeBases.value.push(response)
    selectedKbId.value = response.id
    emit('select', response.id)
    ElMessage.success(t('knowledgeBase.createSuccess'))
  } catch (error) {
    const errorMessage = error.response?.data?.detail || t('knowledgeBase.createFail')
    ElMessage.error(errorMessage)
  } finally {
    isAddModalVisible.value = false
  }
}

// 处理启用/禁用状态变更
const handleStatusChange = async (kb: any) => {
  try {
    await knowledgeBaseApi.updateKnowledgeBase(kb.id, {
      name: kb.name,
      type: kb.type,
      scope: kb.scope,
      status: kb.status,
      table_id: kb.table_id
    })
    ElMessage.success(t('knowledgeBase.statusUpdateSuccess', { status: kb.status ? t('knowledgeBase.statusEnable') : t('knowledgeBase.statusDisable') }))
  } catch (error) {
    kb.status = !kb.status
    console.error('Failed to update knowledge base status:', error)
    ElMessage.error(t('knowledgeBase.statusUpdateFail'))
  }
}

// 获取标签文本
const getTagLabel = (type: string) => {
  const labels: Record<string, string> = {
    TERM: t('knowledgeBase.typeTerm'),
    LOGIC: t('knowledgeBase.typeLogic'),
    EVENT: t('knowledgeBase.typeEvent'),
  }
  return labels[type] || t('knowledgeBase.typeUnknown')
}

// 获取标签样式类
const getTagClass = (type: string) => {
  const classes: Record<string, string> = {
    TERM: 'tag-term',
    LOGIC: 'tag-logic',
    EVENT: 'tag-event'
  }
  return classes[type] || 'tag'
}

// 获取范围标签文本
const getScopeLabel = (scope: string) => {
  const labels: Record<string, string> = {
    GLOBAL: t('knowledgeBase.scopeGlobal'),
    TABLE: t('knowledgeBase.scopeTable'),
  }
  return labels[scope] || t('knowledgeBase.typeUnknown')
}

// 获取范围标签样式类
const getScopeClass = (scope: string) => {
  const classes: Record<string, string> = {
    GLOBAL: 'tag-global',
    TABLE: 'tag-table'
  }
  return classes[scope] || 'tag'
}

// 定义事件
const emit = defineEmits(['add', 'select', 'delete'])

// 组件挂载时加载知识库列表
onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.knowledge-base-list {
  height: 100%;
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}

.list-header .el-tabs .el-tab-pane {
  padding: 0;
}

.list-header .el-tabs .el-tab-bar {
  border-bottom: 1px solid #e4e7ed;
}

.list-header .el-tabs .el-tab-pane .el-tab-pane__item {
  padding: 8px 16px;
}

.actions-row-1 {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

.actions-row-2 {
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.knowledge-base-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  padding: 10px 0;
}

.knowledge-base-card {
  cursor: pointer;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background-color: white;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.knowledge-base-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: #dcdfe6;
}

.knowledge-base-card.selected {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.2);
  background-color: #f0f7ff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 500;
  flex: 1;
  margin-right: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-body {
  color: #606266;
}

.body-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.type-tag, .scope-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.tag-term {
  background-color: #409eff;
}

.tag-logic {
  background-color: #67c23a;
}

.tag-event {
  background-color: #e6a23c;
}

.tag-global {
  background-color: #909399;
}

.tag-table {
  background-color: #e6a23c;
}

.tables-info {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
}

.tables-info em {
  color: #c0c4cc;
}
</style>