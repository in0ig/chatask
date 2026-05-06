<template>
  <div class="navigation-sidebar">
    <!-- Logo 区域 -->
    <div class="logo-section">
      <div class="logo-content">
        <span class="logo-icon"></span>
        <span class="logo-text">Ask Jarvis</span>
      </div>
      <div class="logo-separator"></div>
    </div>
    
    <nav class="nav-menu">
      <ul>
        <!-- 数据分析组 - 只保留ChatBI -->
        <li class="menu-item group-header" @click="toggleGroup('analysis')">
          <div class="menu-link group-link">
            <span class="menu-icon">📊</span>
            <span class="menu-text">{{ $t('nav.dataAnalysis') }}</span>
            <span class="toggle-icon" :class="{ 'expanded': expandedGroups.analysis }">▼</span>
          </div>
        </li>
        <li v-for="item in analysisItems" :key="item.path" class="menu-item" v-show="expandedGroups.analysis">
          <router-link 
            :to="item.path" 
            :class="{ 'active': isActive(item.path) }"
            class="menu-link"
          >
            <span class="menu-icon"></span>
            <span class="menu-text">{{ item.label }}</span>
          </router-link>
        </li>
        
        <!-- 数据准备组 -->
        <li class="menu-item group-header" @click="toggleGroup('dataPrep')">
          <div class="menu-link group-link">
            <span class="menu-icon">📁</span>
            <span class="menu-text">{{ $t('nav.dataPrep') }}</span>
            <span class="toggle-icon" :class="{ 'expanded': expandedGroups.dataPrep }">▼</span>
          </div>
        </li>
        <li v-for="item in dataPrepItems" :key="item.path" class="menu-item" v-show="expandedGroups.dataPrep">
          <router-link 
            :to="item.path" 
            :class="{ 'active': isActive(item.path) }"
            class="menu-link"
          >
            <span class="menu-icon"></span>
            <span class="menu-text">{{ item.label }}</span>
          </router-link>
        </li>
        
        <!-- 对话历史组 -->
        <li class="menu-item group-header" @click="toggleGroup('chatHistory')">
          <div class="menu-link group-link">
            <span class="menu-icon">💬</span>
            <span class="menu-text">{{ $t('chat.sessionHistory') }}</span>
            <span class="toggle-icon" :class="{ 'expanded': expandedGroups.chatHistory }">▼</span>
          </div>
        </li>
        
        <!-- 新建对话按钮 -->
        <li v-show="expandedGroups.chatHistory" class="menu-item new-chat-item">
          <button class="new-chat-btn" @click="createNewSession">
            <span class="menu-icon">➕</span>
            <span class="menu-text">{{ $t('nav.newChat') }}</span>
          </button>
        </li>
        
        <!-- 会话列表 -->
        <li 
          v-for="session in sessions" 
          :key="session.session_id" 
          v-show="expandedGroups.chatHistory"
          class="menu-item session-item"
          :class="{ 'active-session': session.session_id === currentSessionId }"
          @click="switchToSession(session.session_id)"
        >
          <div class="session-link">
            <span class="session-title">{{ session.title || t('chat.newSession') }}</span>
            <button 
              class="delete-session-btn"
              @click="deleteSession(session.session_id, $event)"
              title="🗑️"
            >
              🗑️
            </button>
          </div>
        </li>
        
        <!-- 加载状态 -->
        <li v-if="isLoadingSessions && expandedGroups.chatHistory" class="menu-item loading-item">
          <div class="loading-text">{{ $t('common.loading') }}</div>
        </li>
        
        <!-- 空状态 -->
        <li v-if="!isLoadingSessions && sessions.length === 0 && expandedGroups.chatHistory" class="menu-item empty-item">
          <div class="empty-text">{{ $t('chat.noHistory') }}</div>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router';
import { ref, computed, onMounted, watch } from 'vue';
import { useChatStore } from '@/store/modules/chat';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';
import { useI18n } from 'vue-i18n';

const router = useRouter();
const route = useRoute();
const chatStore = useChatStore();
const { t } = useI18n();

// 分析数据项 - 只保留ChatBI
const analysisItems = computed(() => [
  { label: 'Ask Jarvis', path: '/' }
]);

// 数据准备项
const dataPrepItems = computed(() => [
  { label: t('nav.tables'), path: '/data-prep/tables' },
  { label: t('nav.datasources'), path: '/chatbi/datasources' },
  { label: t('nav.dictionaries'), path: '/data-prep/dictionaries' },
  { label: t('nav.relations'), path: '/data-prep/relations' }
]);

// 会话列表：合并后端会话与本地会话，避免“已新建但左侧不显示”
const sessions = computed(() => {
  const merged = new Map<string, any>();

  // 1) 先放后端数据（权威）
  backendSessions.value.forEach((s: any) => {
    merged.set(s.session_id, { ...s });
  });

  // 2) 再合并本地数据（兜底）
  chatStore.sessionList.forEach((s: any) => {
    const existing = merged.get(s.session_id);
    if (!existing) {
      merged.set(s.session_id, {
        session_id: s.session_id,
        title: s.title || t('chat.newSession'),
        created_at: s.createdAt,
        last_activity_at: s.updatedAt
      });
      return;
    }

    // 后端标题为空或默认标题时，优先使用本地标题
    if (!existing.title || existing.title === '新对话') {
      existing.title = s.title || existing.title || t('chat.newSession');
    }
  });

  const toMs = (v: any) => {
    if (!v) return 0;
    if (typeof v === 'number') return v;
    const n = new Date(v).getTime();
    return Number.isNaN(n) ? 0 : n;
  };

  return Array.from(merged.values()).sort((a: any, b: any) => {
    const ta = toMs(a.last_activity_at || a.updatedAt || a.created_at || a.createdAt);
    const tb = toMs(b.last_activity_at || b.updatedAt || b.created_at || b.createdAt);
    return tb - ta;
  });
});

// 后端加载的会话列表
const backendSessions = ref<any[]>([]);
const isLoadingSessions = ref(false);

// 折叠/展开状态管理
const expandedGroups = ref({
  analysis: true,
  dataPrep: true,
  chatHistory: true  // 新增：对话历史分组
});

// 当前会话ID
const currentSessionId = computed(() => chatStore.currentSessionId);

// 切换分组展开/折叠状态
function toggleGroup(groupName: string) {
  expandedGroups.value[groupName] = !expandedGroups.value[groupName];
}

// 检查当前路由是否匹配
function isActive(path: string) {
  return route.path === path;
}

// 新建对话
async function createNewSession() {
  const sessionId = chatStore.createSession();
  
  // 同步创建后端会话，确保历史记录可见
  try {
    await axios.post('/api/sessions/create', {
      session_id: sessionId,
      title: '新对话'
    });
    console.log('✅ 后端会话已创建:', sessionId);
  } catch (error) {
    console.warn('⚠️ 后端会话创建失败，仅本地创建:', error);
  }
  
  ElMessage.success('已创建新对话');
  
  // 如果不在首页，跳转到首页
  if (route.path !== '/') {
    router.push('/');
  }
  
  // 刷新会话列表
  loadSessions();
}

// 切换会话
function switchToSession(sessionId: string) {
  if (sessionId === currentSessionId.value) return;

  // 兼容：若会话只存在于后端列表，先写入 store 再切换
  if (!chatStore.sessions[sessionId]) {
    const fromSidebar = sessions.value.find((s: any) => s.session_id === sessionId);
    if (fromSidebar) {
      chatStore.sessions[sessionId] = {
        session_id: sessionId,
        title: fromSidebar.title || '新对话',
        createdAt: fromSidebar.created_at || Date.now(),
        updatedAt: fromSidebar.last_activity_at || Date.now(),
        messages: []
      } as any;
    }
  }

  chatStore.switchSession(sessionId);
  
  // 如果不在首页，跳转到首页
  if (route.path !== '/') {
    router.push('/');
  }
}

// 删除会话
async function deleteSession(sessionId: string, event: Event) {
  event.stopPropagation();  // 阻止事件冒泡
  
  try {
    await ElMessageBox.confirm(
      '确定要删除这个对话吗？删除后无法恢复。',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    // 调用后端API删除
    try {
      await axios.delete(`/api/sessions/${sessionId}`);
    } catch (error) {
      console.warn('后端删除失败，仅删除本地数据:', error);
    }
    
    // 删除本地数据
    chatStore.deleteSession(sessionId);
    
    // 刷新会话列表
    await loadSessions();
    
    ElMessage.success('对话已删除');
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      console.error('删除会话失败:', error);
    }
  }
}

// 加载会话列表
async function loadSessions() {
  try {
    isLoadingSessions.value = true;
    
    // 调用后端API获取会话列表
    const response = await axios.get('/api/sessions/', {
      params: {
        limit: 50,
        offset: 0
      }
    });
    
    if (response.data.success) {
      backendSessions.value = response.data.data.sessions || [];
      console.log('✅ 侧边栏会话列表已刷新，数量:', backendSessions.value.length);
    }
  } catch (error) {
    console.error('加载会话列表失败:', error);
    // 降级到本地数据 - 不需要手动设置，computed 会自动使用 chatStore.sessionList
  } finally {
    isLoadingSessions.value = false;
  }
}

// 组件挂载时加载会话列表
onMounted(() => {
  loadSessions();
});

// 监听 chatStore 中会话数量的变化，自动刷新侧边栏
watch(
  () => Object.keys(chatStore.sessions).length,
  (newCount, oldCount) => {
    // 当会话数量增加时（新建会话），自动刷新侧边栏
    if (newCount > oldCount) {
      console.log('🔄 检测到新会话创建，自动刷新侧边栏');
      loadSessions();
    }
  }
);

// 监听当前会话标题的变化，自动刷新侧边栏
watch(
  () => {
    const currentSession = chatStore.currentSessionId ? chatStore.sessions[chatStore.currentSessionId] : null;
    return currentSession?.title;
  },
  (newTitle, oldTitle) => {
    // 当标题从默认值变为生成的标题时，刷新侧边栏
    if (newTitle && newTitle !== oldTitle && oldTitle === '新对话') {
      console.log('🔄 检测到会话标题更新，自动刷新侧边栏:', newTitle);
      loadSessions();
    }
  }
);
</script>

<style scoped>
/* ChatGPT 风格的深色导航侧边栏 */
.navigation-sidebar {
  width: 260px;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background-color: #171717;
  border-right: 1px solid #2d2d2d;
  overflow-y: auto;
  color: #ececec;
}

/* Logo 区域 */
.logo-section {
  height: 56px;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.logo-content {
  display: flex;
  align-items: center;
}

.logo-icon {
  font-size: 20px;
  margin-right: 8px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #ececec;
}

.logo-separator {
  height: 1px;
  background-color: #2d2d2d;
  margin-top: 8px;
}

.nav-menu ul {
  list-style: none;
  margin: 0;
  padding: 8px;
}

.menu-item {
  margin-bottom: 2px;
}

.menu-link {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  text-decoration: none;
  color: #ececec;
  font-weight: 400;
  border-radius: 8px;
  transition: all 0.15s ease;
  width: 100%;
  box-sizing: border-box;
  font-size: 13px;
}

.menu-link:hover {
  background-color: #2d2d2d;
}

.menu-link.active {
  background-color: #2d2d2d;
  font-weight: 500;
  color: #ffffff;
}

.menu-icon {
  margin-right: 10px;
  font-size: 16px;
  width: 16px;
  display: inline-block;
}

.menu-text {
  flex: 1;
  font-size: 13px;
}

/* 分组标题样式 */
.group-header {
  margin-top: 8px;
  margin-bottom: 2px;
}

.group-header .menu-link {
  font-weight: 500;
  font-size: 13px;
  color: #ececec;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.group-header .menu-link:hover {
  background-color: #2d2d2d;
}

.group-header .menu-link .toggle-icon {
  font-size: 10px;
  margin-left: 8px;
  transition: transform 0.2s ease;
  color: #8e8e8e;
}

.group-header .menu-link .toggle-icon.expanded {
  transform: rotate(180deg);
}

/* 新建对话按钮 */
.new-chat-item {
  margin-bottom: 4px;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background-color: transparent;
  color: #ececec;
  border: 1px solid #4d4d4d;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.15s ease;
}

.new-chat-btn:hover {
  background-color: #2d2d2d;
  border-color: #5e5e5e;
}

.new-chat-btn:active {
  transform: scale(0.98);
}

.new-chat-btn .menu-icon {
  margin-right: 10px;
}

/* 会话列表项 */
.session-item {
  cursor: pointer;
}

.session-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  transition: all 0.15s ease;
  background-color: transparent;
}

.session-item:hover .session-link {
  background-color: #2d2d2d;
}

.session-item.active-session .session-link {
  background-color: #2d2d2d;
  border-left: 3px solid #4d4d4d;
}

.session-title {
  flex: 1;
  font-size: 13px;
  color: #ececec;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.delete-session-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  font-size: 14px;
  opacity: 0;
  transition: all 0.15s ease;
  border-radius: 4px;
  flex-shrink: 0;
}

.session-item:hover .delete-session-btn {
  opacity: 1;
}

.delete-session-btn:hover {
  background-color: #3d3d3d;
}

/* 加载和空状态 */
.loading-item,
.empty-item {
  padding: 10px 12px;
  text-align: center;
}

.loading-text,
.empty-text {
  font-size: 12px;
  color: #8e8e8e;
}

/* 滚动条样式 */
.navigation-sidebar::-webkit-scrollbar {
  width: 6px;
}

.navigation-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.navigation-sidebar::-webkit-scrollbar-thumb {
  background: #3d3d3d;
  border-radius: 3px;
}

.navigation-sidebar::-webkit-scrollbar-thumb:hover {
  background: #4d4d4d;
}
</style>