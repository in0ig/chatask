<template>
  <div class="conversation-history-ui">
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <span class="title">对话历史</span>
          <div class="header-actions">
            <el-button type="primary" @click="exportSelected('json')" :disabled="selectedRows.length === 0">
              导出 JSON
            </el-button>
            <el-button type="primary" @click="exportSelected('csv')" :disabled="selectedRows.length === 0">
              导出 CSV
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-section">
        <el-input
          v-model="searchQuery"
          placeholder="按对话摘要搜索"
          clearable
          style="width: 300px"
          @keyup.enter="searchConversations"
        />
        <el-button type="primary" @click="searchConversations" style="margin-left: 10px">
          搜索
        </el-button>
        <el-button @click="resetSearch" style="margin-left: 10px">重置</el-button>
      </div>

      <!-- 对话历史列表 -->
      <div class="history-list">
        <div
          v-for="conversation in paginatedConversations"
          :key="conversation.id"
          class="conversation-item"
          @click="selectConversation(conversation)"
          :class="{ selected: selectedRows.includes(conversation.id) }"
        >
          <div class="item-checkbox">
            <input
              type="checkbox"
              :checked="selectedRows.includes(conversation.id)"
              @change="toggleSelection(conversation.id)"
              @click.stop
            />
          </div>
          <div class="item-content">
            <div class="item-header">
              <span class="item-id">{{ conversation.id }}</span>
              <span class="item-time">{{ formatDate(conversation.createdAt) }}</span>
            </div>
            <div class="item-summary">{{ truncateText(conversation.summary || getFirstMessage(conversation), 100) }}</div>
            <div class="item-meta">
              <span class="message-count">{{ conversation.messages.length }} 条消息</span>
            </div>
          </div>
          <div class="item-actions">
            <el-button size="small" @click.stop="viewConversation(conversation)">查看</el-button>
            <el-button size="small" type="primary" @click.stop="exportSingle(conversation)">导出</el-button>
            <el-popconfirm title="确定要删除吗？" @confirm="deleteConversation(conversation.id)">
              <template #reference>
                <el-button size="small" type="danger" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <div v-if="filteredConversations.length === 0" class="no-data">
          暂无对话历史
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredConversations.length"
          layout="prev, pager, next, jumper"
        />
      </div>
    </el-card>

    <!-- 查看对话详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="对话详情" width="80%" top="5vh">
      <div v-if="currentConversation && currentConversation.messages" class="conversation-detail">
        <div v-for="message in currentConversation.messages" :key="message.id" class="message-item">
          <div :class="['message-card', message.role === 'user' ? 'user-message' : 'assistant-message']">
            <div class="message-header">
              <span class="message-role">{{ message.role === 'user' ? '用户' : '助手' }}</span>
              <span class="message-time">{{ formatDate(message.timestamp) }}</span>
            </div>
            <div class="message-content">{{ message.content }}</div>
          </div>
        </div>
      </div>
      <div v-else class="no-messages">暂无消息</div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="exportSingle(currentConversation)">导出当前对话</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 定义数据类型
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface Conversation {
  id: string
  messages: Message[]
  createdAt: string
  updatedAt: string
  summary?: string
}

// 响应式数据
const conversations = ref<Conversation[]>([
  {
    id: 'conv_001',
    messages: [
      {
        id: 'msg_001',
        role: 'user',
        content: '我想查看上个月的销售数据',
        timestamp: '2024-12-01T10:30:00Z'
      },
      {
        id: 'msg_002',
        role: 'assistant',
        content: '好的，我已经为您生成了上个月的销售数据图表。',
        timestamp: '2024-12-01T10:31:00Z'
      }
    ],
    createdAt: '2024-12-01T10:30:00Z',
    updatedAt: '2024-12-01T10:31:00Z',
    summary: '用户查询上个月的销售数据'
  },
  {
    id: 'conv_002',
    messages: [
      {
        id: 'msg_003',
        role: 'user',
        content: '帮我分析一下产品A和产品B的销售趋势',
        timestamp: '2024-12-02T14:20:00Z'
      },
      {
        id: 'msg_004',
        role: 'assistant',
        content: '根据数据分析，产品A的销售额呈上升趋势，而产品B略有下降。',
        timestamp: '2024-12-02T14:22:00Z'
      }
    ],
    createdAt: '2024-12-02T14:20:00Z',
    updatedAt: '2024-12-02T14:22:00Z',
    summary: '分析产品A和B的销售趋势'
  }
])

const searchQuery = ref('')
const selectedRows = ref<string[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const currentConversation = ref<Conversation | null>(null)

// 计算属性
const filteredConversations = computed(() => {
  if (!searchQuery.value) {
    return conversations.value
  }
  return conversations.value.filter(conv =>
    (conv.summary || getFirstMessage(conv))
      .toLowerCase()
      .includes(searchQuery.value.toLowerCase())
  )
})

const totalPages = computed(() => {
  return Math.ceil(filteredConversations.value.length / pageSize.value)
})

const paginatedConversations = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredConversations.value.slice(start, end)
})

// 方法
const searchConversations = () => {
  currentPage.value = 1
}

const resetSearch = () => {
  searchQuery.value = ''
  currentPage.value = 1
}

const selectConversation = (conversation: Conversation) => {
  const index = selectedRows.value.indexOf(conversation.id)
  if (index > -1) {
    selectedRows.value.splice(index, 1)
  } else {
    selectedRows.value.push(conversation.id)
  }
}

const toggleSelection = (id: string) => {
  const index = selectedRows.value.indexOf(id)
  if (index > -1) {
    selectedRows.value.splice(index, 1)
  } else {
    selectedRows.value.push(id)
  }
}

const viewConversation = (conversation: Conversation) => {
  currentConversation.value = conversation
  dialogVisible.value = true
}

const deleteConversation = (id: string) => {
  const index = conversations.value.findIndex(c => c.id === id)
  if (index > -1) {
    conversations.value.splice(index, 1)
    ElMessage.success('删除成功')
  }
}

const exportSingle = (conversation: Conversation | null) => {
  if (!conversation) return
  ElMessageBox.confirm(
    '请选择导出格式',
    '导出对话',
    {
      confirmButtonText: 'JSON',
      cancelButtonText: 'CSV',
      distinguishCancelAndClose: true,
      type: 'info'
    }
  ).then(() => {
    exportConversation(conversation, 'json')
  }).catch(action => {
    if (action === 'cancel') {
      exportConversation(conversation, 'csv')
    }
  })
}

const exportSelected = (format: 'json' | 'csv') => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要导出的对话')
    return
  }

  selectedRows.value.forEach(id => {
    const conv = conversations.value.find(c => c.id === id)
    if (conv) {
      exportConversation(conv, format)
    }
  })
}

const exportConversation = (conversation: Conversation, format: 'json' | 'csv') => {
  if (format === 'json') {
    const dataStr = JSON.stringify(conversation, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)
    const exportFileDefaultName = `conversation_${conversation.id}.json`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  } else {
    let csvContent = 'ID,Role,Content,Timestamp\n'
    conversation.messages.forEach(msg => {
      csvContent += `"${msg.id}","${msg.role}","${msg.content.replace(/"/g, '""')}","${msg.timestamp}"\n`
    })

    const dataUri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent)
    const exportFileDefaultName = `conversation_${conversation.id}.csv`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  ElMessage.success(`对话已导出为${format.toUpperCase()}格式`)
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const truncateText = (text: string, length: number) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

const getFirstMessage = (conversation: Conversation): string => {
  if (conversation.messages && conversation.messages.length > 0) {
    return conversation.messages[0].content
  }
  return '无内容'
}

const handlePageChange = (page: number) => {
  currentPage.value = page
}
</script>

<style scoped>
.conversation-history-ui {
  padding: 20px;
}

.history-card {
  min-height: 700px;
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

.search-section {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.history-list {
  margin-bottom: 20px;
}

.conversation-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.conversation-item:hover {
  border-color: #409eff;
  background-color: #f5f7fa;
}

.conversation-item.selected {
  background-color: #e6f7ff;
  border-color: #409eff;
}

.item-checkbox {
  margin-right: 12px;
}

.item-checkbox input {
  cursor: pointer;
}

.item-content {
  flex: 1;
}

.item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.item-id {
  color: #606266;
  font-weight: 500;
}

.item-time {
  color: #909399;
}

.item-summary {
  color: #303133;
  margin-bottom: 8px;
  font-size: 14px;
}

.item-meta {
  display: flex;
  font-size: 12px;
  color: #909399;
}

.message-count {
  color: #606266;
}

.item-actions {
  display: flex;
  gap: 8px;
  margin-left: 12px;
}

.no-data {
  text-align: center;
  color: #909399;
  padding: 40px 20px;
  font-style: italic;
}

.pagination {
  margin-top: 20px;
  text-align: center;
}

.conversation-detail {
  max-height: 500px;
  overflow-y: auto;
}

.message-item {
  margin-bottom: 16px;
}

.message-card {
  padding: 12px;
  border-radius: 4px;
  border-left: 4px solid #409eff;
}

.message-card.user-message {
  border-left-color: #409eff;
  background-color: #f0f9ff;
}

.message-card.assistant-message {
  border-left-color: #67c23a;
  background-color: #f0f9ff;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}

.message-role {
  color: #606266;
  font-weight: 500;
}

.message-time {
  color: #909399;
}

.message-content {
  line-height: 1.6;
  word-break: break-word;
  color: #303133;
}

.no-messages {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
