<template>
  <el-drawer
    v-model="drawer"
    :title="'知识库管理'
    :direction="'rtl'"
    :size="'30%'"
    :with-header="true"
    :show-close="true"
    class="knowledge-base-panel"
  >
    <!-- 顶部搜索和新增按钮 -->
    <div class="panel-header">
      <el-input
        v-model="searchText"
        placeholder="搜索知识库..."
        clearable
        prefix-icon="el-icon-search"
        class="search-input"
      />
      <el-button
        type="primary"
        icon="el-icon-plus"
        @click="openCreateDialog"
        class="create-btn"
      >
        新增知识库
      </el-button>
    </div>

    <!-- 知识库列表 -->
    <div class="knowledge-list">
      <el-card
        v-for="kb in filteredKnowledgeBases"
        :key="kb.id"
        class="knowledge-item"
        shadow="hover"
      >
        <div class="item-header">
          <span class="kb-name">{{ kb.name }}</span>
          <span class="kb-type" :class="{ 'type-noun': kb.type === 'noun', 'type-text': kb.type === 'text' }">
            {{ kb.type === 'noun' ? '名词' : '文本' }}
          </span>
        </div>
        <div class="item-footer">
          <el-button
            size="small"
            text
            @click="editKnowledgeBase(kb)"
          >
            编辑
          </el-button>
          <el-button
            size="small"
            text
            @click="deleteKnowledgeBase(kb)"
            class="delete-btn"
          >
            删除
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 创建对话框 -->
    <CreateKnowledgeBaseDialog
      v-if="showCreateDialog"
      :visible="showCreateDialog"
      @close="showCreateDialog = false"
      @create="handleCreateKnowledgeBase"
    />
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue';
import CreateKnowledgeBaseDialog from './CreateKnowledgeBaseDialog.vue';

// 状态管理
const drawer = ref(false);
const showCreateDialog = ref(false);
const searchText = ref('');

// 模拟知识库数据（实际应用中应从API获取）
const knowledgeBases = ref([
  {
    id: 1,
    name: '毛利润定义',
    type: 'noun',
    language: 'zh',
    associatedTables: ['sales', 'finance'],
    scope: ['名词知识库', '业务逻辑知识库']
  },
  {
    id: 2,
    name: '默认时间范围',
    type: 'text',
    language: 'zh',
    associatedTables: ['sales', 'inventory'],
    scope: ['业务逻辑知识库', '数据解读']
  }
]);

// 过滤知识库列表
const filteredKnowledgeBases = computed(() => {
  return knowledgeBases.value.filter(kb =>
    kb.name.toLowerCase().includes(searchText.value.toLowerCase())
  );
});

// 打开创建对话框
const openCreateDialog = () => {
  showCreateDialog.value = true;
};

// 处理创建知识库
const handleCreateKnowledgeBase = (newKb) => {
  knowledgeBases.value.push(newKb);
  showCreateDialog.value = false;
};

// 编辑知识库（占位）
const editKnowledgeBase = (kb) => {
  console.log('编辑知识库:', kb);
};

// 删除知识库（占位）
const deleteKnowledgeBase = (kb) => {
  console.log('删除知识库:', kb);
};

// 公开方法，用于从外部打开抽屉
const open = () => {
  drawer.value = true;
};

// 公开方法，用于从外部关闭抽屉
const close = () => {
  drawer.value = false;
};

// 导出方法供父组件调用
defineExpose({
  open,
  close
});
</script>

<style scoped>
.knowledge-base-panel {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 0 16px;
}

.search-input {
  flex: 1;
}

.create-btn {
  min-width: 100px;
}

.knowledge-list {
  height: calc(100% - 80px);
  overflow-y: auto;
  padding: 0 16px;
}

.knowledge-item {
  margin-bottom: 12px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.kb-name {
  font-weight: 600;
  color: #303133;
}

.kb-type {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.type-noun {
  background-color: #e6f7ff;
  color: #1890ff;
}

.type-text {
  background-color: #f9f0ff;
  color: #722ed1;
}

.item-footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px;
  gap: 8px;
}

.delete-btn {
  color: #f56c6c;
}
</style>