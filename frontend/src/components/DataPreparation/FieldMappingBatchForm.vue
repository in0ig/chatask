<template>
  <div class="field-mapping-batch-form">
    <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
      <el-alert
        title="批量字段映射"
        :description="`为 ${fields.length} 个未映射字段配置业务含义和字典关联`"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <!-- 全局设置 -->
      <div class="global-settings">
        <h4>全局设置</h4>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="默认字典">
              <el-select
                v-model="globalSettings.defaultDictionary"
                placeholder="选择默认字典"
                clearable
                filterable
                @change="applyGlobalDictionary"
              >
                <el-option
                  v-for="dict in dictionaries"
                  :key="dict.id"
                  :label="dict.name"
                  :value="dict.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认必填">
              <el-switch
                v-model="globalSettings.defaultRequired"
                @change="applyGlobalRequired"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 字段映射列表 -->
      <div class="field-mappings">
        <h4>字段映射配置</h4>
        <el-table :data="formData.mappings" border max-height="400">
          <el-table-column prop="field_name" label="字段名称" width="120" fixed="left">
            <template #default="{ row }">
              <div class="field-info">
                <span class="field-name">{{ row.field_name }}</span>
                <el-tag size="small" type="info">{{ row.field_type }}</el-tag>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="业务名称" width="150">
            <template #default="{ row, $index }">
              <el-input
                v-model="row.business_name"
                size="small"
                placeholder="必填"
                :class="{ 'is-error': !row.business_name }"
              />
            </template>
          </el-table-column>
          
          <el-table-column label="业务含义" min-width="200">
            <template #default="{ row }">
              <el-input
                v-model="row.business_meaning"
                type="textarea"
                :rows="2"
                size="small"
                placeholder="描述字段的业务含义"
              />
            </template>
          </el-table-column>
          
          <el-table-column label="关联字典" width="150">
            <template #default="{ row }">
              <el-select
                v-model="row.dictionary_id"
                size="small"
                clearable
                filterable
                placeholder="选择字典"
              >
                <el-option
                  v-for="dict in dictionaries"
                  :key="dict.id"
                  :label="dict.name"
                  :value="dict.id"
                />
              </el-select>
            </template>
          </el-table-column>
          
          <el-table-column label="取值范围" width="120">
            <template #default="{ row }">
              <el-input
                v-model="row.value_range"
                size="small"
                placeholder="如：1-100"
              />
            </template>
          </el-table-column>
          
          <el-table-column label="必填" width="80" align="center">
            <template #default="{ row }">
              <el-switch v-model="row.is_required" size="small" />
            </template>
          </el-table-column>
          
          <el-table-column label="默认值" width="100">
            <template #default="{ row }">
              <el-input
                v-model="row.default_value"
                size="small"
                placeholder="默认值"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 智能推荐 -->
      <div class="smart-suggestions" v-if="suggestions.length > 0">
        <h4>智能推荐</h4>
        <el-alert
          title="根据字段名称智能推荐业务含义"
          type="success"
          show-icon
          :closable="false"
          style="margin-bottom: 12px;"
        />
        <div class="suggestions-list">
          <el-tag
            v-for="suggestion in suggestions"
            :key="suggestion.field_name"
            type="success"
            size="small"
            style="margin: 4px;"
            @click="applySuggestion(suggestion)"
            class="clickable-tag"
          >
            {{ suggestion.field_name }} → {{ suggestion.business_name }}
          </el-tag>
        </div>
      </div>
    </el-form>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        确定配置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

// Props
interface Props {
  tableId: string
  fields: any[]
  dictionaries: any[]
  loading: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  submit: [mappings: any[]]
  cancel: []
}>()

// 表单引用
const formRef = ref<FormInstance>()

// 全局设置
const globalSettings = reactive({
  defaultDictionary: '',
  defaultRequired: false
})

// 表单数据
const formData = reactive({
  mappings: [] as any[]
})

// 验证规则
const rules: FormRules = {
  // 可以添加验证规则
}

// 智能推荐
const suggestions = ref<any[]>([])

// 计算属性
const validMappings = computed(() => {
  return formData.mappings.filter(mapping => mapping.business_name?.trim())
})

// 方法
const initializeForm = () => {
  formData.mappings = props.fields.map(field => ({
    field_id: field.field_id || `field-${field.field_name}`,
    field_name: field.field_name,
    field_type: field.field_type,
    business_name: '',
    business_meaning: '',
    dictionary_id: '',
    value_range: '',
    is_required: false,
    default_value: ''
  }))

  generateSmartSuggestions()
}

const generateSmartSuggestions = () => {
  // 基于字段名称的智能推荐
  const fieldNameMappings: Record<string, string> = {
    'id': 'ID',
    'user_id': '用户ID',
    'username': '用户名',
    'user_name': '用户名',
    'email': '邮箱地址',
    'phone': '手机号码',
    'mobile': '手机号码',
    'password': '密码',
    'status': '状态',
    'state': '状态',
    'type': '类型',
    'category': '分类',
    'name': '名称',
    'title': '标题',
    'description': '描述',
    'content': '内容',
    'created_at': '创建时间',
    'updated_at': '更新时间',
    'deleted_at': '删除时间',
    'create_time': '创建时间',
    'update_time': '更新时间',
    'delete_time': '删除时间',
    'sort': '排序',
    'order': '排序',
    'level': '级别',
    'priority': '优先级',
    'amount': '金额',
    'price': '价格',
    'quantity': '数量',
    'count': '数量'
  }

  suggestions.value = formData.mappings
    .filter(mapping => {
      const fieldName = mapping.field_name.toLowerCase()
      return fieldNameMappings[fieldName] || 
             Object.keys(fieldNameMappings).some(key => fieldName.includes(key))
    })
    .map(mapping => {
      const fieldName = mapping.field_name.toLowerCase()
      let businessName = fieldNameMappings[fieldName]
      
      if (!businessName) {
        // 模糊匹配
        const matchedKey = Object.keys(fieldNameMappings).find(key => fieldName.includes(key))
        if (matchedKey) {
          businessName = fieldNameMappings[matchedKey]
        }
      }
      
      return {
        field_name: mapping.field_name,
        business_name: businessName,
        field_id: mapping.field_id
      }
    })
}

const applySuggestion = (suggestion: any) => {
  const mapping = formData.mappings.find(m => m.field_id === suggestion.field_id)
  if (mapping) {
    mapping.business_name = suggestion.business_name
    mapping.business_meaning = `${suggestion.business_name}字段`
  }
}

const applyGlobalDictionary = () => {
  if (globalSettings.defaultDictionary) {
    formData.mappings.forEach(mapping => {
      if (!mapping.dictionary_id) {
        mapping.dictionary_id = globalSettings.defaultDictionary
      }
    })
  }
}

const applyGlobalRequired = () => {
  formData.mappings.forEach(mapping => {
    mapping.is_required = globalSettings.defaultRequired
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    
    if (validMappings.value.length === 0) {
      ElMessage.warning('请至少配置一个字段的业务名称')
      return
    }

    emit('submit', validMappings.value)
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

const handleCancel = () => {
  emit('cancel')
}

// 生命周期
onMounted(() => {
  initializeForm()
})
</script>

<style scoped lang="scss">
.field-mapping-batch-form {
  .global-settings {
    h4 {
      margin: 0 0 16px 0;
      color: #303133;
      font-size: 16px;
    }
  }

  .field-mappings {
    h4 {
      margin: 0 0 16px 0;
      color: #303133;
      font-size: 16px;
    }

    .field-info {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .field-name {
        font-weight: 500;
        color: #303133;
      }
    }

    .is-error {
      :deep(.el-input__wrapper) {
        border-color: #f56c6c;
      }
    }
  }

  .smart-suggestions {
    margin-top: 20px;

    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
    }

    .suggestions-list {
      .clickable-tag {
        cursor: pointer;
        transition: all 0.3s;

        &:hover {
          transform: scale(1.05);
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
      }
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid #e4e7ed;
  }
}
</style>