<template>
  <div class="session-sidebar" :class="{ 'collapsed': isCollapsed }">
    <!-- 侧边栏头部 -->
    <div class="sidebar-header">
      <h3 v-if="!isCollapsed">{{ $t('chat.sessionHistory') }}</h3>
      <button class="toggle-btn" @click="toggleSidebar" :title="isCollapsed ? $t('thinking.expand') : $t('thinking.collapse')">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path v-if="isCollapsed" d="M9 18l6-6-6-6"/>
          <path v-else d="M15 18l-6-6 6-6"/>
        </svg>
      </button>
    </div>

    <!-- 新建会话按钮 -->
    <div v-if="!isCollapsed" class="new-session-btn-container">
      <button class="new-session-btn" @click="createNewSession">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <span>{{ $t('chat.newSession') }}</span>
      </button>
    </div>

    <!-- 会话列表 -->
    <div v-if="!isCollapsed" class="session-list">
      <div
        v-for="session in sessions"
        :key="session.session_id"
        class="session-item"
        :class="{ 'active': session.session_id === currentSessionId }"
        @click="switchToSession(session.session_id)"
      >
        <div class="session-content">
          <div class="session-title">{{ session.title || $t('chat.newSession') }}</div>
        </div>
        <button
          class="delete-btn"
          @click.stop="deleteSession(session.session_id)"
          :title="$t('common.close')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>

      <!-- 空状态 -->
      <div v-if="sessions.length === 0" class="empty-state">
        <p>{{ $t('chat.noHistory') }}</p>
        <p class="empty-hint">{{ $t('chat.newSession') }}</p>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading && !isCollapsed" class="loading-state">
      <div class="loading-spinner"></div>
      <p>{{ $t('common.loading') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useChatStore } from '@/store/modules/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// Props
interface Props {
  collapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: false
})

// Emits
const emit = defineEmits<{
  (e: 'toggle', collapsed: boolean): void
  (e: 'session-created', sessionId: string): void
  (e: 'session-switched', sessionId: string): void
  (e: 'session-deleted', sessionId: string): void
}>()

// Store
const chatStore = useChatStore()

// State
const isCollapsed = ref(props.collapsed)
const sessions = ref<any[]>([])
const isLoading = ref(false)

// Computed
const currentSessionId = computed(() => chatStore.currentSessionId)

// Methods
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
  emit('toggle', isCollapsed.value)
}

const createNewSession = () => {
  const sessionId = chatStore.createSession()
  emit('session-created', sessionId)
  ElMessage.success('已创建新对话')
  
  // 刷新会话列表
  loadSessions()
}

const switchToSession = (sessionId: string) => {
  if (sessionId === currentSessionId.value) return
  
  chatStore.switchSession(sessionId)
  emit('session-switched', sessionId)
}

const deleteSession = async (sessionId: string) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个对话吗？删除后无法恢复。',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 调用后端API删除
    try {
      await axios.delete(`/api/sessions/${sessionId}`)
    } catch (error) {
      console.warn('后端删除失败，仅删除本地数据:', error)
    }
    
    // 删除本地数据
    chatStore.deleteSession(sessionId)
    emit('session-deleted', sessionId)
    
    // 刷新会话列表
    await loadSessions()
    
    ElMessage.success('对话已删除')
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      console.error('删除会话失败:', error)
    }
  }
}

const loadSessions = async () => {
  try {
    isLoading.value = true
    
    // 调用后端API获取会话列表
    const response = await axios.get('/api/sessions/', {
      params: {
        limit: 50,
        offset: 0
      }
    })
    
    if (response.data.success) {
      sessions.value = response.data.data.sessions || []
    }
  } catch (error) {
    console.error('加载会话列表失败:', error)
    // 降级到本地数据
    sessions.value = chatStore.sessionList
  } finally {
    isLoading.value = false
  }
}

const formatTime = (timestamp: string | number) => {
  if (!timestamp) return ''
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  // 小于1分钟
  if (diff < 60 * 1000) {
    return '刚刚'
  }
  
  // 小于1小时
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes}分钟前`
  }
  
  // 小于24小时
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}小时前`
  }
  
  // 小于7天
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return `${days}天前`
  }
  
  // 显示日期
  return date.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric'
  })
}

// Lifecycle
onMounted(() => {
  loadSessions()
})

// 暴露方法供父组件调用
defineExpose({
  loadSessions
})
</script>

<style scoped>
/* ChatGPT 风格的紧凑侧边栏 */
.session-sidebar {
  width: 260px;
  height: 100%;
  background-color: #171717;
  border-right: 1px solid #2d2d2d;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.session-sidebar.collapsed {
  width: 50px;
}

/* 侧边栏头部 - 更紧凑 */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2d2d2d;
  background-color: #171717;
}

.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #ececec;
  margin: 0;
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: #8e8e8e;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  background-color: #2d2d2d;
  color: #ececec;
}

/* 新建会话按钮 - ChatGPT 风格 */
.new-session-btn-container {
  padding: 8px 12px;
}

.new-session-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 12px;
  background-color: transparent;
  color: #ececec;
  border: 1px solid #4d4d4d;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.new-session-btn:hover {
  background-color: #2d2d2d;
  border-color: #5e5e5e;
}

.new-session-btn:active {
  transform: scale(0.98);
}

/* 会话列表 - 更紧凑的间距 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 2px;
  background-color: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
  position: relative;
}

.session-item:hover {
  background-color: #2d2d2d;
}

.session-item.active {
  background-color: #2d2d2d;
  border-color: #4d4d4d;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 13px;
  font-weight: 400;
  color: #ececec;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.session-time {
  font-size: 11px;
  color: #8e8e8e;
  margin-bottom: 2px;
}

.session-preview {
  font-size: 11px;
  color: #8e8e8e;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #8e8e8e;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  opacity: 0;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background-color: #3d3d3d;
  color: #ef4444;
}

/* 空状态 - 深色主题 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #8e8e8e;
}

.empty-state p {
  margin: 8px 0;
  font-size: 13px;
}

.empty-hint {
  font-size: 12px;
  color: #5e5e5e;
}

/* 加载状态 - 深色主题 */
.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: #8e8e8e;
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid #2d2d2d;
  border-top-color: #ececec;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 滚动条样式 - 深色主题 */
.session-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: #3d3d3d;
  border-radius: 3px;
}

.session-list::-webkit-scrollbar-thumb:hover {
  background: #4d4d4d;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .session-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
  }
  
  .session-sidebar.collapsed {
    transform: translateX(-100%);
  }
}
</style>
