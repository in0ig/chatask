<template>
  <div class="knowledge-base-manager">
    <!-- 返回按钮和标题 -->
    <div class="header">
      <el-button
        type="info"
        plain
        icon="ArrowLeft"
        @click="emit('back')"
        style="margin-right: 10px;"
      >
        {{ $t('knowledgeBase.back') }}
      </el-button>
      <h3>{{ $t('knowledgeBase.title') }}</h3>
    </div>
    
    <!-- 左右布局容器 -->
    <div class="layout-container">
      <!-- 左侧：知识库列表 (30%宽度) -->
      <div class="left-panel">
        <KnowledgeBaseList 
          @add="openAddModal" 
          @select="selectKnowledgeBase"
          :selected-id="selectedKnowledgeBaseId"
        />
      </div>
      
      <!-- 右侧：知识库详情 (70%宽度) -->
      <div class="right-panel">
        <KnowledgeBaseDetail 
          v-if="selectedKnowledgeBaseId"
          :knowledge-base-id="selectedKnowledgeBaseId"
        />
        <div class="empty-state" v-else>
          <p>{{ $t('knowledgeBase.empty') }}</p>
        </div>
      </div>
    </div>
    
    <!-- 新增知识库弹窗 -->
    <AddKnowledgeBaseModal
      v-model:visible="isAddModalVisible"
      @submit="handleAddSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import KnowledgeBaseList from './KnowledgeBaseList.vue'
import AddKnowledgeBaseModal from './AddKnowledgeBaseModal.vue'
import KnowledgeBaseDetail from './KnowledgeBaseDetail.vue'

const emit = defineEmits(['back'])

const isAddModalVisible = ref(false)
const selectedKnowledgeBaseId = ref<string | null>(null)

// 打开新增知识库弹窗
const openAddModal = () => {
  isAddModalVisible.value = true
}

// 处理新增成功
const handleAddSuccess = (newKnowledgeBase: any) => {
  isAddModalVisible.value = false
  // 在成功后选择新创建的知识库
  if (newKnowledgeBase) {
    selectedKnowledgeBaseId.value = newKnowledgeBase.id
  }
}

// 选择知识库
const selectKnowledgeBase = (id: number) => {
  selectedKnowledgeBaseId.value = id
}
</script>

<style scoped>
.knowledge-base-manager {
  height: 100%;
  padding: 16px;
}

.header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}

.header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.layout-container {
  display: flex;
  height: calc(100% - 50px);
  overflow: hidden;
}

.left-panel {
  width: 40%;
  min-width: 350px;
  max-width: 500px;
  padding-right: 15px;
  border-right: 2px solid #e0e0e0;
  background-color: #fafafa;
  overflow-y: auto;
  overflow-x: hidden;
}

.right-panel {
  flex: 1;
  padding-left: 15px;
  background-color: white;
  overflow-y: auto;
  overflow-x: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}
</style>