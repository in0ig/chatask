<template>
  <div class="data-source-list">
    <el-card class="source-card" v-for="source in dataSources" :key="source.id">
      <div class="source-header">
        <el-tag :type="source.is_active ? 'success' : 'info'">{{ source.is_active ? '激活' : '未激活' }}</el-tag>
        <h3>{{ source.name }}</h3>
      </div>
      <div class="source-info">
        <p><strong>类型：</strong>{{ source.type }}</p>
        <p><strong>连接：</strong>{{ source.connection_string || source.file_path }}</p>
        <p><strong>创建时间：</strong>{{ source.created_at }}</p>
      </div>
      <div class="source-actions">
        <el-button size="small" type="primary" @click="editSource(source)">编辑</el-button>
        <el-button size="small" @click="toggleSource(source)">{{ source.is_active ? '停用' : '激活' }}</el-button>
        <el-button size="small" type="danger" @click="deleteSource(source)">删除</el-button>
      </div>
    </el-card>
    
    <el-button type="primary" @click="addNewSource" class="add-source-btn">添加数据源</el-button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useDataPrepStore } from '@/store/modules/dataPrep';

const dataPrepStore = useDataPrepStore();

// 从 store 获取数据源列表
const dataSources = computed(() => dataPrepStore.dataSources);

// 添加新数据源
const addNewSource = () => {
  dataPrepStore.openAddDataSourceDialog();
};

// 编辑数据源
const editSource = (source) => {
  dataPrepStore.openEditDataSourceDialog(source);
};

// 切换数据源激活状态
const toggleSource = (source) => {
  dataPrepStore.toggleDataSourceActive(source.id);
};

// 删除数据源
const deleteSource = (source) => {
  dataPrepStore.deleteDataSource(source.id);
};
</script>

<style scoped>
.data-source-list {
  padding: 16px;
}

.source-card {
  margin-bottom: 16px;
}

.source-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.source-header h3 {
  margin: 0 0 0 12px;
  font-size: 16px;
}

.source-info {
  margin-bottom: 16px;
  color: #606266;
}

.source-info p {
  margin: 4px 0;
}

.source-actions {
  display: flex;
  gap: 8px;
}

.add-source-btn {
  margin-top: 16px;
}
</style>