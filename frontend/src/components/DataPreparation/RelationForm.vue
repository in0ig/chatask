<template>
  <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px" class="relation-form">
    <el-form-item label="主表" prop="mainTable">
      <el-select 
        v-model="formData.mainTable" 
        placeholder="选择主表" 
        filterable 
        @change="onMainTableChange"
        :loading="tablesLoading"
      >
        <el-option 
          v-for="table in availableTables" 
          :key="table.id" 
          :label="table.displayName" 
          :value="table.id" 
        />
      </el-select>
    </el-form-item>

    <el-form-item label="主表关联字段" prop="mainTableColumn">
      <el-select 
        v-model="formData.mainTableColumn" 
        placeholder="选择关联字段" 
        filterable
        @change="onMainColumnChange"
      >
        <el-option 
          v-for="column in mainTableColumns" 
          :key="column.id" 
          :label="`${column.displayName} (${column.dataType})`" 
          :value="column.id" 
        />
      </el-select>
    </el-form-item>

    <el-form-item label="从表" prop="relatedTable">
      <el-select 
        v-model="formData.relatedTable" 
        placeholder="选择从表" 
        filterable 
        @change="onRelatedTableChange"
        :loading="tablesLoading"
      >
        <el-option 
          v-for="table in availableTables" 
          :key="table.id" 
          :label="table.displayName" 
          :value="table.id" 
        />
      </el-select>
    </el-form-item>

    <el-form-item label="从表关联字段" prop="relatedTableColumn">
      <el-select 
        v-model="formData.relatedTableColumn" 
        placeholder="选择关联字段" 
        filterable
        @change="onRelatedColumnChange"
      >
        <el-option 
          v-for="column in relatedTableColumns" 
          :key="column.id" 
          :label="`${column.displayName} (${column.dataType})`" 
          :value="column.id" 
        />
      </el-select>
    </el-form-item>

    <!-- 字段类型匹配验证提示 -->
    <el-form-item v-if="showTypeValidation">
      <el-alert
        :title="typeValidationMessage"
        :type="typeValidationStatus"
        :closable="false"
        show-icon
      />
    </el-form-item>

    <el-form-item label="关联类型" prop="joinType">
      <el-select v-model="formData.joinType" placeholder="选择关联类型">
        <el-option label="Inner Join" value="INNER" />
        <el-option label="Left Join" value="LEFT" />
        <el-option label="Right Join" value="RIGHT" />
        <el-option label="Full Join" value="FULL" />
      </el-select>
    </el-form-item>

    <el-form-item label="描述" prop="description">
      <el-input v-model="formData.description" type="textarea" placeholder="输入关联关系的描述" />
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, computed } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import { ElForm, ElFormItem, ElInput, ElSelect, ElOption, ElAlert } from 'element-plus';
import { useDataPreparationStore } from '@/store/modules/dataPreparation';
import type { DataTable, TableField } from '@/store/modules/dataPreparation';

interface Props {
  initialData?: RelationFormData;
}

interface RelationFormData {
  mainTable: string;
  mainTableColumn: string;
  relatedTable: string;
  relatedTableColumn: string;
  joinType: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL';
  description: string;
}

const props = defineProps<Props>();
const emit = defineEmits(['update:modelValue']);

// Store 实例
const dataPreparationStore = useDataPreparationStore();

const formRef = ref<FormInstance>();
const formData = reactive<RelationFormData>({
  mainTable: '',
  mainTableColumn: '',
  relatedTable: '',
  relatedTableColumn: '',
  joinType: 'LEFT',
  description: '',
});

// 表单验证规则
const rules = reactive<FormRules>({
  mainTable: [{ required: true, message: '请选择主表', trigger: 'change' }],
  mainTableColumn: [{ required: true, message: '请选择主表关联字段', trigger: 'change' }],
  relatedTable: [
    { required: true, message: '请选择从表', trigger: 'change' },
    { 
      validator: (rule, value, callback) => {
        if (value === formData.mainTable) {
          callback(new Error('从表不能与主表相同'));
        } else {
          callback();
        }
      }, 
      trigger: 'change' 
    }
  ],
  relatedTableColumn: [{ required: true, message: '请选择从表关联字段', trigger: 'change' }],
  joinType: [{ required: true, message: '请选择关联类型', trigger: 'change' }],
});

interface NormalizedTableOption {
  id: string;
  name: string;
  displayName: string;
}

interface NormalizedFieldOption {
  id: string;
  name: string;
  displayName: string;
  dataType: string;
}

// 计算属性：兼容后端字段命名（name/table_name）
const availableTables = computed<NormalizedTableOption[]>(() => {
  const tables = (dataPreparationStore.dataTables || []) as DataTable[];
  return tables.map((t: any) => ({
    id: String(t.id),
    name: t.table_name || t.name || '',
    displayName: t.table_name || t.name || `Table ${t.id}`,
  }));
});
const tablesLoading = computed(() => dataPreparationStore.loading);

// 字段数据
const mainTableColumns = ref<NormalizedFieldOption[]>([]);
const relatedTableColumns = ref<NormalizedFieldOption[]>([]);

const normalizeField = (f: any): NormalizedFieldOption => ({
  id: String(f.id),
  name: f.field_name || f.name || '',
  displayName: f.field_name || f.name || `field_${f.id}`,
  dataType: f.data_type || f.type || '',
});

const toStoreTableId = (tableId: string): string | number => {
  const n = Number(tableId);
  return Number.isNaN(n) ? tableId : n;
};

// 字段类型验证相关
const mainColumnType = ref<string>('');
const relatedColumnType = ref<string>('');

// 字段类型匹配验证
const showTypeValidation = computed(() => {
  return Boolean(mainColumnType.value && relatedColumnType.value);
});

const typeValidationStatus = computed(() => {
  if (!mainColumnType.value || !relatedColumnType.value) return 'info';
  return areTypesCompatible(mainColumnType.value, relatedColumnType.value) ? 'success' : 'warning';
});

const typeValidationMessage = computed(() => {
  if (!mainColumnType.value || !relatedColumnType.value) return '';
  
  const compatible = areTypesCompatible(mainColumnType.value, relatedColumnType.value);
  if (compatible) {
    return `字段类型匹配：${mainColumnType.value} ↔ ${relatedColumnType.value}`;
  } else {
    return `字段类型不匹配：${mainColumnType.value} ↔ ${relatedColumnType.value}，建议选择相同或兼容的数据类型`;
  }
});

// 字段类型兼容性检查
const areTypesCompatible = (type1: string, type2: string): boolean => {
  // 标准化类型名称（转换为小写并移除长度限制）
  const normalizeType = (type: string): string => {
    return type.toLowerCase()
      .replace(/\(\d+\)/g, '') // 移除长度限制，如 varchar(50) -> varchar
      .replace(/\s+/g, ''); // 移除空格
  };

  const normalizedType1 = normalizeType(type1);
  const normalizedType2 = normalizeType(type2);

  // 完全相同
  if (normalizedType1 === normalizedType2) return true;

  // 定义兼容类型组
  const compatibleGroups = [
    // 整数类型
    ['int', 'integer', 'bigint', 'smallint', 'tinyint'],
    // 浮点数类型
    ['float', 'double', 'decimal', 'numeric', 'real'],
    // 字符串类型
    ['varchar', 'char', 'text', 'string', 'nvarchar', 'nchar'],
    // 日期时间类型
    ['date', 'datetime', 'timestamp', 'time'],
    // 布尔类型
    ['boolean', 'bool', 'bit'],
  ];

  // 检查是否在同一兼容组中
  for (const group of compatibleGroups) {
    if (group.includes(normalizedType1) && group.includes(normalizedType2)) {
      return true;
    }
  }

  return false;
};

// 主表选择变化处理
const onMainTableChange = async (tableId: string) => {
  await dataPreparationStore.fetchTableFields(toStoreTableId(tableId) as any);
  const fields = (dataPreparationStore.tableFields || []) as TableField[];
  mainTableColumns.value = fields.map(normalizeField);
  formData.mainTableColumn = '';
  mainColumnType.value = '';
};

// 从表选择变化处理
const onRelatedTableChange = async (tableId: string) => {
  await dataPreparationStore.fetchTableFields(toStoreTableId(tableId) as any);
  const fields = (dataPreparationStore.tableFields || []) as TableField[];
  relatedTableColumns.value = fields.map(normalizeField);
  formData.relatedTableColumn = '';
  relatedColumnType.value = '';
};

// 主表字段选择变化处理
const onMainColumnChange = (columnId: string) => {
  const column = mainTableColumns.value.find(c => c.id === columnId);
  mainColumnType.value = column ? column.dataType : '';
};

// 从表字段选择变化处理
const onRelatedColumnChange = (columnId: string) => {
  const column = relatedTableColumns.value.find(c => c.id === columnId);
  relatedColumnType.value = column ? column.dataType : '';
};

// 监听初始数据变化
watch(() => props.initialData, (newData) => {
  if (newData) {
    Object.assign(formData, newData);
    // 如果有初始数据，需要加载对应的字段
    if (newData.mainTable) {
      onMainTableChange(newData.mainTable);
    }
    if (newData.relatedTable) {
      onRelatedTableChange(newData.relatedTable);
    }
  } else {
    formRef.value?.resetFields();
    mainTableColumns.value = [];
    relatedTableColumns.value = [];
    mainColumnType.value = '';
    relatedColumnType.value = '';
  }
}, { immediate: true, deep: true });

// 获取表单数据和验证方法
const getFormData = async () => {
  if (!formRef.value) return null;
  try {
    await formRef.value.validate();
    
    // 获取表和字段的详细信息
    const mainTable = availableTables.value.find(t => t.id === formData.mainTable);
    const relatedTable = availableTables.value.find(t => t.id === formData.relatedTable);
    const mainColumn = mainTableColumns.value.find(c => c.id === formData.mainTableColumn);
    const relatedColumn = relatedTableColumns.value.find(c => c.id === formData.relatedTableColumn);

    return {
      ...formData,
      // 添加额外的表和字段信息
      mainTableName: mainTable?.displayName || '',
      relatedTableName: relatedTable?.displayName || '',
      mainColumnName: mainColumn?.name || '',
      relatedColumnName: relatedColumn?.name || '',
      mainColumnType: mainColumn?.dataType || '',
      relatedColumnType: relatedColumn?.dataType || '',
      typesCompatible: areTypesCompatible(
        mainColumn?.dataType || '', 
        relatedColumn?.dataType || ''
      )
    };
  } catch (error) {
    console.error("Form validation failed:", error);
    return null;
  }
};

// 组件挂载时加载数据表
onMounted(async () => {
  // 如果数据表列表为空，则加载数据
  if (availableTables.value.length === 0) {
    await dataPreparationStore.fetchDataTables();
  }

  // 如果有初始数据，加载对应的字段
  if (props.initialData?.mainTable) {
    onMainTableChange(props.initialData.mainTable);
  }
  if (props.initialData?.relatedTable) {
    onRelatedTableChange(props.initialData.relatedTable);
  }
});

// 暴露方法给父组件
defineExpose({
  getFormData,
  areTypesCompatible,
});
</script>

<style scoped>
.relation-form {
  padding: 20px;
}
.el-select {
  width: 100%;
}
</style>
