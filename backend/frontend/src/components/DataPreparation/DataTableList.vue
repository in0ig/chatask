<template>
  <div class="data-table-list">
    <el-table
      :data="dataTables"
      style="width: 100%"
      border
      :row-class-name="tableRowClassName"
    >
      <el-table-column
        prop="name"
        label="表名"
        width="200"
      >
      </el-table-column>
      
      <el-table-column
        prop="source_name"
        label="数据源"
        width="150"
      >
      </el-table-column>
      
      <el-table-column
        prop="row_count"
        label="行数"
        width="100"
      >
      </el-table-column>
      
      <el-table-column
        prop="column_count"
        label="列数"
        width="100"
      >
      </el-table-column>
      
      <el-table-column
        prop="created_at"
        label="创建时间"
        width="180"
      >
      </el-table-column>
      
      <el-table-column
        label="操作"
        width="200"
      >
        <template #default="scope">
          <el-button
            size="small"
            type="primary"
            @click="editTable(scope.row)"
          >
            编辑
          </el-button>
          <el-button
            size="small"
            @click="viewTableFields(scope.row)"
          >
            字段
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="deleteTable(scope.row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <div class="table-actions">
      <el-button type="primary" @click="addNewTable">添加数据表</el-button>
      <el-button @click="syncTables">同步表</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useDataPrepStore } from '@/store/modules/dataPrep';

const dataPrepStore = useDataPrepStore();

// 从 store 获取数据表列表
const dataTables = computed(() => dataPrepStore.dataTables);

// 表格行样式
const tableRowClassName = ({ row }) => {
  return row.is_active ? '' : 'disabled-row';
};

// 添加新数据表
const addNewTable = () => {
  dataPrepStore.openAddDataTableDialog();
};

// 编辑数据表
const editTable = (table) => {
  dataPrepStore.openEditDataTableDialog(table);
};

// 查看表字段
const viewTableFields = (table) => {
  dataPrepStore.openTableFieldsDialog(table);
};

// 删除数据表
const deleteTable = (table) => {
  dataPrepStore.deleteDataTable(table.id);
};

// 同步表
const syncTables = () => {
  dataPrepStore.syncTables();
};
</script>

<style scoped>
.data-table-list {
  padding: 16px;
}

.table-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.disabled-row {
  opacity: 0.6;
}
</style>