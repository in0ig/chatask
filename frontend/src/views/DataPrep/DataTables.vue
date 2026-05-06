<template>
  <div class="data-tables-container">
    <div class="header">
      <h1>数据表管理</h1>
      <el-button type="primary" @click="createTable">新建数据表</el-button>
    </div>
    
    <div class="tables-list">
      <el-card 
        v-for="table in tables" 
        :key="table.id" 
        class="table-card"
      >
        <div class="table-header">
          <div class="table-info">
            <h3>{{ table.name }}</h3>
            <span class="table-type">{{ table.type }}</span>
          </div>
          <div class="table-actions">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewTable(table)"
            >
              查看
            </el-button>
            <el-button 
              size="small" 
              @click="editTable(table)"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteTable(table)"
            >
              删除
            </el-button>
            <el-button 
              size="small" 
              @click="viewRelationGraph(table.id)"
            >
              查看关系图
            </el-button>
          </div>
        </div>
        
        <div class="table-details">
          <p><strong>数据源：</strong>{{ table.source_name }}</p>
          <p><strong>字段数量：</strong>{{ table.field_count }}</p>
          <p><strong>记录数量：</strong>{{ table.record_count }}</p>
          <p><strong>创建时间：</strong>{{ formatDate(table.created_at) }}</p>
          <p><strong>更新时间：</strong>{{ formatDate(table.updated_at) }}</p>
        </div>
        
        <div class="table-preview">
          <h4>预览</h4>
          <el-table 
            :data="table.preview_data.slice(0, 3)" 
            style="width: 100%"
            size="small"
            border
          >
            <el-table-column 
              v-for="column in table.preview_columns" 
              :key="column.name" 
              :prop="column.name" 
              :label="column.label"
              :width="column.width"
            />
          </el-table>
        </div>
      </el-card>
    </div>
    
    <!-- 创建数据表模态框 -->
    <el-dialog 
      v-model="createTableModalVisible" 
      title="新建数据表" 
      width="600px"
    >
      <div class="create-table-content">
        <el-form 
          :model="createTableForm" 
          label-width="120px" 
          class="create-table-form"
        >
          <el-form-item label="数据源">
            <el-select 
              v-model="createTableForm.source_id" 
              placeholder="请选择数据源" 
              @change="loadTableStructure"
            >
              <el-option
                v-for="source in dataSources"
                :key="source.id"
                :label="source.name"
                :value="source.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="表名">
            <el-input 
              v-model="createTableForm.name" 
              placeholder="请输入表名" 
            />
          </el-form-item>
          
          <el-form-item label="表描述">
            <el-input 
              v-model="createTableForm.description" 
              type="textarea" 
              :rows="3"
              placeholder="请输入表的描述信息"
            />
          </el-form-item>
          
          <el-form-item label="字段结构">
            <div class="field-structure">
              <el-button 
                type="primary" 
                size="small" 
                @click="addField"
              >
                添加字段
              </el-button>
              
              <div class="field-list" v-if="createTableForm.fields.length > 0">
                <div 
                  v-for="(field, index) in createTableForm.fields" 
                  :key="index" 
                  class="field-item"
                >
                  <el-input 
                    v-model="field.name" 
                    placeholder="字段名" 
                    class="field-name"
                  />
                  <el-select 
                    v-model="field.type" 
                    placeholder="选择类型" 
                    class="field-type"
                  >
                    <el-option label="字符串" value="string" />
                    <el-option label="数字" value="number" />
                    <el-option label="日期" value="date" />
                    <el-option label="布尔" value="boolean" />
                  </el-select>
                  <el-input 
                    v-model="field.alias" 
                    placeholder="别名" 
                    class="field-alias"
                  />
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="removeField(index)"
                  >
                    删除
                  </el-button>
                </div>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="createTableModalVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateTable">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 模拟数据
const tables = ref([
  {
    id: '1',
    name: '销售记录',
    type: 'MySQL',
    source_name: '销售数据',
    field_count: 8,
    record_count: 12547,
    created_at: '2026-01-15T10:30:00Z',
    updated_at: '2026-01-15T10:30:00Z',
    preview_columns: [
      { name: 'id', label: 'ID', width: '80' },
      { name: 'product_name', label: '产品名称', width: '150' },
      { name: 'sales_amount', label: '销售额', width: '120' },
      { name: 'sale_date', label: '销售日期', width: '120' }
    ],
    preview_data: [
      { id: 1, product_name: 'iPhone 15', sales_amount: 8999, sale_date: '2026-01-10' },
      { id: 2, product_name: 'iPad Pro', sales_amount: 6999, sale_date: '2026-01-11' },
      { id: 3, product_name: 'MacBook Air', sales_amount: 8999, sale_date: '2026-01-12' }
    ]
  },
  {
    id: '2',
    name: '库存记录',
    type: 'Excel',
    source_name: '库存数据',
    field_count: 6,
    record_count: 892,
    created_at: '2026-01-14T09:15:00Z',
    updated_at: '2026-01-14T09:15:00Z',
    preview_columns: [
      { name: 'product_id', label: '产品ID', width: '100' },
      { name: 'product_name', label: '产品名称', width: '150' },
      { name: 'stock_quantity', label: '库存数量', width: '120' },
      { name: 'warehouse', label: '仓库', width: '100' }
    ],
    preview_data: [
      { product_id: 'P001', product_name: 'iPhone 15', stock_quantity: 120, warehouse: '北京仓' },
      { product_id: 'P002', product_name: 'iPad Pro', stock_quantity: 85, warehouse: '上海仓' },
      { product_id: 'P003', product_name: 'MacBook Air', stock_quantity: 92, warehouse: '广州仓' }
    ]
  }
])

const dataSources = ref([
  { id: '1', name: '销售数据' },
  { id: '2', name: '库存数据' },
  { id: '3', name: '客户数据' }
])

// 创建数据表模态框状态
const createTableModalVisible = ref(false)

// 创建表单数据
const createTableForm = reactive({
  source_id: '',
  name: '',
  description: '',
  fields: [
    { name: '', type: 'string', alias: '' }
  ]
})

// 格式化日期
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// 加载表结构
const loadTableStructure = () => {
  // 这里应该调用后端 API 获取数据源的表结构
  // 为演示目的，我们使用一个示例
  if (createTableForm.source_id === '1') {
    createTableForm.fields = [
      { name: 'id', type: 'number', alias: 'ID' },
      { name: 'product_name', type: 'string', alias: '产品名称' },
      { name: 'sales_amount', type: 'number', alias: '销售额' },
      { name: 'sale_date', type: 'date', alias: '销售日期' }
    ]
  } else if (createTableForm.source_id === '2') {
    createTableForm.fields = [
      { name: 'product_id', type: 'string', alias: '产品ID' },
      { name: 'product_name', type: 'string', alias: '产品名称' },
      { name: 'stock_quantity', type: 'number', alias: '库存数量' },
      { name: 'warehouse', type: 'string', alias: '仓库' }
    ]
  }
}

// 添加字段
const addField = () => {
  createTableForm.fields.push({ name: '', type: 'string', alias: '' })
}

// 移除字段
const removeField = (index) => {
  createTableForm.fields.splice(index, 1)
}

// 查看数据表
const viewTable = (table) => {
  ElMessage.info(`查看数据表: ${table.name}`)
}

// 编辑数据表
const editTable = (table) => {
  ElMessage.info(`编辑数据表: ${table.name}`)
}

// 删除数据表
const deleteTable = (table) => {
  ElMessageBox.confirm(
    `确定要删除数据表 '${table.name}' 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const index = tables.value.findIndex(t => t.id === table.id)
    if (index !== -1) {
      tables.value.splice(index, 1)
      ElMessage.success('数据表已删除')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 查看关系图
const viewRelationGraph = (tableId) => {
  router.push({
    path: '/data-prep/relations',
    query: { tableId }
  })
}

// 创建新数据表
const createTable = () => {
  createTableModalVisible.value = true
  createTableForm.source_id = ''
  createTableForm.name = ''
  createTableForm.description = ''
  createTableForm.fields = [{ name: '', type: 'string', alias: '' }]
}

// 提交创建数据表
const submitCreateTable = () => {
  if (!createTableForm.source_id || !createTableForm.name) {
    ElMessage.error('请填写必填字段')
    return
  }
  
  if (createTableForm.fields.some(field => !field.name)) {
    ElMessage.error('所有字段都必须有名称')
    return
  }
  
  // 模拟创建成功
  const newTable = {
    id: Date.now().toString(),
    name: createTableForm.name,
    type: dataSources.value.find(ds => ds.id === createTableForm.source_id)?.type || 'MySQL',
    source_name: dataSources.value.find(ds => ds.id === createTableForm.source_id)?.name || '',
    field_count: createTableForm.fields.length,
    record_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    preview_columns: createTableForm.fields.map(field => ({
      name: field.name,
      label: field.alias || field.name,
      width: '120'
    })),
    preview_data: []
  }
  
  tables.value.unshift(newTable)
  ElMessage.success('数据表创建成功')
  createTableModalVisible.value = false
}
</script>

<style scoped>
.data-tables-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.tables-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.table-card {
  transition: all 0.3s ease;
}

.table-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.table-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.table-type {
  background-color: #e8f5e9;
  color: #2e7d32;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.table-details {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.table-preview {
  margin-top: 16px;
}

.table-preview h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.create-table-content {
  padding: 16px 0;
}

.create-table-form {
  width: 100%;
}

.create-table-form .el-form-item {
  margin-bottom: 20px;
}

.field-structure {
  margin-top: 16px;
}

.field-list {
  margin-top: 16px;
}

.field-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.field-name {
  flex: 2;
}

.field-type {
  flex: 1;
}

.field-alias {
  flex: 1;
}
</style>