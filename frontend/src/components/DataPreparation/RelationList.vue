<template>
  <div class="relation-list-container">
    <el-table :data="relations" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80"></el-table-column>
      <el-table-column prop="source_table" label="源数据表"></el-table-column>
      <el-table-column prop="source_column" label="源列"></el-table-column>
      <el-table-column prop="target_table" label="目标数据表"></el-table-column>
      <el-table-column prop="target_column" label="目标列"></el-table-column>
      <el-table-column prop="type" label="关联类型"></el-table-column>
      <el-table-column label="操作" width="120">
        <template #default>
          <el-button type="text" size="small">编辑</el-button>
          <el-button type="text" size="small">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && relations.length === 0" class="empty-state">
      <p>暂无数据, 请添加表关联</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const loading = ref(true);
const relations = ref([]);

// Mock data for now
const mockRelations = [
  { id: 1, source_table: 'orders', source_column: 'customer_id', target_table: 'customers', target_column: 'id', type: 'Many-to-One' },
  { id: 2, source_table: 'order_items', source_column: 'order_id', target_table: 'orders', target_column: 'id', type: 'Many-to-One' },
  { id: 3, source_table: 'order_items', source_column: 'product_id', target_table: 'products', target_column: 'id', type: 'Many-to-One' },
];

onMounted(() => {
  setTimeout(() => {
    relations.value = mockRelations;
    loading.value = false;
  }, 1000);
});
</script>

<style scoped>
.relation-list-container {
  /* No specific styles needed here for now */
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #909399;
}
</style>
