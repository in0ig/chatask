<template>
  <div class="batch-add-form">
    <el-alert
      title="格式说明"
      type="info"
      :closable="false"
      show-icon
    >
      <p>每行代表一个字典项，请使用英文逗号 (,) 分隔项键、项值和描述。</p>
      <p>格式：<code>项键,项值,描述</code></p>
      <p>例如：<code>male,男,表示男性</code></p>
      <p>描述为可选字段。</p>
    </el-alert>

    <el-form ref="formRef" :model="form" class="mt-4">
      <el-form-item>
        <el-input
          v-model="form.textData"
          type="textarea"
          :rows="10"
          placeholder="请在此处粘贴或输入字典项数据..."
        />
      </el-form-item>
    </el-form>
    
    <div class="form-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        添加
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

interface Props {
  loading?: boolean
}
defineProps<Props>()

const emit = defineEmits<{
  (e: 'submit', items: Array<{ key: string, value: string, description?: string }>): void
  (e: 'cancel'): void
}>()

const form = reactive({
  textData: '',
})

const handleSubmit = () => {
  const lines = form.textData.split('\n').filter(line => line.trim() !== '')
  if (lines.length === 0) {
    ElMessage.warning('请输入要添加的数据')
    return
  }
  
  try {
    const items = lines.map((line, index) => {
      const parts = line.split(',')
      const key = parts[0]?.trim()
      const value = parts[1]?.trim()
      
      if (!key || !value) {
        throw new Error(`第 ${index + 1} 行数据格式错误，请确保包含项键和项值。`)
      }

      const description = parts.slice(2).join(',').trim()
      return { key, value, description }
    })
    
    emit('submit', items)

  } catch (error: any) {
    ElMessage.error(error.message || '数据解析失败，请检查格式。')
  }
}
</script>

<style scoped>
.batch-add-form {
  padding: 20px 20px 0 20px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
}
.mt-4 {
    margin-top: 16px;
}
</style>