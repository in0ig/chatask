<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="100px"
    class="dictionary-form"
    :disabled="loading"
  >
    <el-form-item label="字典名称" prop="name">
      <el-input v-model="form.name" placeholder="请输入字典名称" />
    </el-form-item>

    <el-form-item label="字典编码" prop="code">
      <el-input v-model="form.code" placeholder="请输入字典编码" />
    </el-form-item>

    <el-form-item label="父级字典" prop="parentId">
      <el-tree-select
        v-model="form.parentId"
        :data="parentOptions"
        :props="{ value: 'id', label: 'name', children: 'children' }"
        check-strictly
        clearable
        filterable
        placeholder="请选择父级字典"
        style="width: 100%"
      />
    </el-form-item>

    <el-form-item label="状态" prop="status">
      <el-radio-group v-model="form.status">
        <el-radio value="ENABLED">启用</el-radio>
        <el-radio value="DISABLED">禁用</el-radio>
      </el-radio-group>
    </el-form-item>

    <el-form-item label="描述" prop="description">
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="3"
        placeholder="请输入描述信息"
      />
    </el-form-item>

    <div class="form-footer">
      <el-button @click="handleCancel" :disabled="loading">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        {{ mode === 'create' ? '立即创建' : '保存更新' }}
      </el-button>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, watch, computed, reactive, nextTick } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { Dictionary } from '@/types/dataPreparation'
import { listToTree } from '@/utils/tree'

// Props
interface Props {
  mode: 'create' | 'edit'
  dictionary?: Dictionary | null
  dictionaries: Dictionary[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'create',
  dictionary: null,
  loading: false,
})

// Emits
const emit = defineEmits<{
  submit: [formData: Partial<Dictionary>]
  cancel: []
}>()

// 表单引用
const formRef = ref<FormInstance>()

// 表单数据
const form = reactive({
  id: '',
  name: '',
  code: '',
  parentId: null as string | null,
  status: 'ENABLED' as 'ENABLED' | 'DISABLED',
  description: '',
})

// 表单验证规则
const rules = reactive<FormRules>({
  name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入字典编码', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
})

// 父级字典选项
const parentOptions = computed(() => {
  // 在编辑模式下，过滤掉当前字典及其所有子孙字典
  let availableDicts = props.dictionaries
  if (props.mode === 'edit' && props.dictionary) {
    const descendantIds = new Set<string>()
    const findDescendants = (dictId: string) => {
      descendantIds.add(dictId)
      props.dictionaries
        .filter(d => d.parent_id === dictId) // 修复：使用 parent_id
        .forEach(child => findDescendants(child.id))
    }
    findDescendants(props.dictionary.id)
    availableDicts = props.dictionaries.filter(d => !descendantIds.has(d.id))
  }
  
  return listToTree(availableDicts, { id: 'id', parentId: 'parent_id' }) // 修复：使用 parent_id
})


// 监听 props.dictionary 的变化来更新表单
watch(
  () => props.dictionary,
  (newDict) => {
    // 使用 nextTick 确保表单已重置
    nextTick(() => {
      if (newDict && props.mode === 'edit') {
        form.id = newDict.id
        form.name = newDict.name
        form.code = newDict.code
        form.parentId = newDict.parent_id || null // 修复：使用 parent_id
        form.status = newDict.status ? 'ENABLED' : 'DISABLED' // 修复：从 boolean 转换为字符串
        form.description = newDict.description || ''
      } else {
        // 重置表单
        form.id = ''
        form.name = ''
        form.code = ''
        form.parentId = null
        form.status = 'ENABLED'
        form.description = ''
      }
      // 清除之前的验证状态
      formRef.value?.clearValidate()
    })
  },
  { immediate: true, deep: true }
)

// 方法
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
      const formData: Partial<Dictionary> = {
        name: form.name,
        code: form.code,
        parent_id: form.parentId, // 修复：使用 parent_id 而不是 parentId
        status: form.status === 'ENABLED', // 修复：转换为 boolean
        description: form.description,
        created_by: 'system', // 修复：添加必需的 created_by 字段
      }
      if (props.mode === 'edit') {
        formData.id = form.id
      }
      emit('submit', formData)
    }
  })
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped>
.dictionary-form {
  padding: 20px 30px 0 10px;
}

.form-footer {
  text-align: right;
  padding-top: 20px;
}
</style>