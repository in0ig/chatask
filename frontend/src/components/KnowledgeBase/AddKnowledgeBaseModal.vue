<template>
  <el-dialog
    :title="$t('knowledgeBase.createDialog.title')"
    v-model="dialogVisible"
    width="800px"
    @close="handleClose"
  >
    <el-form
      :model="form"
      :rules="rules"
      ref="formRef"
      label-width="120px"
      class="knowledge-base-form"
    >
      <div class="form-container">
        <!-- 左侧表单区域 -->
        <div class="form-section">
          <el-form-item :label="$t('knowledgeBase.createDialog.nameLabel')" prop="name">
            <el-input v-model="form.name" :placeholder="$t('knowledgeBase.createDialog.namePlaceholder')" />
          </el-form-item>

          <el-form-item :label="$t('knowledgeBase.createDialog.typeLabel')" prop="type">
            <el-radio-group v-model="form.type" direction="horizontal">
              <el-radio value="TERM" border>{{ $t('knowledgeBase.typeTerm') }}</el-radio>
              <el-radio value="LOGIC" border>{{ $t('knowledgeBase.typeLogic') }}</el-radio>
              <el-radio value="EVENT" border>{{ $t('knowledgeBase.typeEvent') }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="$t('knowledgeBase.createDialog.scopeLabel')" prop="scope">
            <el-radio-group v-model="form.scope" direction="horizontal">
              <el-radio value="GLOBAL" border>{{ $t('knowledgeBase.createDialog.scopeGlobal') }}</el-radio>
              <el-radio value="TABLE" border>{{ $t('knowledgeBase.createDialog.scopeTable') }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="$t('knowledgeBase.createDialog.statusLabel')" prop="status">
            <el-radio-group v-model="form.status" direction="horizontal">
              <el-radio :value="true" border>{{ $t('knowledgeBase.createDialog.statusEnable') }}</el-radio>
              <el-radio :value="false" border>{{ $t('knowledgeBase.createDialog.statusDisable') }}</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item :label="$t('knowledgeBase.createDialog.relatedTableLabel')" v-if="form.scope === 'TABLE'">
            <el-select
              v-model="form.table_id"
              :placeholder="$t('knowledgeBase.createDialog.relatedTablePlaceholder')"
              style="width: 100%"
              :loading="loadingTables"
            >
              <el-option
                v-for="table in dataTables"
                :key="table.id"
                :label="table.name"
                :value="table.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item :label="$t('knowledgeBase.createDialog.descLabel')">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              :placeholder="$t('knowledgeBase.createDialog.descPlaceholder')"
            />
          </el-form-item>
        </div>

        <!-- 右侧说明区域 -->
        <div class="info-section">
          <div class="info-content">
            <p v-if="form.type === 'TERM'">{{ $t('knowledgeBase.createDialog.termHint') }}</p>
            <p v-else-if="form.type === 'LOGIC'">{{ $t('knowledgeBase.createDialog.logicHint') }}</p>
            <p v-else-if="form.type === 'EVENT'">{{ $t('knowledgeBase.createDialog.eventHint') }}</p>
            <p v-else>{{ $t('knowledgeBase.createDialog.typeHint') }}</p>
          </div>
        </div>
      </div>
    </el-form>

    <div class="dialog-footer">
      <el-button @click="handleClose">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('common.confirm') }}</el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { dataTableApi } from '@/services/dataTableApi'
import { ElMessage } from 'element-plus'

const { t } = useI18n()

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'submit'])

// 内部对话框可见性状态
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// 表单数据
const form = reactive({
  name: '',
  type: '',
  scope: 'GLOBAL',
  status: true,
  table_id: '',
  description: ''
})

// 表单验证规则
const rules = reactive({
  name: [
    { required: true, message: () => t('knowledgeBase.createDialog.nameRequired'), trigger: 'blur' }
  ],
  type: [
    { required: true, message: () => t('knowledgeBase.createDialog.typeRequired'), trigger: 'change' }
  ],
  scope: [
    { required: true, message: () => t('knowledgeBase.createDialog.scopeRequired'), trigger: 'change' }
  ]
})

// 🆕 数据表列表（从 API 加载）
const dataTables = ref([])
const loadingTables = ref(false)

// 🆕 加载数据表列表
const loadDataTables = async () => {
  try {
    loadingTables.value = true
    const tables = await dataTableApi.getAll()
    dataTables.value = tables || []
    console.log('✅ 加载数据表列表成功:', dataTables.value.length, '个表')
  } catch (error) {
    console.error('❌ 加载数据表列表失败:', error)
    ElMessage.error('加载数据表列表失败')
    dataTables.value = []
  } finally {
    loadingTables.value = false
  }
}

// 🆕 组件挂载时加载数据表列表
onMounted(() => {
  loadDataTables()
})

// 表单引用
const formRef = ref(null)

// 当生效范围为全局时，清空关联数据表
watch(() => form.scope, (newVal) => {
  if (newVal === 'GLOBAL') {
    form.table_id = ''
  }
})

// 关闭弹窗
const handleClose = () => {
  // 重置表单
  formRef.value?.resetFields()
  // 手动重置所有字段
  form.name = ''
  form.type = ''
  form.scope = 'GLOBAL'
  form.status = true
  form.table_id = ''
  form.description = ''
  
  emit('update:visible', false)
}

// 提交表单
const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      // 创建知识库对象（不包含 id，由后端生成）
      const newKnowledgeBase = {
        name: form.name,
        description: form.description || null,
        type: form.type,
        scope: form.scope,
        status: form.status,
        table_id: form.table_id || null
      }
      
      emit('submit', newKnowledgeBase)
      
      // 提交后重置表单
      formRef.value?.resetFields()
      form.name = ''
      form.type = ''
      form.scope = 'GLOBAL'
      form.status = true
      form.table_id = ''
      form.description = ''
      
      emit('update:visible', false)
    } else {
      console.log('表单验证失败')
      return false
    }
  })
}
</script>

<style scoped>
.knowledge-base-form {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-container {
  display: flex;
  height: calc(100% - 60px);
}

.form-section {
  flex: 1;
  padding-right: 30px;
  border-right: 1px solid #eee;
}

.info-section {
  width: 300px;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 4px;
  margin-left: 20px;
  overflow-y: auto;
}

.info-content {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

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
