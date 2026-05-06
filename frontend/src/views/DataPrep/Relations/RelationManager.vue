<template>
  <div class="relation-manager-container">
    <div class="header">
      <h1 class="title">表关联管理</h1>
      <div class="view-switcher">
        <el-button-group>
          <el-button :type="currentView === 'list' ? 'primary' : 'default'" @click="currentView = 'list'">列表视图</el-button>
          <el-button :type="currentView === 'graph' ? 'primary' : 'default'" @click="currentView = 'graph'">图形视图</el-button>
        </el-button-group>
      </div>
    </div>

    <div class="content">
      <RelationTable v-if="currentView === 'list'" ref="relationTableRef">
        <template #form="{ formData, isEdit }">
          <RelationForm ref="relationFormRef" :initialData="formData" />
        </template>
      </RelationTable>
      <RelationGraph v-if="currentView === 'graph'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import RelationTable from '@/components/DataPreparation/RelationTable.vue';
import RelationForm from '@/components/DataPreparation/RelationForm.vue';
import RelationGraph from '@/components/DataPreparation/RelationGraph.vue';

const currentView = ref('list');
const relationTableRef = ref(null);
const relationFormRef = ref(null);

// 暴露方法给子组件使用
const getFormData = async () => {
  if (relationFormRef.value && relationFormRef.value.getFormData) {
    return await relationFormRef.value.getFormData();
  }
  return null;
};

// 提供给 RelationTable 使用的方法
defineExpose({
  getFormData
});
</script>

<style scoped>
.relation-manager-container {
  padding: 20px;
  background-color: #f5f7fa;
  height: 100%;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  font-size: 24px;
  font-weight: bold;
}

.content {
  background-color: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.graph-view-placeholder {
  text-align: center;
  padding: 40px;
  color: #909399;
}
</style>
