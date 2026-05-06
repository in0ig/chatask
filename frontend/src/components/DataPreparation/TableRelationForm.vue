<template>
  <div class="table-relation-form">
    <form @submit.prevent="handleSubmit" class="relation-form">
      <!-- 关联名称 -->
      <div class="form-group">
        <label for="relationName" class="form-label">关联名称 *</label>
        <input
          id="relationName"
          v-model="form.relationName"
          type="text"
          class="form-input"
          :class="{ 'form-error': errors.relationName }"
          placeholder="请输入关联名称"
          maxlength="100"
        />
        <div v-if="errors.relationName" class="error-message">{{ errors.relationName }}</div>
      </div>

      <!-- 主表选择 -->
      <div class="form-group">
        <label for="primaryTable" class="form-label">主表 *</label>
        <select
          id="primaryTable"
          v-model="form.primaryTableId"
          class="form-select"
          :class="{ 'form-error': errors.primaryTableId }"
          @change="onPrimaryTableChange"
        >
          <option value="">请选择主表</option>
          <option
            v-for="table in dataTables"
            :key="table.id"
            :value="table.id"
          >
            {{ table.name }}
          </option>
        </select>
        <div v-if="errors.primaryTableId" class="error-message">{{ errors.primaryTableId }}</div>
      </div>

      <!-- 主表字段选择 -->
      <div class="form-group">
        <label for="primaryField" class="form-label">主表字段 *</label>
        <select
          id="primaryField"
          v-model="form.primaryFieldId"
          class="form-select"
          :class="{ 'form-error': errors.primaryFieldId }"
          :disabled="!form.primaryTableId"
          @change="onPrimaryFieldChange"
        >
          <option value="">请选择主表字段</option>
          <option
            v-for="field in primaryFields"
            :key="field.id"
            :value="field.id"
          >
            {{ field.name }} ({{ field.type }})
          </option>
        </select>
        <div v-if="errors.primaryFieldId" class="error-message">{{ errors.primaryFieldId }}</div>
      </div>

      <!-- 从表选择 -->
      <div class="form-group">
        <label for="foreignTable" class="form-label">从表 *</label>
        <select
          id="foreignTable"
          v-model="form.foreignTableId"
          class="form-select"
          :class="{ 'form-error': errors.foreignTableId }"
          @change="onForeignTableChange"
        >
          <option value="">请选择从表</option>
          <option
            v-for="table in dataTables"
            :key="table.id"
            :value="table.id"
          >
            {{ table.name }}
          </option>
        </select>
        <div v-if="errors.foreignTableId" class="error-message">{{ errors.foreignTableId }}</div>
      </div>

      <!-- 从表字段选择 -->
      <div class="form-group">
        <label for="foreignField" class="form-label">从表字段 *</label>
        <select
          id="foreignField"
          v-model="form.foreignFieldId"
          class="form-select"
          :class="{ 'form-error': errors.foreignFieldId }"
          :disabled="!form.foreignTableId"
          @change="onForeignFieldChange"
        >
          <option value="">请选择从表字段</option>
          <option
            v-for="field in foreignFields"
            :key="field.id"
            :value="field.id"
          >
            {{ field.name }} ({{ field.type }})
          </option>
        </select>
        <div v-if="errors.foreignFieldId" class="error-message">{{ errors.foreignFieldId }}</div>
      </div>

      <!-- JOIN 类型选择 -->
      <div class="form-group">
        <label for="joinType" class="form-label">JOIN 类型 *</label>
        <select
          id="joinType"
          v-model="form.joinType"
          class="form-select"
          :class="{ 'form-error': errors.joinType }"
        >
          <option value="">请选择 JOIN 类型</option>
          <option value="INNER">INNER JOIN</option>
          <option value="LEFT">LEFT JOIN</option>
          <option value="RIGHT">RIGHT JOIN</option>
          <option value="FULL">FULL JOIN</option>
        </select>
        <div v-if="errors.joinType" class="error-message">{{ errors.joinType }}</div>
      </div>

      <!-- 字段类型兼容性提示 -->
      <div v-if="form.primaryFieldId && form.foreignFieldId" class="type-compatibility">
        <span :class="{ 'type-match': isTypeCompatible, 'type-mismatch': !isTypeCompatible }">
          {{ isTypeCompatible ? '✓ 字段类型兼容' : '✗ 字段类型不兼容' }}
        </span>
        <div v-if="!isTypeCompatible" class="type-mismatch-details">
          <p>主表字段: {{ primaryField?.name }} ({{ primaryField?.type }})</p>
          <p>从表字段: {{ foreignField?.name }} ({{ foreignField?.type }})</p>
          <p>建议: 请确保两个字段的数据类型匹配（如：字符串与字符串、数值与数值等）</p>
        </div>
      </div>

      <!-- 描述 -->
      <div class="form-group">
        <label for="description" class="form-label">描述</label>
        <textarea
          id="description"
          v-model="form.description"
          class="form-textarea"
          placeholder="请输入关联描述（可选）"
          rows="3"
          maxlength="500"
        ></textarea>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
          {{ isEditing ? '更新关联' : '创建关联' }}
        </button>
        <button type="button" class="btn btn-secondary" @click="handleCancel" :disabled="isSubmitting">
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { tableRelationApi, TableRelation, CreateTableRelationRequest, UpdateTableRelationRequest } from '@/services/tableRelationApi'
import { dataTableApi, DataTable, TableField } from '@/services/dataTableApi'

// 定义表单数据
const form = ref<CreateTableRelationRequest>({
  relationName: '',
  primaryTableId: '',
  primaryFieldId: '',
  foreignTableId: '',
  foreignFieldId: '',
  joinType: 'INNER',
  createdBy: 'user', // 默认值，实际应用中应从用户认证获取
})

// 定义错误对象
const errors = ref<Record<string, string>>({})

// 定义加载状态
const isSubmitting = ref(false)
const isEditing = ref(false)

// 定义数据源状态
const dataTables = ref<DataTable[]>([])
const primaryFields = ref<TableField[]>([])
const foreignFields = ref<TableField[]>([])

// 获取当前数据准备 store
const dataPreparationStore = useDataPreparationStore()

// 获取主表和从表字段
const primaryField = computed(() => {
  return primaryFields.value.find(field => field.id === form.value.primaryFieldId) || null
})

const foreignField = computed(() => {
  return foreignFields.value.find(field => field.id === form.value.foreignFieldId) || null
})

// 字段类型兼容性检查
const isTypeCompatible = computed(() => {
  if (!primaryField.value || !foreignField.value) return true
  
  const primaryType = primaryField.value.type.toLowerCase()
  const foreignType = foreignField.value.type.toLowerCase()
  
  // 定义类型组
  const stringTypes = ['varchar', 'char', 'text', 'mediumtext', 'longtext', 'nvarchar', 'nchar']
  const intTypes = ['int', 'integer', 'bigint', 'smallint', 'tinyint']
  const floatTypes = ['decimal', 'numeric', 'float', 'double', 'real']
  const dateTypes = ['date', 'datetime', 'timestamp', 'time']
  
  // 类型匹配规则
  if (stringTypes.includes(primaryType) && stringTypes.includes(foreignType)) return true
  if (intTypes.includes(primaryType) && intTypes.includes(foreignType)) return true
  if (floatTypes.includes(primaryType) && floatTypes.includes(foreignType)) return true
  if (dateTypes.includes(primaryType) && dateTypes.includes(foreignType)) return true
  if (primaryType === foreignType) return true
  
  return false
})

// 加载所有数据表
const loadDataTables = async () => {
  try {
    dataTables.value = await dataTableApi.getAll()
  } catch (error) {
    console.error('加载数据表失败:', error)
  }
}

// 根据表ID加载字段
const loadFields = async (tableId: string) => {
  try {
    const fields = await dataTableApi.getFields(tableId)
    return fields
  } catch (error) {
    console.error(`加载表 ${tableId} 的字段失败:`, error)
    return []
  }
}

// 主表变化时的处理
const onPrimaryTableChange = async () => {
  errors.value.primaryTableId = ''
  if (form.value.primaryTableId) {
    primaryFields.value = await loadFields(form.value.primaryTableId)
    form.value.primaryFieldId = '' // 重置字段选择
  } else {
    primaryFields.value = []
  }
}

// 从表变化时的处理
const onForeignTableChange = async () => {
  errors.value.foreignTableId = ''
  if (form.value.foreignTableId) {
    foreignFields.value = await loadFields(form.value.foreignTableId)
    form.value.foreignFieldId = '' // 重置字段选择
  } else {
    foreignFields.value = []
  }
}

// 主表字段变化时的处理
const onPrimaryFieldChange = () => {
  errors.value.primaryFieldId = ''
}

// 从表字段变化时的处理
const onForeignFieldChange = () => {
  errors.value.foreignFieldId = ''
}

// 表单验证
const validateForm = (): boolean => {
  const newErrors: Record<string, string> = {}
  
  if (!form.value.relationName.trim()) {
    newErrors.relationName = '关联名称不能为空'
  }
  
  if (!form.value.primaryTableId) {
    newErrors.primaryTableId = '请选择主表'
  }
  
  if (!form.value.primaryFieldId) {
    newErrors.primaryFieldId = '请选择主表字段'
  }
  
  if (!form.value.foreignTableId) {
    newErrors.foreignTableId = '请选择从表'
  }
  
  if (!form.value.foreignFieldId) {
    newErrors.foreignFieldId = '请选择从表字段'
  }
  
  if (!form.value.joinType) {
    newErrors.joinType = '请选择 JOIN 类型'
  }
  
  // 检查是否选择了相同的表
  if (form.value.primaryTableId === form.value.foreignTableId) {
    newErrors.foreignTableId = '主表和从表不能相同'
  }
  
  // 检查字段类型兼容性
  if (!isTypeCompatible.value) {
    newErrors.foreignFieldId = '主表字段和从表字段类型不兼容，请选择兼容的字段'
  }
  
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

// 提交表单
const handleSubmit = async () => {
  if (!validateForm()) return
  
  isSubmitting.value = true
  errors.value = {}
  
  try {
    if (isEditing.value && form.value.id) {
      // 更新模式
      const updateData: UpdateTableRelationRequest = {
        relationName: form.value.relationName,
        primaryTableId: form.value.primaryTableId,
        primaryFieldId: form.value.primaryFieldId,
        foreignTableId: form.value.foreignTableId,
        foreignFieldId: form.value.foreignFieldId,
        joinType: form.value.joinType,
        description: form.value.description,
        status: form.value.status
      }
      
      await tableRelationApi.update(form.value.id as string, updateData)
    } else {
      // 创建模式
      await tableRelationApi.create({
        relationName: form.value.relationName,
        primaryTableId: form.value.primaryTableId,
        primaryFieldId: form.value.primaryFieldId,
        foreignTableId: form.value.foreignTableId,
        foreignFieldId: form.value.foreignFieldId,
        joinType: form.value.joinType,
        description: form.value.description,
        createdBy: form.value.createdBy
      })
    }
    
    // 成功后重置表单
    resetForm()
    
    // 通知父组件表单已提交
    emit('submit')
    
  } catch (error: any) {
    console.error('表单提交失败:', error)
    if (error.response?.data?.detail) {
      errors.value.general = error.response.data.detail
    } else {
      errors.value.general = '提交失败，请重试'
    }
  } finally {
    isSubmitting.value = false
  }
}

// 取消操作
const handleCancel = () => {
  resetForm()
  emit('cancel')
}

// 重置表单
const resetForm = () => {
  form.value = {
    relationName: '',
    primaryTableId: '',
    primaryFieldId: '',
    foreignTableId: '',
    foreignFieldId: '',
    joinType: 'INNER',
    createdBy: 'user'
  }
  errors.value = {}
}

// 编辑模式 - 接收编辑数据
const props = defineProps({
  relation: {
    type: Object as () => TableRelation | null,
    default: null
  }
})

// 定义事件
const emit = defineEmits(['submit', 'cancel'])

// 初始化编辑模式
watch(
  () => props.relation,
  (newRelation) => {
    if (newRelation) {
      isEditing.value = true
      form.value = {
        id: newRelation.id,
        relationName: newRelation.relationName,
        primaryTableId: newRelation.primaryTableId,
        primaryFieldId: newRelation.primaryFieldId,
        foreignTableId: newRelation.foreignTableId,
        foreignFieldId: newRelation.foreignFieldId,
        joinType: newRelation.joinType,
        description: newRelation.description || '',
        status: newRelation.status,
        createdBy: newRelation.createdBy
      }
      
      // 加载主表和从表字段
      loadFields(newRelation.primaryTableId).then(fields => {
        primaryFields.value = fields
      })
      
      loadFields(newRelation.foreignTableId).then(fields => {
        foreignFields.value = fields
      })
    } else {
      isEditing.value = false
      resetForm()
    }
  },
  { immediate: true }
)

// 组件挂载时加载数据表
onMounted(() => {
  loadDataTables()
})
</script>

<style scoped>
.table-relation-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.relation-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.form-input,
.form-select,
.form-textarea {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.form-error {
  border-color: #dc3545;
}

.error-message {
  color: #dc3545;
  font-size: 12px;
  margin-top: 4px;
}

.type-compatibility {
  margin: 12px 0;
  padding: 10px;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.type-match {
  color: #28a745;
  font-weight: 600;
}

.type-mismatch {
  color: #dc3545;
  font-weight: 600;
}

.type-mismatch-details {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.type-mismatch-details p {
  margin: 4px 0;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0069d9;
}

.btn-primary:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #5a6268;
}

.btn-secondary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .table-relation-form {
    padding: 12px;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>