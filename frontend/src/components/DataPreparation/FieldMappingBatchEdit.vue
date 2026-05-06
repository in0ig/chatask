<template>
  <div class="field-mapping-batch-edit">
    <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
      <el-alert
        title="批量编辑字段映射"
        :description="`将对选中的 ${mappings.length} 个字段映射进行批量修改`"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <!-- 选中字段列表 -->
      <div class="selected-fields">
        <h4>选中的字段</h4>
        <div class="fields-list">
          <el-tag
            v-for="mapping in mappings"
            :key="mapping.field_id"
            size="small"
            style="margin: 4px;"
          >
            {{ mapping.field_name }}
          </el-tag>
        </div>
      </div>

      <el-divider />

      <!-- 批量编辑选项 -->
      <div class="batch-edit-options">
        <h4>批量修改选项</h4>
        
        <el-form-item>
          <el-checkbox v-model="editOptions.dictionary" label="修改关联字典" />
        </el-form-item>
        
        <el-form-item v-if="editOptions.dictionary" label="关联字典">
          <el-select
            v-model="formData.dictionary_id"
            placeholder="选择字典"
            clearable
            filterable
            style="width: 100%;"
          >
            <el-option
              v-for="dict in dictionaries"
              :key="dict.id"
              :label="dict.name"
              :value="dict.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="editOptions.required" label="修改必填状态" />
        </el-form-item>
        
        <el-form-item v-if="editOptions.required" label="必填状态">
          <el-radio-group v-model="formData.is_required">
            <el-radio :label="true">必填</el-radio>
            <el-radio :label="false">非必填</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="editOptions.valueRange" label="修改取值范围" />
        </el-form-item>
        
        <el-form-item v-if="editOptions.valueRange" label="取值范围">
          <el-input
            v-model="formData.value_range"
            placeholder="如：1-100, A|B|C"
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="editOptions.defaultValue" label="修改默认值" />
        </el-form-item>
        
        <el-form-item v-if="editOptions.defaultValue" label="默认值">
          <el-input
            v-model="formData.default_value"
            placeholder="设置默认值"
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="editOptions.businessMeaning" label="追加业务含义" />
        </el-form-item>
        
        <el-form-item v-if="editOptions.businessMeaning" label="业务含义后缀">
          <el-input
            v-model="formData.business_meaning_suffix"
            type="textarea"
            :rows="3"
            placeholder="将追加到现有业务含义后面"
          />
        </el-form-item>
      </div>

      <!-- 预览变更 -->
      <div class="preview-changes" v-if="hasChanges">
        <h4>变更预览</h4>
        <el-table :data="previewData" border size="small" max-height="300">
          <el-table-column prop="field_name" label="字段名称" width="120" />
          <el-table-column prop="change_type" label="变更类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="getChangeTypeColor(row.change_type)">
                {{ row.change_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="old_value" label="原值" min-width="150" />
          <el-table-column prop="new_value" label="新值" min-width="150" />
        </el-table>
      </div>
    </el-form>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button 
        type="primary" 
        @click="handleSubmit" 
        :loading="loading"
        :disabled="!hasChanges"
      >
        确定修改
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

// Props
interface Props {
  mappings: any[]
  dictionaries: any[]
  loading: boolean
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  submit: [editData: any]
  cancel: []
}>()

// 表单引用
const formRef = ref<FormInstance>()

// 编辑选项
const editOptions = reactive({
  dictionary: false,
  required: false,
  valueRange: false,
  defaultValue: false,
  businessMeaning: false
})

// 表单数据
const formData = reactive({
  dictionary_id: '',
  is_required: false,
  value_range: '',
  default_value: '',
  business_meaning_suffix: ''
})

// 验证规则
const rules: FormRules = {
  // 可以添加验证规则
}

// 计算属性
const hasChanges = computed(() => {
  return Object.values(editOptions).some(option => option)
})

const previewData = computed(() => {
  const changes: any[] = []
  
  props.mappings.forEach(mapping => {
    if (editOptions.dictionary) {
      const dictName = formData.dictionary_id ? 
        props.dictionaries.find(d => d.id === formData.dictionary_id)?.name || '未知字典' :
        '无'
      
      changes.push({
        field_name: mapping.field_name,
        change_type: '关联字典',
        old_value: mapping.dictionary_name || '无',
        new_value: dictName
      })
    }
    
    if (editOptions.required) {
      changes.push({
        field_name: mapping.field_name,
        change_type: '必填状态',
        old_value: mapping.is_required ? '必填' : '非必填',
        new_value: formData.is_required ? '必填' : '非必填'
      })
    }
    
    if (editOptions.valueRange) {
      changes.push({
        field_name: mapping.field_name,
        change_type: '取值范围',
        old_value: mapping.value_range || '无',
        new_value: formData.value_range || '无'
      })
    }
    
    if (editOptions.defaultValue) {
      changes.push({
        field_name: mapping.field_name,
        change_type: '默认值',
        old_value: mapping.default_value || '无',
        new_value: formData.default_value || '无'
      })
    }
    
    if (editOptions.businessMeaning && formData.business_meaning_suffix) {
      changes.push({
        field_name: mapping.field_name,
        change_type: '业务含义',
        old_value: mapping.business_meaning || '无',
        new_value: (mapping.business_meaning || '') + formData.business_meaning_suffix
      })
    }
  })
  
  return changes
})

// 方法
const getChangeTypeColor = (changeType: string) => {
  const colorMap: Record<string, string> = {
    '关联字典': 'primary',
    '必填状态': 'warning',
    '取值范围': 'info',
    '默认值': 'success',
    '业务含义': 'primary'
  }
  return colorMap[changeType] || 'default'
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    
    if (!hasChanges.value) {
      ElMessage.warning('请至少选择一个修改选项')
      return
    }

    // 构建提交数据
    const submitData: any = {}
    
    if (editOptions.dictionary) {
      submitData.dictionary_id = formData.dictionary_id
    }
    
    if (editOptions.required) {
      submitData.is_required = formData.is_required
    }
    
    if (editOptions.valueRange) {
      submitData.value_range = formData.value_range
    }
    
    if (editOptions.defaultValue) {
      submitData.default_value = formData.default_value
    }
    
    if (editOptions.businessMeaning && formData.business_meaning_suffix) {
      submitData.business_meaning_suffix = formData.business_meaning_suffix
    }

    emit('submit', submitData)
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped lang="scss">
.field-mapping-batch-edit {
  .selected-fields {
    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
    }

    .fields-list {
      padding: 12px;
      background: #f5f7fa;
      border-radius: 4px;
      min-height: 60px;
    }
  }

  .batch-edit-options {
    h4 {
      margin: 0 0 16px 0;
      color: #303133;
      font-size: 16px;
    }

    .el-form-item {
      margin-bottom: 16px;
    }
  }

  .preview-changes {
    margin-top: 20px;

    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 16px;
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