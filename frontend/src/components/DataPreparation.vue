<template>
  <div class="data-preparation">
    <h3>数据准备</h3>
    <div class="prep-item" @click="handleAction('create-table')">建表</div>
    <div class="prep-item" @click="handleAction('manage-dictionary')">字典表</div>
  </div>
</template>

<script>
// 创建日志函数
const createDataPrepLog = () => {
  const logKey = 'dataPreparationLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load data preparation logs from localStorage');
  }
  return { logs, logKey };
};

const addDataPrepLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'action':
      console.groupCollapsed('%cData Preparation Action', 'color: #1890ff; font-weight: bold');
      console.log('Action:', message);
      console.log('Timestamp:', data?.timestamp);
      console.groupEnd();
      break;
    case 'action-error':
      console.groupCollapsed('%cData Preparation Error', 'color: red; font-weight: bold');
      console.log('Action:', message);
      console.log('Error:', data?.error);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createDataPrepLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save data preparation logs to localStorage');
  }
};

export default {
  name: 'DataPreparation',
  methods: {
    handleAction(action) {
      try {
        addDataPrepLog('action', action, {
          timestamp: new Date().toISOString()
        });
        this.$emit('action', action);
      } catch (error) {
        addDataPrepLog('action-error', action, {
          error: error.message
        });
        console.error('Data preparation action error:', error);
      }
    }
  },
  mounted() {
    addDataPrepLog('update', 'Data preparation panel mounted');
  }
}
</script>

<style scoped>
.data-preparation {
  margin-bottom:20px;
}

.prep-item {
  padding:8px 12px;
  margin-bottom:8px;
  border-radius:6px;
  cursor: pointer;
}

.prep-item:hover {
  background-color: #f0f7ff;
}
</style>