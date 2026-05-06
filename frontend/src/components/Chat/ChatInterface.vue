<template>
  <div class="chat-interface">
    <!-- 消息列表区域 -->
    <div class="message-list" ref="messageListRef">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message-item"
        :class="`message-${message.role}`"
      >
        <div class="message-avatar">
          <el-avatar :size="32">
            {{ message.role === 'user' ? 'U' : 'AI' }}
          </el-avatar>
        </div>
        <div class="message-content">
          <div class="message-header">
            <span class="message-role">{{ getRoleName(message.role) }}</span>
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
          </div>
          <div
            class="message-body"
            :class="{
              'message-thinking': message.type === 'thinking',
              'message-streaming': message.status === 'streaming'
            }"
          >
            <MessageContent 
              :message="message"
              :show-actions="message.role !== 'system'"
              :can-edit="message.role === 'user' && message.status === 'sent'"
              :can-resend="message.role === 'user' && message.status === 'error'"
              :can-rollback="message.role === 'assistant' && messages.indexOf(message) < messages.length - 1"
              @edit="handleEditMessage(message.id, $event)"
              @resend="handleResendMessage(message.id)"
              @export="handleExportMessage(message.id, $event)"
              @share="handleShareMessage(message.id, $event)"
              @rollback="handleRollbackToMessage(message.id)"
            />
          </div>
        </div>
      </div>

      <!-- 加载指示器 -->
      <div v-if="isStreaming" class="streaming-indicator">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>AI 正在思考...</span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="输入您的问题..."
        :disabled="isStreaming"
        @keydown.enter.ctrl="handleSend"
      />
      <div class="input-actions">
        <el-button
          type="primary"
          :disabled="!inputText.trim() || isStreaming"
          :loading="isStreaming"
          @click="handleSend"
        >
          发送 (Ctrl+Enter)
        </el-button>
        <el-button @click="handleClear">清空对话</el-button>
      </div>
    </div>

    <!-- 连接状态指示 -->
    <div v-if="!isConnected" class="connection-status">
      <el-alert
        title="连接已断开"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #default>
          正在尝试重新连接...
        </template>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useChatStore } from '@/store/modules/chat'
import { createWebSocketService } from '@/services/websocketService'
import MessageContent from './MessageContent.vue'
import type { WSMessage } from '@/types/chat'

// Store
const chatStore = useChatStore()

// 响应式数据
const inputText = ref('')
const messageListRef = ref<HTMLElement>()

// WebSocket 服务实例
let websocketService: ReturnType<typeof createWebSocketService> | null = null

// 计算属性
const messages = computed(() => chatStore.currentMessages)
const isConnected = computed(() => chatStore.isConnected)
const isStreaming = computed(() => chatStore.isStreaming)

// 当前流式消息ID
let currentStreamingMessageId: string | null = null

// 格式化时间
const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 获取角色名称
const getRoleName = (role: string): string => {
  const roleMap: Record<string, string> = {
    user: '用户',
    assistant: 'AI 助手',
    system: '系统'
  }
  return roleMap[role] || role
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// 处理发送消息
const handleSend = async () => {
  console.log('=== 📤 ChatInterface.handleSend 开始执行 ===')
  console.log('⏱️ 时间戳:', new Date().toLocaleTimeString())
  console.log('📝 inputText.value:', inputText.value)
  console.log('🆔 chatStore.currentSessionId:', chatStore.currentSessionId)
  console.log('⏳ isStreaming.value:', isStreaming.value)
  
  const text = inputText.value.trim()
  if (!text || isStreaming.value) {
    console.log('⚠️ 输入为空或正在流式输出，退出')
    return
  }

  // 添加用户消息
  console.log('📝 添加用户消息到 Store')
  chatStore.addMessage({
    role: 'user',
    type: 'text',
    content: text,
    status: 'sent'
  })
  console.log('✅ 用户消息已添加')

  // 清空输入
  inputText.value = ''
  console.log('✅ 输入框已清空')

  // 滚动到底部
  scrollToBottom()

  // 设置流式状态
  console.log('⏳ 设置流式状态为 true')
  chatStore.setStreaming(true)
  console.log('✅ 流式状态已设置')

  // 调用后端 API 开始对话
  try {
    const sessionId = chatStore.currentSessionId
    const url = `/api/chat/start/${sessionId}?user_question=${encodeURIComponent(text)}`
    
    console.log('🌐 发起请求')
    console.log('🌐 URL:', url)
    console.log('🌐 方法: POST')
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })

    console.log('🌐 响应状态:', response.status)
    console.log('🌐 响应状态文本:', response.statusText)

    if (!response.ok) {
      const errorText = await response.text()
      console.error('🌐 错误响应体:', errorText)
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    console.log('✅ 请求成功，后端返回:', result)
    
    if (!result.success) {
      throw new Error(result.message || '对话处理失败')
    }

    // 对话已通过 WebSocket 流式推送，这里不需要额外处理
    console.log('✅ Chat started successfully')
    console.log('=== ✅ ChatInterface.handleSend 执行完成 ===')
    
  } catch (error) {
    console.error('=== ❌ ChatInterface.handleSend 执行出错 ===')
    console.error('⏱️ 时间戳:', new Date().toLocaleTimeString())
    console.error('❌ 错误类型:', error instanceof Error ? error.constructor.name : typeof error)
    console.error('❌ 错误信息:', (error as Error).message)
    console.error('❌ 错误堆栈:', (error as Error).stack)
    
    ElMessage.error('发送失败: ' + (error as Error).message)
    console.log('✅ 流式状态已重置为 false')
    chatStore.setStreaming(false)
    
    // 添加错误消息
    chatStore.addMessage({
      role: 'system',
      type: 'error',
      content: '消息发送失败，请重试',
      status: 'error'
    })
  }
}

// 处理清空对话
const handleClear = () => {
  chatStore.clearCurrentSession()
}

// 处理编辑消息
const handleEditMessage = (messageId: string, newContent: string) => {
  chatStore.editMessage(messageId, newContent)
  ElMessage.success('消息已更新')
}

// 处理重发消息
const handleResendMessage = async (messageId: string) => {
  const message = messages.value.find(m => m.id === messageId)
  if (message) {
    chatStore.resendMessage(messageId)
    chatStore.setStreaming(true)
    
    // 重新发送到后端
    try {
      const response = await fetch(
        `/api/chat/start/${chatStore.currentSessionId}?user_question=${encodeURIComponent(message.content)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (!result.success) {
        throw new Error(result.message || '对话处理失败')
      }

      ElMessage.success('消息已重新发送')
    } catch (error) {
      ElMessage.error('重发失败: ' + (error as Error).message)
      console.error('Failed to resend message:', error)
      chatStore.setStreaming(false)
    }
  }
}

// 处理导出消息
const handleExportMessage = (messageId: string, format: string) => {
  const message = messages.value.find(m => m.id === messageId)
  if (!message) return
  
  chatStore.exportMessage(messageId, format)
  
  // 根据格式导出
  let content = ''
  let filename = ''
  
  if (format === 'csv' || format === 'excel') {
    // 导出表格数据
    if (message.type === 'table' && message.metadata?.data) {
      const data = message.metadata.data
      const columns = message.metadata.columns || []
      
      // 生成CSV内容
      const header = columns.join(',')
      const rows = data.map((row: any) => 
        columns.map((col: string) => row[col] || '').join(',')
      ).join('\n')
      content = `${header}\n${rows}`
      filename = `table_${messageId}.csv`
    }
  } else {
    // 导出文本内容
    content = message.content
    filename = `message_${messageId}.txt`
  }
  
  // 创建下载
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('导出成功')
}

// 处理分享消息
const handleShareMessage = (messageId: string, method: string) => {
  chatStore.shareMessage(messageId, method)
  ElMessage.success(`已通过${method}方式分享`)
}

// 处理回溯到消息
const handleRollbackToMessage = (messageId: string) => {
  chatStore.rollbackToMessage(messageId)
  ElMessage.success('已回溯到此消息')
}

// 处理 WebSocket 消息
const handleWSMessage = (wsMessage: WSMessage) => {
  switch (wsMessage.type) {
    case 'thinking':
      // 创建思考过程消息
      currentStreamingMessageId = chatStore.addMessage({
        role: 'assistant',
        type: 'thinking',
        content: wsMessage.content,
        status: 'streaming'
      })
      scrollToBottom()
      break

    case 'message':
      // 追加流式内容
      if (currentStreamingMessageId) {
        chatStore.appendMessageContent(currentStreamingMessageId, wsMessage.content)
        scrollToBottom()
      }
      break

    case 'result':
      // 完成当前思考消息
      if (currentStreamingMessageId) {
        chatStore.updateMessage(currentStreamingMessageId, {
          status: 'completed'
        })
      }

      // 创建最终结果消息
      currentStreamingMessageId = chatStore.addMessage({
        role: 'assistant',
        type: 'text',
        content: wsMessage.content,
        status: 'completed',
        metadata: wsMessage.metadata
      })
      scrollToBottom()
      break

    case 'error':
      // 创建错误消息
      chatStore.addMessage({
        role: 'system',
        type: 'error',
        content: wsMessage.content,
        status: 'error'
      })
      chatStore.setStreaming(false)
      currentStreamingMessageId = null
      scrollToBottom()
      break

    case 'complete':
      // 完成流式输出
      if (currentStreamingMessageId) {
        chatStore.updateMessage(currentStreamingMessageId, {
          status: 'completed'
        })
      }
      chatStore.setStreaming(false)
      currentStreamingMessageId = null
      break
  }
}

// 处理连接状态变化
const handleConnectionChange = (connected: boolean) => {
  chatStore.setConnected(connected)
  if (connected) {
    ElMessage.success('连接已建立')
  } else {
    ElMessage.warning('连接已断开')
  }
}

// 处理错误
const handleError = (error: Error) => {
  chatStore.setError(error.message)
  ElMessage.error(`连接错误: ${error.message}`)
}

// 生命周期
onMounted(async () => {
  // 创建默认会话
  if (!chatStore.currentSessionId) {
    chatStore.createSession()
  }

  // 创建 WebSocket 服务实例
  websocketService = createWebSocketService(chatStore.currentSessionId!)

  // 连接 WebSocket
  try {
    await websocketService.connect()
    
    // 注册事件处理器
    websocketService.onMessage(handleWSMessage)
    websocketService.onConnection(handleConnectionChange)
    websocketService.onError(handleError)
  } catch (error) {
    console.error('Failed to connect WebSocket:', error)
    ElMessage.error('无法连接到服务器')
  }
})

onUnmounted(() => {
  // 断开 WebSocket
  if (websocketService) {
    websocketService.disconnect()
  }
})

// 监听消息变化，自动滚动
watch(messages, () => {
  scrollToBottom()
}, { deep: true })
</script>

<style scoped lang="scss">
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f5f7fa;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-thumb {
    background-color: #dcdfe6;
    border-radius: 3px;
  }
}

.message-item {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease-in;
  
  &.message-user {
    flex-direction: row-reverse;
    
    .message-content {
      align-items: flex-end;
    }
    
    .message-body {
      background-color: #409eff;
      color: white;
    }
  }
  
  &.message-assistant,
  &.message-system {
    .message-body {
      background-color: white;
      border: 1px solid #e4e7ed;
    }
  }
}

.message-avatar {
  margin: 0 12px;
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  color: #909399;
  
  .message-role {
    font-weight: 500;
    margin-right: 8px;
  }
}

.message-body {
  padding: 12px 16px;
  border-radius: 8px;
  word-wrap: break-word;
  line-height: 1.6;
  
  &.message-thinking {
    color: #909399;
    font-style: italic;
    background-color: #f4f4f5 !important;
  }
  
  &.message-streaming {
    position: relative;
    
    &::after {
      content: '▋';
      animation: blink 1s infinite;
    }
  }
}

.streaming-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  color: #909399;
  font-size: 14px;
  
  .el-icon {
    margin-right: 8px;
  }
}

.input-area {
  padding: 20px;
  background-color: white;
  border-top: 1px solid #e4e7ed;
  
  .el-textarea {
    margin-bottom: 12px;
  }
  
  .input-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}

.connection-status {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
</style>
