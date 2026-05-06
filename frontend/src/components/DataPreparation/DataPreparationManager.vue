<template>
  <div class="data-preparation-manager">
    <!-- 标签页导航 -->
    <el-tabs
      v-model="activeTab"
      class="tabs-container"
      @tab-click="handleTabClick"
    >
      <el-tab-pane
        label="数据源"
        name="datasource"
        class="tab-pane"
      >
        <DataSourceList />
      </el-tab-pane>
      
      <el-tab-pane
        label="数据表"
        name="datatable"
        class="tab-pane"
      >
        <DataTableList />
      </el-tab-pane>
      
      <el-tab-pane
        label="字典表"
        name="dictionary"
        class="tab-pane"
      >
        <DictionaryTree />
      </el-tab-pane>
      
      <el-tab-pane
        label="表关联"
        name="relation"
        class="tab-pane"
      >
        <TableRelationList />
      </el-tab-pane>
    </el-tabs>
    
    <!-- 加载状态遮罩 -->
    <div 
      class="loading-overlay" 
      :class="{ 'show-loading': loading }"
    >
      <el-loading
        :text="loadingText"
        :spinner="'el-icon-loading'"
        :background="'rgba(0, 0, 0, 0.5)'"
      />
    </div>
    
    <!-- 错误提示 -->
    <div 
      class="error-message" 
      :class="{ 'show-error': error }"
    >
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="true"
        @close="clearError"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { ElMessage } from 'element-plus'
import DataSourceList from './DataSourceList.vue'
import DataTableList from './DataTableList.vue'
import DictionaryTree from './DictionaryTree.vue'
import TableRelationList from './TableRelationList.vue'

// 状态管理
const dataPrepStore = useDataPreparationStore()

// 激活的标签页
const activeTab = ref('datasource')

// 加载状态
const loading = ref(false)
const loadingText = ref('正在加载数据...')

// 错误状态
const error = ref('')

// 监听数据源加载状态
const dataSourceLoading = computed(() => dataPrepStore.dataSourceLoading)
const dataTableLoading = computed(() => dataPrepStore.dataTablesLoading)
const dictionaryLoading = computed(() => dataPrepStore.dictionariesLoading)
const relationLoading = computed(() => dataPrepStore.tableRelationsLoading)

// 统一加载状态计算
const isAnyLoading = computed(() => {
  return dataSourceLoading.value || 
         dataTableLoading.value || 
         dictionaryLoading.value || 
         relationLoading.value
})

// 监听当前标签页变化，自动加载对应数据
const handleTabClick = (tab: any) => {
  activeTab.value = tab.name
  loadTabData(tab.name)
}

// 根据标签页加载对应数据
const loadTabData = (tabName: string) => {
  loading.value = true
  error.value = ''
  
  switch (tabName) {
    case 'datasource':
      dataPrepStore.fetchDataSources().catch(err => {
        error.value = '加载数据源失败，请稍后重试'
        console.error('加载数据源失败:', err)
      })
      break
    case 'datatable':
      dataPrepStore.fetchDataTables().catch(err => {
        error.value = '加载数据表失败，请稍后重试'
        console.error('加载数据表失败:', err)
      })
      break
    case 'dictionary':
      dataPrepStore.fetchDictionaries().catch(err => {
        error.value = '加载字典表失败，请稍后重试'
        console.error('加载字典表失败:', err)
      })
      break
    case 'relation':
      dataPrepStore.fetchTableRelations().catch(err => {
        error.value = '加载表关联失败，请稍后重试'
        console.error('加载表关联失败:', err)
      })
      break
  }
  
  // 延迟关闭加载状态，避免闪烁
  setTimeout(() => {
    loading.value = false
  }, 300)
}

// 清除错误信息
const clearError = () => {
  error.value = ''
}

// 初始化：加载默认标签页数据
loadTabData(activeTab.value)
</script>

<style scoped>
.data-preparation-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.tabs-container {
  flex: 0 0 auto;
  border-bottom: 1px solid #e4e7ed;
}

.tab-pane {
  height: calc(100% - 50px);
  overflow-y: auto;
  padding: 20px;
}

/* 加载遮罩层样式 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.3s ease;
}

.loading-overlay.show-loading {
  background-color: rgba(0, 0, 0, 0.5);
}

/* 错误提示样式 */
.error-message {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1001;
  width: 80%;
  max-width: 600px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.error-message.show-error {
  opacity: 1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tab-pane {
    padding: 15px;
  }
  
  .error-message {
    width: 90%;
  }
}

@media (max-width: 480px) {
  .tab-pane {
    padding: 10px;
  }
}
</style>