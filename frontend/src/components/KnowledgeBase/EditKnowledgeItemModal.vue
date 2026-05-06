<template>
  <el-dialog
    :title="$t('knowledgeBase.item.editTitle')"
    v-model="dialogVisible"
    width="600px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item :label="$t('knowledgeBase.item.typeLabel')">
        <el-tag>{{ getTypeLabel(form.type) }}</el-tag>
      </el-form-item>

      <el-form-item :label="$t('knowledgeBase.item.nameLabel')" prop="name" v-if="form.type === 'TERM'">
        <el-input v-model="form.name" :placeholder="$t('knowledgeBase.item.namePlaceholder')" maxlength="200" show-word-limit />
      </el-form-item>

      <el-form-item :label="$t('knowledgeBase.item.dateLabel')" prop="dateRange" v-if="form.type === 'EVENT'">
        <el-date-picker
          v-model="form.dateRange"
          type="daterange"
          :range-separator="$t('knowledgeBase.item.to')"
          :start-placeholder="$t('knowledgeBase.item.dateLabel')"
          :end-placeholder="$t('knowledgeBase.item.dateLabel')"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
      </el-form-item>
      
      <el-form-item :label="$t('knowledgeBase.item.explanationLabel')" prop="explanation">
        <el-input v-model="form.explanation" type="textarea" :rows="6" :placeholder="getExplanationPlaceholder()" maxlength="1500" show-word-limit />
      </el-form-item>
      
      <el-form-item :label="$t('knowledgeBase.item.exampleLabel')" prop="exampleQuestion" v-if="form.type !== 'EVENT'">
        <el-input v-model="form.exampleQuestion" type="textarea" :rows="3" :placeholder="getExamplePlaceholder()" maxlength="200" show-word-limit />
      </el-form-item>
    </el-form>

    <div class="dialog-footer">
      <el-button @click="handleClose">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('common.save') }}</el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  knowledgeItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const form = reactive({
  type: 'TERM',
  name: '',
  explanation: '',
  exampleQuestion: '',
  dateRange: null
})

const rules = reactive({
  name: [{ required: true, message: () => t('knowledgeBase.item.nameRequired'), trigger: 'blur' }],
  explanation: [{ required: true, message: () => t('knowledgeBase.item.explanationRequired'), trigger: 'blur' }]
})

const formRef = ref(null)

const getTypeLabel = (type) => {
  const map = {
    'TERM': t('knowledgeBase.typeTerm'),
    'LOGIC': t('knowledgeBase.typeLogic'),
    'EVENT': t('knowledgeBase.typeEvent'),
  }
  return map[type] || t('knowledgeBase.typeUnknown')
}

const getExplanationPlaceholder = () => {
  switch (form.type) {
    case 'TERM': return t('knowledgeBase.item.termExplanationPlaceholder')
    case 'LOGIC': return t('knowledgeBase.item.logicExplanationPlaceholder')
    case 'EVENT': return t('knowledgeBase.item.eventExplanationPlaceholder')
    default: return t('knowledgeBase.item.explanationLabel')
  }
}

const getExamplePlaceholder = () => {
  switch (form.type) {
    case 'TERM': return t('knowledgeBase.item.termExamplePlaceholder')
    case 'LOGIC': return t('knowledgeBase.item.logicExamplePlaceholder')
    default: return t('knowledgeBase.item.exampleLabel')
  }
}

const initForm = () => {
  if (props.knowledgeItem) {
    form.type = props.knowledgeItem.type
    form.name = props.knowledgeItem.name || ''
    form.explanation = props.knowledgeItem.explanation || ''
    form.exampleQuestion = props.knowledgeItem.example_question || ''
    
    // 将后端的 event_date_start 和 event_date_end 转换为前端的 dateRange
    if (props.knowledgeItem.event_date_start && props.knowledgeItem.event_date_end) {
      form.dateRange = [
        props.knowledgeItem.event_date_start,
        props.knowledgeItem.event_date_end
      ]
    } else {
      form.dateRange = null
    }
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    initForm()
  }
})

watch(() => props.knowledgeItem, () => {
  if (props.visible) {
    initForm()
  }
})

const handleClose = () => {
  emit('update:visible', false)
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      // 构建符合后端 API 的数据格式（使用 snake_case）
      const updatedItem = {
        id: props.knowledgeItem.id,
        knowledge_base_id: props.knowledgeItem.knowledge_base_id,
        type: form.type,
        name: form.type === 'TERM' ? form.name : null,
        explanation: form.explanation,
        example_question: form.type !== 'EVENT' ? (form.exampleQuestion || null) : null,
        event_date_start: form.type === 'EVENT' && form.dateRange ? form.dateRange[0] : null,
        event_date_end: form.type === 'EVENT' && form.dateRange ? form.dateRange[1] : null
      }
      
      emit('submit', updatedItem)
      emit('update:visible', false)
    } else {
      console.log('表单验证失败')
      return false
    }
  })
}
</script>

<style scoped>
.el-form-item {
  margin-bottom: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}
</style>
