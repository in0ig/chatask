<template>
  <div class="prompt-management">
    <el-card class="prompt-management-card">
      <template #header>
        <div class="card-header">
          <span class="title">Prompt 管理</span>
          <el-button type="primary" @click="showCreateDialog">新建 Prompt</el-button>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-section">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-input
              v-model="searchQuery"
              placeholder="搜索 Prompt 名称或类型..."
              prefix-icon="Search"
              clearable
              @input="handleSearch"
            />
          </el-col>
          <el-col :span="8">
            <el-select
              v-model="filterType"
              placeholder="按类型筛选"
              clearable
              @change="handleFilter"
            >
              <el-option
                v-for="type in promptTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-select
              v-model="filterStatus"
              placeholder="按状态筛选"
              clearable
              @change="handleFilter"
            >
              <el-option label="启用" value="true" />
              <el-option label="禁用" value="false" />
            </el-select>
          </el-col>
        </el-row>
      </div>

      <!-- Prompt 列表 -->
      <el-table
        :data="filteredPrompts"
        style="width: 100%"
        v-loading="loading"
        row-key="id"
      >
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="type" label="类型" width="150">
          <template #default="{ row }">
            {{ getPromptTypeName(row?.type || '') }}
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="150" />
        <el-table-column prop="enabled" label="启用状态" width="120">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="togglePromptStatus(row)"
              :active-text="row.enabled ? '启用' : ''"
              :inactive-text="row.enabled ? '' : '禁用'"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="editPrompt(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deletePrompt(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 创建/编辑 Prompt 对话框 -->
      <el-dialog
        v-model="dialogVisible"
        :title="isEditing ? '编辑 Prompt' : '创建 Prompt'"
        width="60%"
        :before-close="closeDialog"
      >
        <el-form
          :model="currentPrompt"
          :rules="formRules"
          ref="promptFormRef"
          label-width="120px"
          v-loading="dialogLoading"
        >
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="名称" prop="name">
                <el-input v-model="currentPrompt.name" placeholder="请输入 Prompt 名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Prompt 类型" prop="type">
                <el-select
                  v-model="currentPrompt.type"
                  placeholder="请选择 Prompt 类型"
                  :disabled="isEditing"
                >
                  <el-option
                    v-for="type in promptTypes"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="分类" prop="category">
                <el-input v-model="currentPrompt.category" placeholder="请输入分类" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="系统 Prompt" prop="systemPrompt">
            <el-input
              v-model="currentPrompt.systemPrompt"
              type="textarea"
              :rows="4"
              placeholder="请输入系统 Prompt"
            />
          </el-form-item>

          <el-form-item label="用户 Prompt 模板" prop="userPromptTemplate">
            <el-input
              v-model="currentPrompt.userPromptTemplate"
              type="textarea"
              :rows="4"
              placeholder="请输入用户 Prompt 模板"
            />
          </el-form-item>

          <el-form-item label="示例" prop="examples">
            <el-input
              v-model="currentPrompt.examples"
              type="textarea"
              :rows="6"
              placeholder="请输入 JSON 格式的示例数据"
            />
          </el-form-item>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="温度系数" prop="temperature">
                <el-slider
                  v-model="currentPrompt.temperature"
                  :min="0.1"
                  :max="0.7"
                  :step="0.01"
                  show-input
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="最大 Token 数" prop="maxTokens">
                <el-input-number
                  v-model="currentPrompt.maxTokens"
                  :min="1"
                  :max="4096"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="启用状态" prop="enabled">
            <el-switch
              v-model="currentPrompt.enabled"
              active-text="启用"
              inactive-text="禁用"
            />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="closeDialog">取消</el-button>
            <el-button type="primary" @click="submitForm">确定</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';

// Prompt 类型定义
const promptTypes = [
  { value: 'query_generation', label: '查询生成' },
  { value: 'chart_generation', label: '图表生成' },
  { value: 'data_analysis', label: '数据分析' },
  { value: 'natural_language', label: '自然语言处理' },
  { value: 'report_generation', label: '报告生成' },
];

interface Prompt {
  id: string;
  name: string;  // 修复：添加了缺失的 name 字段
  type: string;
  category?: string;
  systemPrompt: string;
  userPromptTemplate: string;
  examples: string;
  temperature: number;
  maxTokens: number;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

// 响应式数据
const prompts = ref<Prompt[]>([]);
const filteredPrompts = ref<Prompt[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const dialogLoading = ref(false);
const isEditing = ref(false);
const searchQuery = ref('');
const filterType = ref('');
const filterStatus = ref('');

const currentPrompt = reactive({
  id: '',
  name: '',  // 修复：添加了缺失的 name 字段
  type: '',
  category: '',
  systemPrompt: '',
  userPromptTemplate: '',
  examples: '',
  temperature: 0.3,
  maxTokens: 1024,
  enabled: true,
});

const promptFormRef = ref<FormInstance>();

// 表单验证规则
const formRules: FormRules = {
  type: [
    { required: true, message: '请选择 Prompt 类型', trigger: 'change' }
  ],
  name: [  // 修复：添加了 name 字段的验证规则
    { required: true, message: '请输入 Prompt 名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  systemPrompt: [
    { required: true, message: '请输入系统 Prompt', trigger: 'blur' }
  ],
  userPromptTemplate: [
    { required: true, message: '请输入用户 Prompt 模板', trigger: 'blur' }
  ],
  temperature: [
    { required: true, message: '请输入温度系数', trigger: 'blur' },
    { type: 'number', min: 0.1, max: 0.7, message: '温度系数应在 0.1-0.7 之间', trigger: 'blur' }
  ],
  maxTokens: [
    { required: true, message: '请输入最大 Token 数', trigger: 'blur' },
    { type: 'number', min: 1, max: 4096, message: '最大 Token 数应在 1-4096 之间', trigger: 'blur' }
  ],
  enabled: [
    { required: true, message: '请选择启用状态', trigger: 'change' }
  ]
};

// 获取 Prompt 类型名称
const getPromptTypeName = (type: string) => {
  const found = promptTypes.find(item => item.value === type);
  return found ? found.label : type;
};

// 获取 Prompt 列表
const fetchPrompts = async () => {
  loading.value = true;
  try {
    // 模拟数据
    prompts.value = [
      {
        id: '1',
        name: '查询生成 Prompt',  // 修复：添加了缺失的 name 字段
        type: 'query_generation',
        category: 'SQL',
        systemPrompt: '你是一个专业的 SQL 查询生成助手...',
        userPromptTemplate: '根据以下需求生成 SQL 查询: {query}',
        examples: JSON.stringify([
          {
            input: '查询销售额最高的产品',
            output: 'SELECT product_name FROM products ORDER BY sales DESC LIMIT 1'
          }
        ], null, 2),
        temperature: 0.3,
        maxTokens: 1024,
        enabled: true,
        createdAt: '2023-01-01',
        updatedAt: '2023-01-01'
      },
      {
        id: '2',
        name: '图表生成 Prompt',  // 修复：添加了缺失的 name 字段
        type: 'chart_generation',
        category: 'Visualization',
        systemPrompt: '你是一个专业的图表生成助手...',
        userPromptTemplate: '根据以下数据生成合适的图表: {data}',
        examples: JSON.stringify([
          {
            input: '销售数据',
            output: '柱状图展示各月份销售额'
          }
        ], null, 2),
        temperature: 0.4,
        maxTokens: 2048,
        enabled: true,
        createdAt: '2023-01-02',
        updatedAt: '2023-01-02'
      }
    ];
    
    filteredPrompts.value = [...prompts.value];
  } catch (error) {
    console.error('获取 Prompt 列表失败:', error);
    ElMessage.error('获取 Prompt 列表失败');
  } finally {
    loading.value = false;
  }
};

// 显示创建对话框
const showCreateDialog = () => {
  resetForm();
  isEditing.value = false;
  dialogVisible.value = true;
};

// 编辑 Prompt
const editPrompt = (prompt: Prompt) => {
  Object.assign(currentPrompt, prompt);
  isEditing.value = true;
  dialogVisible.value = true;
};

// 删除 Prompt
const deletePrompt = async (prompt: Prompt) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 Prompt "${prompt.name}" 吗？`,  // 修复：现在 name 字段存在
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    // 模拟删除
    prompts.value = prompts.value.filter(p => p.id !== prompt.id);
    filteredPrompts.value = filteredPrompts.value.filter(p => p.id !== prompt.id);
    
    ElMessage.success('删除成功');
  } catch (error) {
    console.error('删除 Prompt 失败:', error);
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};

// 切换 Prompt 状态
const togglePromptStatus = async (prompt: Prompt) => {
  try {
    // 模拟更新
    prompt.enabled = !prompt.enabled;
    ElMessage.success(prompt.enabled ? '启用成功' : '禁用成功');
  } catch (error) {
    console.error('更新 Prompt 状态失败:', error);
    ElMessage.error('更新状态失败');
    // 如果失败，恢复原状态
    prompt.enabled = !prompt.enabled;
  }
};

// 提交表单
const submitForm = async () => {
  if (!promptFormRef.value) return;
  
  const valid = await promptFormRef.value.validate().catch(() => false);
  if (!valid) return;
  
  dialogLoading.value = true;
  try {
    if (isEditing.value) {
      // 更新 Prompt
      // 模拟更新
      const index = prompts.value.findIndex(p => p.id === currentPrompt.id);
      if (index !== -1) {
        prompts.value[index] = { ...currentPrompt };
      }
      ElMessage.success('更新成功');
    } else {
      // 创建 Prompt
      // 模拟创建
      const newPrompt = {
        ...currentPrompt,
        id: Date.now().toString(),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      prompts.value.push(newPrompt);
      filteredPrompts.value.push(newPrompt);
      ElMessage.success('创建成功');
    }
    
    closeDialog();
  } catch (error) {
    console.error(isEditing.value ? '更新 Prompt 失败:' : '创建 Prompt 失败:', error);
    ElMessage.error(isEditing.value ? '更新失败' : '创建失败');
  } finally {
    dialogLoading.value = false;
  }
};

// 关闭对话框
const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

// 重置表单
const resetForm = () => {
  Object.assign(currentPrompt, {
    id: '',
    name: '',  // 修复：重置 name 字段
    type: '',
    category: '',
    systemPrompt: '',
    userPromptTemplate: '',
    examples: '',
    temperature: 0.3,
    maxTokens: 1024,
    enabled: true,
  });
  
  if (promptFormRef.value) {
    promptFormRef.value.clearValidate();
  }
};

// 处理搜索
const handleSearch = () => {
  filterPrompts();
};

// 处理筛选
const handleFilter = () => {
  filterPrompts();
};

// 过滤 Prompt 列表
const filterPrompts = () => {
  filteredPrompts.value = prompts.value.filter(prompt => {
    const matchesSearch = !searchQuery.value || 
      prompt.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      prompt.type.toLowerCase().includes(searchQuery.value.toLowerCase());
    
    const matchesType = !filterType.value || prompt.type === filterType.value;
    const matchesStatus = !filterStatus.value || prompt.enabled.toString() === filterStatus.value;
    
    return matchesSearch && matchesType && matchesStatus;
  });
};

onMounted(() => {
  fetchPrompts();
});
</script>

<style scoped>
.prompt-management {
  padding: 20px;
}

.prompt-management-card {
  min-height: 500px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: bold;
}

.filter-section {
  margin-bottom: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>