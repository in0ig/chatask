<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="100px"
    :loading="loading"
    class="dictionary-item-form"
  >
    <el-form-item label="项键" prop="item_key">
      <el-input v-model="form.item_key" placeholder="请输入字典项键" />
    </el-form-item>
    
    <el-form-item label="项值" prop="item_value">
      <el-input v-model="form.item_value" placeholder="请输入字典项值" />
    </el-form-item>
    
    <el-form-item label="描述" prop="description">
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="3"
        placeholder="请输入描述信息"
      />
    </el-form-item>
    
    <el-form-item label="排序" prop="sort_order">
      <el-input-number v-model="form.sort_order" :min="0" />
    </el-form-item>

    <el-form-item label="状态" prop="is_enabled">
      <el-switch
        v-model="form.is_enabled"
        active-text="启用"
        inactive-text="禁用"
      />
    </el-form-item>
    
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleSubmit">
        {{ mode === 'create' ? '创建' : '保存' }}
      </el-button>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import type { DictionaryItem } from '@/store/modules/dataPreparation'

// Props and Emits
interface Props {
  mode: 'create' | 'edit'
  item: DictionaryItem | null
  loading?: boolean
  dictionaryId: string  // 改为 string 类型，因为使用的是 UUID
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  (e: 'submit', data: Partial<DictionaryItem>): void
  (e: 'cancel'): void
}>()

// Form state and validation
const formRef = ref<FormInstance>()

const initialFormState = {
  item_key: '',
  item_value: '',
  description: '',
  sort_order: 0,
  is_enabled: true,
}

const form = reactive({ ...initialFormState })

const rules: FormRules = {
  item_key: [{ required: true, message: '请输入字典项键', trigger: 'blur' }],
  item_value: [{ required: true, message: '请输入字典项值', trigger: 'blur' }],
}

// Watch for item changes to populate form
watch(
  () => props.item,
  (newItem) => {
    if (newItem && props.mode === 'edit') {
      Object.assign(form, newItem)
    } else {
      Object.assign(form, initialFormState)
      // Reset validation state when switching to create mode or clearing form
      formRef.value?.resetFields()
    }
  },
  { immediate: true }
)

// Methods
const handleCancel = () => {
  emit('cancel')
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (valid) {
      emit('submit', { ...form })
    }
  } catch (error) {
    ElMessage.error('表单验证失败，请检查输入')
  }
}
</script>

<style scoped>
.dictionary-item-form {
  padding: 20px 20px 0 20px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  padding: 20px 0;
}
</style>