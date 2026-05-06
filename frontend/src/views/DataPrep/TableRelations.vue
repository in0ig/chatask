<template>
  <div class="table-relations-container">
    <div class="header">
      <h1>表关系图</h1>
      <el-button type="primary" @click="goBack">返回</el-button>
    </div>
    
    <div class="content">
      <TableRelationGraph 
        :tables="filteredTables" 
        :relations="filteredRelations" 
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TableRelationGraph from '@/components/DataPreparation/TableRelationGraph.vue'

const route = useRoute()
const router = useRouter()

// 模拟数据 - 在实际应用中，这里应该从后端API获取
const tables = ref([
  {
    id: '1',
    name: '销售记录',
    fields: ['id', 'product_id', 'sales_amount', 'sale_date', 'customer_id']
  },
  {
    id: '2',
    name: '产品信息',
    fields: ['id', 'name', 'price', 'category', 'supplier_id']
  },
  {
    id: '3',
    name: '客户信息',
    fields: ['id', 'name', 'email', 'phone', 'address']
  },
  {
    id: '4',
    name: '供应商信息',
    fields: ['id', 'name', 'contact', 'phone', 'address']
  }
])

const relations = ref([
  {
    id: '1',
    source_table_id: '1',
    target_table_id: '2',
    type: 'foreign-key',
    source_field: 'product_id',
    target_field: 'id'
  },
  {
    id: '2',
    source_table_id: '1',
    target_table_id: '3',
    type: 'foreign-key',
    source_field: 'customer_id',
    target_field: 'id'
  },
  {
    id: '3',
    source_table_id: '2',
    target_table_id: '4',
    type: 'foreign-key',
    source_field: 'supplier_id',
    target_field: 'id'
  }
])

// 根据查询参数过滤数据
const tableId = computed(() => route.query.tableId)

// 如果有指定的表ID，则只显示与该表相关的数据
const filteredTables = computed(() => {
  if (!tableId.value) return tables.value
  return tables.value.filter(table => table.id === tableId.value)
})

const filteredRelations = computed(() => {
  if (!tableId.value) return relations.value
  return relations.value.filter(relation => 
    relation.source_table_id === tableId.value || relation.target_table_id === tableId.value
  )
})

// 返回上一页
const goBack = () => {
  router.push('/data-prep/tables')
}
</script>

<style scoped>
.table-relations-container {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.content {
  flex: 1;
  overflow: hidden;
}
</style>