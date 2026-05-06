<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="100px"
    class="data-table-form"
    @submit.prevent="handleSave"
  >
    <!-- 数据源选择 -->
    <el-form-item
      label="数据源"
      prop="sourceId"
    >
      <el-select
        v-model="form.sourceId"
        placeholder="请选择数据源"
        @change="handleDataSourceChange"
        :disabled="dataSourceLoading"
        style="width: 100%"
      >
        <el-option
          v-for="source in dataSources"
          :key="source.id"
          :label="source.name"
          :value="source.id"
          :disabled="!source.is_active"
        />
      </el-select>
    </el-form-item>

    <!-- 表选择 -->
    <el-form-item
      label="表名"
      prop="tableName"
    >
      <el-select
        v-model="form.tableName"
        placeholder="请选择数据表"
        :disabled="!form.sourceId || tableLoading"
        style="width: 100%"
      >
        <el-option
          v-for="table in availableTables"
          :key="table.table_name"
          :label="table.table_name"
          :value="table.table_name"
        />
      </el-select>
    </el-form-item>

    <!-- 显示名称 -->
    <el-form-item
      label="显示名称"
      prop="name"
    >
      <el-input
        v-model="form.name"
        placeholder="请输入数据表的中文显示名称"
        style="width: 100%"
      />
    </el-form-item>

    <!-- 描述 -->
    <el-form-item
      label="描述"
      prop="description"
    >
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="3"
        placeholder="请输入数据表的描述信息"
        style="width: 100%"
      />
    </el-form-item>

    <!-- 操作按钮 -->
    <el-form-item class="form-actions">
      <el-button
        type="primary"
        @click="handleSave"
        :loading="saving"
        :disabled="!form.sourceId || !form.tableName"
      >
        保存
      </el-button>
      <el-button @click="handleCancel">
        取消
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dataSourceApi, DataSource } from '@/api/dataSourceApi'
import { dataTableApi, DataTable } from '@/api/dataTableApi'
import { ElMessage, ElMessageBox } from 'element-plus'

// Store 实例
const dataPrepStore = useDataPreparationStore()

// 表单数据
const form = reactive({
  sourceId: '' as string | number | null,
  tableName: '' as string | null,
  name: '',
  description: ''
})

// 表单验证规则
const rules = reactive({
  sourceId: [
    { required: true, message: '请选择数据源', trigger: 'change' }
  ],
  tableName: [
    { required: true, message: '请选择数据表', trigger: 'change' }
  ],
  name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' }
  ]
})

// 加载状态
const dataSourceLoading = ref(false)
const tableLoading = ref(false)
const saving = ref(false)

// 数据源列表
const dataSources = computed(() => dataPrepStore.dataSources)

// 可用的表列表
const availableTables = computed(() => {
  if (!form.sourceId) return []
  return dataPrepStore.dataTables.filter(table => table.source_id === form.sourceId)
})

// 获取数据源列表
const fetchSources = async () => {
  dataSourceLoading.value = true
  try {
    await dataPrepStore.fetchDataSources()
  } catch (error) {
    ElMessage.error('获取数据源列表失败')
  } finally {
    dataSourceLoading.value = false
  }
}

// 当数据源改变时，加载对应的表列表
const handleDataSourceChange = async () => {
  if (!form.sourceId) {
    form.tableName = null
    return
  }
  
  tableLoading.value = true
  try {
    // 如果数据表尚未加载，则加载
    if (dataPrepStore.dataTables.length === 0 || !dataPrepStore.dataTables.some(t => t.source_id === form.sourceId)) {
      await dataPrepStore.fetchDataTables(String(form.sourceId))
    }
  } catch (error) {
    ElMessage.error('加载数据表失败')
  } finally {
    tableLoading.value = false
  }
}

// 保存表
const handleSave = async () => {
  const formEl = document.querySelector('.data-table-form')
  if (!formEl) return
  
  // 验证表单
  const isValid = await (formEl as any).validate().catch(() => false)
  if (!isValid) return
  
  saving.value = true
  try {
    // 调用 API 创建数据表
    const response = await dataTableApi.create({
      source_id: Number(form.sourceId),
      table_name: form.tableName!,
      columns: [] // 会自动同步结构，不需要手动定义列
    })
    
    // 更新 store
    dataPrepStore.dataTables.push({
      ...response,
      created_at: new Date(response.created_at).toISOString(),
      updated_at: new Date(response.updated_at).toISOString()
    })
    
    ElMessage.success('数据表添加成功')
    
    // 清空表单
    form.name = ''
    form.description = ''
    
    // 重置表单
    const formEl = document.querySelector('.data-table-form')
    if (formEl) {
      (formEl as any).resetFields()
    }
    
    // 重新加载数据源和表
    await fetchSources()
    
  } catch (error: any) {
    ElMessage.error(error.message || '添加数据表失败')
  } finally {
    saving.value = false
  }
}

// 取消操作
const handleCancel = () => {
  const formEl = document.querySelector('.data-table-form')
  if (formEl) {
    (formEl as any).resetFields()
  }
  form.name = ''
  form.description = ''
}

// 初始化
fetchSources()
</script>

<style scoped>
.data-table-form {
  max-width: 600px;
  margin: 0 auto;
}

.form-actions {
  text-align: center;
}

.el-form-item {
  margin-bottom: 20px;
}
</style>