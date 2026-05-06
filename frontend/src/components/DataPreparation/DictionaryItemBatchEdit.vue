<template>
  <div class="batch-edit-form">
    <p class="summary-text">
      已选择 <strong>{{ items.length }}</strong> 个字典项进行批量编辑。
    </p>
    <el-form ref="formRef" :model="form" label-width="120px">
      <el-form-item label="统一设置状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio-button label="ENABLED">启用</el-radio-button>
          <el-radio-button label="DISABLED">禁用</el-radio-button>
        </el-radio-group>
      </el-form-item>
       <!-- You can add more fields for batch editing here in the future -->
    </el-form>
    <div class="form-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        应用修改
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import type { DictionaryItem } from '@/store/modules/dataPreparation'

interface Props {
  items: DictionaryItem[]
  loading?: boolean
}
defineProps<Props>()

const emit = defineEmits<{
  (e: 'submit', data: { status: 'ENABLED' | 'DISABLED' }): void
  (e: 'cancel'): void
}>()

const form = reactive({
  status: 'ENABLED' as 'ENABLED' | 'DISABLED',
})

const handleSubmit = () => {
  emit('submit', { status: form.status })
}
</script>

<style scoped>
.batch-edit-form {
  padding: 20px 20px 0 20px;
}
.summary-text {
  margin-bottom: 20px;
  color: #606266;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
}
</style>