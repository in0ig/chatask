<template>
  <div class="table-relation-list">
    <el-card class="relation-card" v-for="relation in relations" :key="relation.id">
      <div class="relation-header">
        <h3>{{ relation.name }}</h3>
        <el-tag type="info">{{ relation.type }}</el-tag>
      </div>
      
      <div class="relation-details">
        <div class="relation-source">
          <h4>源表</h4>
          <p>{{ relation.source_table }}</p>
        </div>
        
        <div class="relation-arrow">
          <i class="el-icon-arrow-right"></i>
        </div>
        
        <div class="relation-target">
          <h4>目标表</h4>
          <p>{{ relation.target_table }}</p>
        </div>
      </div>
      
      <div class="relation-fields">
        <h4>关联字段</h4>
        <div class="field-pair" v-for="field in relation.fields" :key="field.id">
          <span class="field-source">{{ field.source_field }}</span>
          <span class="field-arrow">=</span>
          <span class="field-target">{{ field.target_field }}</span>
        </div>
      </div>
      
      <div class="relation-actions">
        <el-button size="small" type="primary" @click="editRelation(relation)">编辑</el-button>
        <el-button size="small" @click="viewRelationGraph(relation)">查看图</el-button>
        <el-button size="small" type="danger" @click="deleteRelation(relation)">删除</el-button>
      </div>
    </el-card>
    
    <el-button type="primary" @click="addNewRelation" class="add-relation-btn">添加表关联</el-button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useDataPrepStore } from '@/store/modules/dataPrep';

const dataPrepStore = useDataPrepStore();

// 从 store 获取表关联列表
const relations = computed(() => dataPrepStore.tableRelations);

// 添加新表关联
const addNewRelation = () => {
  dataPrepStore.openAddTableRelationDialog();
};

// 编辑表关联
const editRelation = (relation) => {
  dataPrepStore.openEditTableRelationDialog(relation);
};

// 查看关联图
const viewRelationGraph = (relation) => {
  dataPrepStore.openTableRelationGraphDialog(relation);
};

// 删除表关联
const deleteRelation = (relation) => {
  dataPrepStore.deleteTableRelation(relation.id);
};
</script>

<style scoped>
.table-relation-list {
  padding: 16px;
}

.relation-card {
  margin-bottom: 16px;
}

.relation-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.relation-header h3 {
  margin: 0 0 0 12px;
  font-size: 16px;
}

.relation-details {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.relation-source, .relation-target {
  flex: 1;
  text-align: center;
}

.relation-source h4, .relation-target h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #606266;
}

.relation-source p, .relation-target p {
  margin: 0;
  font-weight: bold;
}

.relation-arrow {
  margin: 0 16px;
  color: #909399;
}

.relation-fields {
  margin-bottom: 16px;
}

.relation-fields h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #606266;
}

.field-pair {
  display: flex;
  align-items: center;
  margin: 4px 0;
}

.field-source, .field-target {
  min-width: 100px;
  padding: 4px 8px;
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  font-size: 13px;
}

.field-arrow {
  margin: 0 8px;
  color: #909399;
}

.relation-actions {
  display: flex;
  gap: 8px;
}

.add-relation-btn {
  margin-top: 16px;
}
</style>