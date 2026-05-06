<template>
  <div class="query-input">
    <div class="input-container">
      <input 
        v-model="currentQuery" 
        placeholder="请输入您的问题，例如：上月销售额最高的产品是什么？" 
        @keyup.enter="processQuery"
        @input="logInput"
      >
      <button @click="processQuery" class="btn-primary">分析</button>
    </div>
    <ExampleQuestions @query="handleExampleQuery" />
  </div>
</template>

<script>
import ExampleQuestions from './ExampleQuestions.vue'

// 创建日志函数
const createQueryLog = () => {
  const logKey = 'queryInputLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load query logs from localStorage');
  }
  return { logs, logKey };
};

const addQueryLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'input':
      console.groupCollapsed('%cQuery Input', 'color: #666; font-weight: bold');
      console.log('Text:', message);
      console.log('Length:', message.length);
      console.groupEnd();
      break;
    case 'submit':
      console.groupCollapsed('%cQuery Submitted', 'color: #1890ff; font-weight: bold');
      console.log('Query:', message);
      console.log('Length:', message.length);
      console.groupEnd();
      break;
    case 'example':
      console.groupCollapsed('%cExample Query Selected', 'color: #52c41a; font-weight: bold');
      console.log('Example:', message);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createQueryLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save query logs to localStorage');
  }
};

export default {
  name: 'QueryInput',
  components: {
    ExampleQuestions
  },
  data() {
    return {
      currentQuery: ''
    }
  },
  methods: {
    logInput() {
      addQueryLog('input', this.currentQuery);
    },
    processQuery() {
      if (this.currentQuery.trim()) {
        addQueryLog('submit', this.currentQuery);
        this.$emit('query', this.currentQuery);
        // 清空输入框
        this.currentQuery = '';
      } else {
        addQueryLog('error', 'Empty query submitted');
      }
    },
    handleExampleQuery(query) {
      addQueryLog('example', query);
      this.currentQuery = query;
      this.processQuery();
    }
  }
}
</script>

<style scoped>
.query-input {
  padding:20px;
  background-color: #fff;
  border-bottom:1px solid #eee;
}

.input-container {
  display: flex;
  gap:10px;
  margin-bottom:15px;
}

.input-container input {
  flex:1;
  padding:12px 16px;
  border:1px solid #ddd;
  border-radius:8px;
  font-size:16px;
  outline: none;
}

.input-container input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.btn-primary {
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