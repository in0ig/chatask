<template>
  <el-dialog
    v-model="visible"
    :title="'创建知识库'
    width="600px"
    class="create-kb-dialog"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      class="kb-form"
    >
      <!-- 知识库名称 -->
      <el-form-item
        label="知识库名称"
        prop="name"
      >
        <el-input
          v-model="form.name"
          placeholder="请输入知识库名称"
          clearable
        />
      </el-form-item>

      <!-- 知识库类型 -->
      <el-form-item
        label="知识库类型"
        prop="type"
      >
        <el-radio-group v-model="form.type">
          <el-radio
            label="noun"
            class="radio-option"
          >
            <span class="radio-label">名词</span>
            <span class="radio-tip">录入毛利润等业务常用的专有名词和解释</span>
          </el-radio>
          <el-radio
            label="text"
            class="radio-option"
          >
            <span class="radio-label">文本</span>
            <span class="radio-tip">录入默认时间等业务逻辑知识。业务逻辑知识过多会影响问答效果，每张数据表的业务逻辑条数推荐不要超过30条</span>
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 语言选择 -->
      <el-form-item
        label="语言"
        prop="language"
      >
        <el-radio-group v-model="form.language">
          <el-radio
            label="zh"
            class="radio-option"
          >
            <span class="radio-label">中文</span>
          </el-radio>
          <el-radio
            label="en"
            class="radio-option"
          >
            <span class="radio-label">英文</span>
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 关联数据表 -->
      <el-form-item
        label="关联数据表"
        prop="associatedTables"
      >
        <el-select
          v-model="form.associatedTables"
          multiple
          placeholder="请选择关联的数据表"
          class="select-multiple"
        >
          <el-option
            v-for="table in availableTables"
            :key="table.value"
            :label="table.label"
            :value="table.value"
          />
        </el-select>
      </el-form-item>

      <!-- 生效范围 -->
      <el-form-item
        label="生效范围"
        prop="scope"
      >
        <el-checkbox-group v-model="form.scope">
          <el-checkbox
            label="名词知识库"
            class="checkbox-item"
          >
            名词知识库
          </el-checkbox>
          <el-checkbox
            label="业务逻辑知识库"
            class="checkbox-item"
          >
            业务逻辑知识库
          </el-checkbox>
          <el-checkbox
            label="数据解读"
            class="checkbox-item"
          >
            数据解读
          </el-checkbox>
          <el-checkbox
            label="数据填报"
            class="checkbox-item"
          >
            数据填报
          </el-checkbox>
          <el-checkbox
            label="波动归因"
            class="checkbox-item"
          >
            波动归因
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <!-- 提示信息 -->
      <el-form-item class="tip-item">
        <el-alert
          title="事件知识库说明"
          type="info"
          show-icon
          :closable="false"
          class="info-alert"
        >
          <template #description>
            <p>事件知识库：录入某个时间发生的事件，大模型会应用事件知识解读和归因数据。事件知识仅在波动归因模块生效。知识过多会影响问答效果，每张数据表的知识条数推荐不要超过30条。</p>
          </template>
        </el-alert>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, defineEmits, defineProps } from 'vue';

// 定义props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
});

// 定义emits
const emit = defineEmits(['update:visible', 'close', 'create']);

// 表单数据
const form = ref({
  name: '',
  type: 'noun', // 默认为名词
  language: 'zh', // 默认为中文
  associatedTables: [],
  scope: []
});

// 表单验证规则
const rules = ref({
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择知识库类型', trigger: 'change' }
  ],
  language: [
    { required: true, message: '请选择语言', trigger: 'change' }
  ],
  associatedTables: [
    { required: true, message: '请选择至少一个关联数据表', trigger: 'change' }
  ],
  scope: [
    { required: true, message: '请选择至少一个生效范围', trigger: 'change' }
  ]
});

// 可用数据表（模拟数据）
const availableTables = ref([
  { value: 'sales', label: '销售数据' },
  { value: 'finance', label: '财务数据' },
  { value: 'inventory', label: '库存数据' },
  { value: 'customer', label: '客户数据' },
  { value: 'product', label: '产品数据' },
  { value: 'marketing', label: '营销数据' }
]);

// 表单引用
const formRef = ref(null);

// 关闭对话框
const handleClose = () => {
  emit('update:visible', false);
  emit('close');
};

// 提交表单
const handleSubmit = async () => {
  // 验证表单
  const isValid = await formRef.value.validate().catch(() => {});
  if (!isValid) return;

  // 发出创建事件
  emit('create', { ...form.value });

  // 重置表单并关闭
  form.value = {
    name: '',
    type: 'noun',
    language: 'zh',
    associatedTables: [],
    scope: []
  };
  handleClose();
};

// 监听visible变化
const updateVisible = (val) => {
  if (!val) {
    // 重置表单验证
    formRef.value?.resetFields();
  }
};

// 绑定监听
watch(props.visible, updateVisible);
</script>

<style scoped>
.create-kb-dialog {
  --el-dialog-padding-primary: 20px;
}

.kb-form {
  padding: 0 20px;
}

.radio-option {
  display: block;
  margin-bottom: 12px;
}

.radio-label {
  font-weight: 500;
  color: #303133;
}

.radio-tip {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #606266;
}

.select-multiple {
  width: 100%;
}

.checkbox-item {
  display: block;
  margin-bottom: 8px;
}

.tip-item {
  margin-top: 20px;
}

.info-alert {
  border: 1px solid #e6f7ff;
  border-radius: 8px;
  background-color: #f0f7ff;
}

.info-alert .el-alert__description {
  margin-top: 8px;
}
</style>