<template>
  <div class="session-list">
    <h3>会话</h3>
    <VirtualList 
      :items="sessions" 
      :item-height="40" 
      :container-height="300"
    >
      <template #item="{ item, index }">
        <div 
          class="session-item"
          :class="{ active: currentSession && item.session_id === currentSession.session_id }"
          @click="handleSessionClick(item)"
        >
          {{ item.name }}
        </div>
      </template>
    </VirtualList>
    <button @click="createNewSession" class="btn-primary">新会话</button>
  </div>
</template>

<script>
// 创建日志函数
const createSessionLog = () => {
  const logKey = 'sessionChatLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load session logs from localStorage');
  }
  return { logs, logKey };
};

const addSessionLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'switch':
      console.groupCollapsed('%cSession Switched', 'color: #1890ff; font-weight: bold');
      console.log('Session ID:', message);
      console.log('Session Name:', data?.name);
      console.log('Previous Session:', data?.previous);
      console.groupEnd();
      break;
    case 'create':
      console.groupCollapsed('%cNew Session Created', 'color: #52c41a; font-weight: bold');
      console.log('Session ID:', message);
      console.log('Session Name:', data?.name);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createSessionLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save session logs to localStorage');
  }
};

import VirtualList from '@/components/VirtualList.vue';

export default {
  name: 'SessionChat',
  components: {
    VirtualList
  },
  props: {
    sessions: Array,
    currentSession: Object
  },
  methods: {
    handleSessionClick(session) {
      addSessionLog('switch', session.session_id, {
        name: session.name,
        previous: this.currentSession?.session_id || 'none'
      });
      this.$emit('switch', session);
    },
    createNewSession() {
      const sessionId = 'sess_' + Date.now();
      const sessionName = '新会话 ' + (this.sessions.length + 1);
      addSessionLog('create', sessionId, {
        name: sessionName
      });
      this.$emit('new-session');
    }
  }
}
</script>

<style scoped>
.session-list {
  margin-bottom:20px;
}

.session-item {
  padding:8px 12px;
  margin-bottom:6px;
  border-radius:6px;
  cursor: pointer;
  font-size:14px;
  color:#666;
}

.session-item:hover {
  background-color: #f0f7ff;
}

.btn-primary {
  width:100%;
  background-color: #1890ff;
  color: white;
  border: none;
  padding:12px 24px;
  border-radius:8px;
  font-size:16px;
  font-weight:500;
  cursor: pointer;
}

.btn-primary:hover {
  background-color: #0978e0;
}
</style>