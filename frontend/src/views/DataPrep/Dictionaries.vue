<template>
  <div class="dictionaries-container">
    <div class="header">
      <h1>字典表管理</h1>
      <el-button type="primary" @click="createDictionary">新建字典表</el-button>
    </div>
    
    <div class="dictionaries-list">
      <el-card 
        v-for="dict in dictionaries" 
        :key="dict.id" 
        class="dictionary-card"
      >
        <div class="dictionary-header">
          <div class="dictionary-info">
            <h3>{{ dict.table_name }}</h3>
            <span class="dictionary-type">字典表</span>
          </div>
          <div class="dictionary-actions">
            <el-button 
              size="small" 
              type="primary" 
              @click="editDictionary(dict)"
            >
              编辑
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteDictionary(dict)"
            >
              删除
            </el-button>
          </div>
        </div>
        
        <div class="dictionary-details">
          <p><strong>描述：</strong>{{ dict.description }}</p>
          <p><strong>字段：</strong>{{ dict.field_name }}</p>
          <p><strong>激活状态：</strong><el-tag :type="dict.is_active ? 'success' : 'info'">{{ dict.is_active ? '已激活' : '已停用' }}</el-tag></p>
        </div>
        
        <div class="dictionary-values">
          <h4>值映射</h4>
          <el-table 
            :data="dict.values" 
            style="width: 100%"
            size="small"
            border
          >
            <el-table-column 
              prop="value" 
              label="原始值" 
              width="120"
            />
            <el-table-column 
              prop="label" 
              label="显示标签" 
              width="150"
            />
            <el-table-column 
              prop="sort_order" 
              label="排序" 
              width="80"
            />
            <el-table-column 
              prop="description" 
              label="描述" 
              min-width="200"
            />
          </el-table>
        </div>
      </el-card>
    </div>
    
    <!-- 创建字典表模态框 -->
    <el-dialog 
      v-model="createDictModalVisible" 
      title="新建字典表" 
      width="700px"
    >
      <div class="create-dict-content">
        <el-form 
          :model="createDictForm" 
          label-width="120px" 
          class="create-dict-form"
        >
          <el-form-item label="表名">
            <el-input 
              v-model="createDictForm.table_name" 
              placeholder="请输入表名（如：gender、status）" 
            />
          </el-form-item>
          
          <el-form-item label="字段名">
            <el-input 
              v-model="createDictForm.field_name" 
              placeholder="请输入字段名（如：gender、status）" 
            />
          </el-form-item>
          
          <el-form-item label="描述">
            <el-input 
              v-model="createDictForm.description" 
              type="textarea" 
              :rows="3"
              placeholder="请输入字典表的描述信息"
            />
          </el-form-item>
          
          <el-form-item label="默认值">
            <el-input 
              v-model="createDictForm.default_value" 
              placeholder="请输入默认值（可选）"
            />
          </el-form-item>
          
          <el-form-item label="值映射">
            <div class="value-mapping">
              <el-button 
                type="primary" 
                size="small" 
                @click="addValue"
              >
                添加映射
              </el-button>
              
              <div class="value-list" v-if="createDictForm.values.length > 0">
                <div 
                  v-for="(value, index) in createDictForm.values" 
                  :key="index" 
                  class="value-item"
                >
                  <el-input 
                    v-model="value.value" 
                    placeholder="原始值" 
                    class="value-input"
                  />
                  <el-input 
                    v-model="value.label" 
                    placeholder="显示标签" 
                    class="label-input"
                  />
                  <el-input 
                    v-model.number="value.sort_order" 
                    placeholder="排序" 
                    class="sort-input"
                    type="number"
                  />
                  <el-input 
                    v-model="value.description" 
                    placeholder="描述" 
                    class="desc-input"
                  />
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="removeValue(index)"
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
        <el-button @click="createDictModalVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateDict">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 模拟数据
const dictionaries = ref([
  {
    id: '1',
    table_name: 'gender',
    field_name: 'gender',
    description: '性别字典表',
    default_value: 'unknown',
    is_active: true,
    values: [
      { value: 'M', label: '男', sort_order: 1, description: '男性' },
      { value: 'F', label: '女', sort_order: 2, description: '女性' },
      { value: 'U', label: '未知', sort_order: 3, description: '未指定性别' }
    ]
  },
  {
    id: '2',
    table_name: 'status',
    field_name: 'status',
    description: '订单状态字典表',
    default_value: 'pending',
    is_active: true,
    values: [
      { value: 'pending', label: '待处理', sort_order: 1, description: '订单已创建，待处理' },
      { value: 'confirmed', label: '已确认', sort_order: 2, description: '订单已确认' },
      { value: 'shipped', label: '已发货', sort_order: 3, description: '订单已发货' },
      { value: 'delivered', label: '已送达', sort_order: 4, description: '订单已送达' },
      { value: 'cancelled', label: '已取消', sort_order: 5, description: '订单已取消' }
    ]
  },
  {
    id: '3',
    table_name: 'department',
    field_name: 'department',
    description: '部门字典表',
    default_value: '',
    is_active: false,
    values: [
      { value: 'sales', label: '销售部', sort_order: 1, description: '销售部门' },
      { value: 'marketing', label: '市场部', sort_order: 2, description: '市场部门' },
      { value: 'hr', label: '人事部', sort_order: 3, description: '人事部门' }
    ]
  }
])

// 创建字典表模态框状态
const createDictModalVisible = ref(false)

// 创建字典表表单数据
const createDictForm = reactive({
  table_name: '',
  field_name: '',
  description: '',
  default_value: '',
  values: [
    { value: '', label: '', sort_order: 0, description: '' }
  ]
})

// 添加映射值
const addValue = () => {
  createDictForm.values.push({ value: '', label: '', sort_order: 0, description: '' })
}

// 移除映射值
const removeValue = (index) => {
  createDictForm.values.splice(index, 1)
}

// 编辑字典表
const editDictionary = (dict) => {
  ElMessage.info(`编辑字典表: ${dict.table_name}`)
}

// 删除字典表
const deleteDictionary = (dict) => {
  ElMessageBox.confirm(
    `确定要删除字典表 '${dict.table_name}' 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    const index = dictionaries.value.findIndex(d => d.id === dict.id)
    if (index !== -1) {
      dictionaries.value.splice(index, 1)
      ElMessage.success('字典表已删除')
    }
  }).catch(() => {
    // 取消删除
  })
}

// 创建新字典表
const createDictionary = () => {
  createDictModalVisible.value = true
  createDictForm.table_name = ''
  createDictForm.field_name = ''
  createDictForm.description = ''
  createDictForm.default_value = ''
  createDictForm.values = [{ value: '', label: '', sort_order: 0, description: '' }]
}

// 提交创建字典表
const submitCreateDict = () => {
  if (!createDictForm.table_name || !createDictForm.field_name) {
    ElMessage.error('表名和字段名是必填项')
    return
  }
  
  if (createDictForm.values.some(value => !value.value || !value.label)) {
    ElMessage.error('所有映射值都必须有原始值和显示标签')
    return
  }
  
  // 模拟创建成功
  const newDict = {
    id: Date.now().toString(),
    table_name: createDictForm.table_name,
    field_name: createDictForm.field_name,
    description: createDictForm.description,
    default_value: createDictForm.default_value,
    is_active: true,
    values: createDictForm.values.map(v => ({
      ...v,
      sort_order: v.sort_order || 0
    }))
  }
  
  dictionaries.value.unshift(newDict)
  ElMessage.success('字典表创建成功')
  createDictModalVisible.value = false
}
</script>

<style scoped>
.dictionaries-container {
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

.dictionaries-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.dictionary-card {
  transition: all 0.3s ease;
}

.dictionary-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.dictionary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.dictionary-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.dictionary-type {
  background-color: #e8f5e9;
  color: #2e7d32;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.dictionary-actions {
  display: flex;
  gap: 8px;
}

.dictionary-details {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.dictionary-values {
  margin-top: 16px;
}

.dictionary-values h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.create-dict-content {
  padding: 16px 0;
}

.create-dict-form {
  width: 100%;
}

.create-dict-form .el-form-item {
  margin-bottom: 20px;
}

.value-mapping {
  margin-top: 16px;
}

.value-list {
  margin-top: 16px;
}

.value-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.value-input {
  flex: 1;
}

.label-input {
  flex: 1;
}

.sort-input {
  flex: 0.5;
}

.desc-input {
  flex: 2;
}
</style>