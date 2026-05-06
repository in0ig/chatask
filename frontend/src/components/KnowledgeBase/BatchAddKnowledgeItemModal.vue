<template>
  <el-dialog
    :title="$t('knowledgeBase.item.batchTitle')"
    v-model="dialogVisible"
    width="800px"
    @close="handleClose"
  >
    <el-alert
      :title="$t('knowledgeBase.item.batchFormatTitle')"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <div v-if="props.knowledgeBaseType === 'TERM'">
        <p><strong>{{ $t('knowledgeBase.item.batchTermFormat') }}</strong></p>
        <p>{{ $t('knowledgeBase.item.batchTermDesc') }}</p>
        <p>{{ $t('knowledgeBase.item.batchTermExample') }}</p>
        <p>{{ $t('knowledgeBase.item.batchTermSample') }}</p>
        <p class="text-muted">{{ $t('knowledgeBase.item.batchOptional') }}</p>
      </div>
      <div v-else-if="props.knowledgeBaseType === 'LOGIC'">
        <p><strong>{{ $t('knowledgeBase.item.batchLogicFormat') }}</strong></p>
        <p>{{ $t('knowledgeBase.item.batchTermDesc') }}</p>
        <p>{{ $t('knowledgeBase.item.batchLogicExample') }}</p>
        <p>{{ $t('knowledgeBase.item.batchLogicSample') }}</p>
        <p class="text-muted">{{ $t('knowledgeBase.item.batchOptional') }}</p>
      </div>
      <div v-else-if="props.knowledgeBaseType === 'EVENT'">
        <p><strong>{{ $t('knowledgeBase.item.batchEventFormat') }}</strong></p>
        <p>{{ $t('knowledgeBase.item.batchTermDesc') }}</p>
        <p>{{ $t('knowledgeBase.item.batchEventExample') }}</p>
        <p>{{ $t('knowledgeBase.item.batchEventSample') }}</p>
        <p class="text-muted">{{ $t('knowledgeBase.item.batchDateHint') }}</p>
      </div>
    </el-alert>

    <el-form ref="formRef" :model="form" class="batch-form">
      <el-form-item>
        <el-input v-model="form.textData" type="textarea" :rows="12" :placeholder="getPlaceholder()" />
      </el-form-item>
    </el-form>
    
    <div class="dialog-footer">
      <el-button @click="handleClose">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        {{ $t('knowledgeBase.item.batchAddBtn') }}
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const { t } = useI18n()

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  knowledgeBaseId: {
    type: [Number, String],
    required: true
  },
  knowledgeBaseType: {
    type: String,
    required: true,
    validator: (value) => ['TERM', 'LOGIC', 'EVENT'].includes(value)
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const form = reactive({
  textData: '',
})

const formRef = ref(null)

const getPlaceholder = () => {
  switch (props.knowledgeBaseType) {
    case 'TERM': return t('knowledgeBase.item.batchTermPlaceholder')
    case 'LOGIC': return t('knowledgeBase.item.batchLogicPlaceholder')
    case 'EVENT': return t('knowledgeBase.item.batchEventPlaceholder')
    default: return ''
  }
}

const handleClose = () => {
  form.textData = ''
  emit('update:visible', false)
}

const parseTerm = (line, index) => {
  const parts = line.split(',')
  const name = parts[0]?.trim()
  const explanation = parts[1]?.trim()
  const exampleQuestion = parts.slice(2).join(',').trim() || null
  if (!name || !explanation) {
    throw new Error(t('knowledgeBase.item.batchTermError', { line: index + 1 }))
  }
  return { knowledge_base_id: props.knowledgeBaseId.toString(), type: 'TERM', name, explanation, example_question: exampleQuestion, event_date_start: null, event_date_end: null }
}

const parseLogic = (line, index) => {
  const parts = line.split(',')
  const explanation = parts[0]?.trim()
  const exampleQuestion = parts.slice(1).join(',').trim() || null
  if (!explanation) {
    throw new Error(t('knowledgeBase.item.batchLogicError', { line: index + 1 }))
  }
  return { knowledge_base_id: props.knowledgeBaseId.toString(), type: 'LOGIC', name: null, explanation, example_question: exampleQuestion, event_date_start: null, event_date_end: null }
}

const parseEvent = (line, index) => {
  const parts = line.split(',')
  const startDate = parts[0]?.trim()
  const endDate = parts[1]?.trim()
  const explanation = parts.slice(2).join(',').trim()
  if (!startDate || !endDate || !explanation) {
    throw new Error(t('knowledgeBase.item.batchEventError', { line: index + 1 }))
  }
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/
  if (!dateRegex.test(startDate) || !dateRegex.test(endDate)) {
    throw new Error(t('knowledgeBase.item.batchDateError', { line: index + 1 }))
  }
  return { knowledge_base_id: props.knowledgeBaseId.toString(), type: 'EVENT', name: null, explanation, example_question: null, event_date_start: startDate, event_date_end: endDate }
}

const handleSubmit = () => {
  const lines = form.textData.split('\n').filter(line => line.trim() !== '')
  if (lines.length === 0) {
    ElMessage.warning(t('knowledgeBase.item.batchEmptyWarning'))
    return
  }
  try {
    const items = lines.map((line, index) => {
      switch (props.knowledgeBaseType) {
        case 'TERM': return parseTerm(line, index)
        case 'LOGIC': return parseLogic(line, index)
        case 'EVENT': return parseEvent(line, index)
        default: throw new Error(t('knowledgeBase.typeUnknown'))
      }
    })
    emit('submit', items)
  } catch (error) {
    ElMessage.error(error.message || t('knowledgeBase.item.batchParseError'))
  }
}
</script>

<style scoped>
.batch-form {
  margin-top: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.mb-4 {
  margin-bottom: 16px;
}

.text-muted {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.el-alert__description) {
  font-size: 13px;
  line-height: 1.6;
}

:deep(.el-alert__description) p {
  margin: 4px 0;
}

:deep(.el-alert__description) code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  color: #e6a23c;
}
</style>
