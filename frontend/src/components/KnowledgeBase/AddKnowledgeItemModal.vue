<template>
  <el-dialog
    :title="$t('knowledgeBase.item.addTitle')"
    v-model="dialogVisible"
    width="600px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item :label="$t('knowledgeBase.item.nameLabel')" prop="name" v-if="props.knowledgeBaseType === 'TERM'">
        <el-input v-model="form.name" :placeholder="$t('knowledgeBase.item.namePlaceholder')" maxlength="200" show-word-limit />
      </el-form-item>

      <el-form-item :label="$t('knowledgeBase.item.dateLabel')" prop="dateRange" v-if="props.knowledgeBaseType === 'EVENT'">
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
      
      <el-form-item :label="$t('knowledgeBase.item.exampleLabel')" prop="exampleQuestion" v-if="props.knowledgeBaseType !== 'EVENT'">
        <el-input v-model="form.exampleQuestion" type="textarea" :rows="3" :placeholder="getExamplePlaceholder()" maxlength="200" show-word-limit />
      </el-form-item>
    </el-form>

    <div class="dialog-footer">
      <el-button @click="handleClose">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('common.confirm') }}</el-button>
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
  knowledgeBaseId: {
    type: [Number, String],
    required: true
  },
  knowledgeBaseType: {
    type: String,
    required: true,
    validator: (value) => ['TERM', 'LOGIC', 'EVENT'].includes(value)
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const form = reactive({
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

const getExplanationPlaceholder = () => {
  switch (props.knowledgeBaseType) {
    case 'TERM': return t('knowledgeBase.item.termExplanationPlaceholder')
    case 'LOGIC': return t('knowledgeBase.item.logicExplanationPlaceholder')
    case 'EVENT': return t('knowledgeBase.item.eventExplanationPlaceholder')
    default: return t('knowledgeBase.item.explanationLabel')
  }
}

const getExamplePlaceholder = () => {
  switch (props.knowledgeBaseType) {
    case 'TERM': return t('knowledgeBase.item.termExamplePlaceholder')
    case 'LOGIC': return t('knowledgeBase.item.logicExamplePlaceholder')
    default: return t('knowledgeBase.item.exampleLabel')
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    form.name = ''
    form.explanation = ''
    form.exampleQuestion = ''
    form.dateRange = null
  }
})

const handleClose = () => {
  emit('update:visible', false)
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      // 构建符合后端 API 的数据格式（使用 snake_case）
      const newItem = {
        knowledge_base_id: props.knowledgeBaseId.toString(),
        type: props.knowledgeBaseType,
        name: props.knowledgeBaseType === 'TERM' ? form.name : null,
        explanation: form.explanation,
        example_question: props.knowledgeBaseType !== 'EVENT' ? (form.exampleQuestion || null) : null,
        event_date_start: props.knowledgeBaseType === 'EVENT' && form.dateRange ? form.dateRange[0] : null,
        event_date_end: props.knowledgeBaseType === 'EVENT' && form.dateRange ? form.dateRange[1] : null
      }
      
      emit('submit', newItem)
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
