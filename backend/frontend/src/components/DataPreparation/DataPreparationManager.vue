<template>
  <div class="data-preparation-manager">
    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" class="tabs-container" @tab-click="handleTabClick">
      <el-tab-pane
        label="数据源"
        name="datasources"
        :key="'datasources'"
      >
        <div class="tab-content">
          <DataSourceList />
        </div>
      </el-tab-pane>
      
      <el-tab-pane
        label="数据表"
        name="datatables"
        :key="'datatables'"
      >
        <div class="tab-content">
          <DataTableList />
        </div>
      </el-tab-pane>
      
      <el-tab-pane
        label="字典表"
        name="dictionaries"
        :key="'dictionaries'"
      >
        <div class="tab-content">
          <DictionaryTree />
        </div>
      </el-tab-pane>
      
      <el-tab-pane
        label="表关联"
        name="relations"
        :key="'relations'"
      >
        <div class="tab-content">
          <TableRelationList />
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <!-- 统一加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-loading
        :fullscreen="true"
        :text="'加载中...'
        :spinner="'el-icon-loading'"
        :background="'rgba(0, 0, 0, 0.7)'"
      />
    </div>
    
    <!-- 统一错误处理 -->
    <div v-else-if="error" class="error-state">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="true"
        @close="handleErrorClose"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useDataPrepStore } from '@/store/modules/dataPrep';
import DataSourceList from './DataSourceList.vue';
import DataTableList from './DataTableList.vue';
import DictionaryTree from './DictionaryTree.vue';
import TableRelationList from './TableRelationList.vue';

// Pinia store
const dataPrepStore = useDataPrepStore();

// 状态管理
const activeTab = ref('datasources');
const loading = ref(false);
const error = ref(null);

// 标签页切换处理
const handleTabClick = (tab) => {
  activeTab.value = tab.name;
};

// 加载状态管理
const startLoading = () => {
  loading.value = true;
  error.value = null;
};

const stopLoading = () => {
  loading.value = false;
};

// 错误处理
const handleError = (errorMessage) => {
  error.value = errorMessage;
  loading.value = false;
};

const handleErrorClose = () => {
  error.value = null;
};

// 初始化时加载数据
const initialize = async () => {
  startLoading();
  try {
    await dataPrepStore.fetchAllData();
  } catch (err) {
    handleError(err.message || '加载数据准备数据失败');
  } finally {
    stopLoading();
  }
};

// 组件挂载时初始化
initialize();
</script>

<style scoped>
.data-preparation-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tabs-container {
  flex: 1;
}

.tab-content {
  height: calc(100% - 40px);
  padding: 16px;
  overflow-y: auto;
}

.loading-state {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
}

.error-state {
  margin: 16px;
}
</style>