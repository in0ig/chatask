<template>
  <div class="conversation-history">
    <!-- 标题和操作按钮 -->
    <div class="header">
      <h3>对话历史</h3>
      <div class="actions">
        <el-button 
          size="small" 
          type="primary" 
          @click="exportHistory"
          :disabled="history.length === 0"
        >
          导出
        </el-button>
        <el-button 
          size="small" 
          type="danger" 
          @click="clearHistory"
          :disabled="history.length === 0"
        >
          清空
        </el-button>
      </div>
    </div>
    
    <!-- 搜索框 -->
    <div class="search-container">
      <el-input 
        v-model="searchQuery" 
        placeholder="搜索对话内容..." 
        size="small"
        clearable
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>
    
    <!-- 对话历史列表 -->
    <div class="history-list">
      <div class="conversation-detail">
        <div 
          v-for="item in filteredHistory" 
          :key="item.id"
          class="history-item"
          :class="{ selected: selectedItemId === item.id }"
          @click="selectItem(item)"
        >
          <div class="item-header">
            <span class="turn-number">第 {{ item.turn }} 轮</span>
            <span class="intent-tag" :class="`intent-${item.intent}`">
</span>
              {{ getIntentLabel(item.intent) }}
            </span>
            <span class="timestamp">{{ formatTime(item.createdAt) }}</span>
          </div>
          <div class="item-content">
            <span class="role" :class="item.role">{{ item.role === 'user' ? '用户：' : '助手：' }}</span>
            <span class="content">{{ item.content }}</span>
          </div>
          <div class="item-actions">
            <el-button 
              size="small" 
              type="danger" 
              class="delete-btn" 
              @click.stop="deleteItem(item)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 无数据提示 -->
      <div v-if="filteredHistory.length === 0" class="empty-state">
        <el-empty description="暂无对话历史" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/store/modules/chat'
import { ElEmpty } from 'element-plus'
import { Search } from '@element-plus/icons-vue'

const chatStore = useChatStore()

// 状态
const searchQuery = ref('')
const selectedItemId = ref<string | null>(null)

// 获取对话历史
const history = computed(() => chatStore.getConversationHistory())

// 过滤历史记录
const filteredHistory = computed(() => {
  if (!searchQuery.value) return history.value
  
  return history.value.filter(item => 
    item.content.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    item.intent.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// 获取意图标签
const getIntentLabel = (intent: string): string => {
  const labels: Record<string, string> = {
    query: '查询',
    interpretation: '解释',
    report: '报告',
    data_prep: '数据准备'
  }
  return labels[intent] || intent
}

// 格式化时间
const formatTime = (date: Date): string => {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 选择项目
const selectItem = (item: any) => {
  selectedItemId.value = item.id
}

// 删除项目
const deleteItem = (item: any) => {
  // 实际实现中应调用API删除，这里先从本地状态移除
  const index = history.value.findIndex(i => i.id === item.id)
  if (index !== -1) {
    chatStore.conversationHistory.splice(index, 1)
    selectedItemId.value = null
  }
}

// 导出历史
const exportHistory = () => {
  const dataStr = JSON.stringify(history.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chat-history-${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// 清空历史
const clearHistory = () => {
  if (confirm('确定要清空所有对话历史吗？')) {
    chatStore.conversationHistory = []
    selectedItemId.value = null
  }
}
</script>

<style scoped>
.conversation-history {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.actions {
  display: flex;
  gap: 8px;
}

.search-container {
  margin-bottom: 16px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.history-item {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.history-item.selected {
  border-color: #1890ff;
  background-color: #f0f7ff;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
}

.turn-number {
  color: #666;
}

.intent-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
}

.intent-query {
  background-color: #1890ff;
}

.intent-interpretation {
  background-color: #faad14;
}

.intent-report {
  background-color: #52c41a;
}

.intent-data_prep {
  background-color: #eb2f96;
}

.timestamp {
  color: #999;
}

.item-content {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.role {
  font-weight: 600;
  margin-right: 8px;
  color: #333;
}

.role.user {
  color: #1890ff;
}

.role.assistant {
  color: #52c41a;
}

.content {
  color: #333;
  flex: 1;
  word-wrap: break-word;
}

.item-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}
</style>