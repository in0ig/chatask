<template>
  <div class="history-list">
    <h3>历史查询</h3>
    <VirtualList 
      :items="history" 
      :item-height="40" 
      :container-height="300"
    >
      <template #item="{ item, index }">
        <div 
          class="history-item"
          @click="handleQueryLoad(item)"
        >
          {{ item }}
        </div>
      </template>
    </VirtualList>
  </div>
</template>

<script>
// 创建日志函数
const createHistoryLog = () => {
  const logKey = 'historyPanelLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load history logs from localStorage');
  }
  return { logs, logKey };
};

const addHistoryLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'load':
      console.groupCollapsed('%cHistory Query Loaded', 'color: #1890ff; font-weight: bold');
      console.log('Query:', message);
      console.log('History length:', data?.length);
      console.log('Position:', data?.position);
      console.groupEnd();
      break;
    case 'update':
      console.groupCollapsed('%cHistory Updated', 'color: #52c41a; font-weight: bold');
      console.log('New query added:', message);
      console.log('Total queries:', data?.total);
      console.log('Previous count:', data?.previous);
      console.groupEnd();
      break;
    case 'click':
      console.groupCollapsed('%cHistory Item Clicked', 'color: #666; font-weight: bold');
      console.log('Query:', message);
      console.log('Index:', data?.index);
      console.log('Total items:', data?.total);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createHistoryLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save history logs to localStorage');
  }
};

import VirtualList from '@/components/VirtualList.vue';

export default {
  name: 'HistoryPanel',
  components: {
    VirtualList
  },
  props: {
    history: Array
  },
  methods: {
    handleQueryLoad(query) {
      addHistoryLog('load', query, {
        length: this.history.length,
        position: this.history.indexOf(query)
      });
      this.$emit('load', query);
    }
  },
  watch: {
    history: {
      handler(newHistory, oldHistory) {
        if (newHistory && oldHistory) {
          const newQuery = newHistory[newHistory.length - 1];
          addHistoryLog('update', newQuery, {
            total: newHistory.length,
            previous: oldHistory.length
          });
        }
      },
      deep: true
    }
  },
  mounted() {
    addHistoryLog('update', 'History panel mounted', {
      total: this.history.length
    });
  }
}
</script>

<style scoped>
.history-list {
  margin-bottom:20px;
}

.history-item {
  padding:8px 12px;
  margin-bottom:6px;
  border-radius:6px;
  cursor: pointer;
  font-size:14px;
  color:#666;
}

.history-item:hover {
  background-color: #f0f7ff;
}
</style>