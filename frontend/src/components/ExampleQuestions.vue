<template>
  <div class="examples">
    <span 
      v-for="(query, index) in exampleQueries" 
      :key="index" 
      class="example"
      @click="handleExampleClick(query.text)"
    >
      {{ query.text }}
    </span>
  </div>
</template>

<script>
// 创建日志函数
const createExampleLog = () => {
  const logKey = 'exampleQuestionsLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load example logs from localStorage');
  }
  return { logs, logKey };
};

const addExampleLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'click':
      console.groupCollapsed('%cExample Query Clicked', 'color: #52c41a; font-weight: bold');
      console.log('Query:', message);
      console.log('Total examples:', data?.total);
      console.log('Position:', data?.position);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createExampleLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save example logs to localStorage');
  }
};

export default {
  name: 'ExampleQuestions',
  data() {
    return {
      exampleQueries: [
        { text: '上月销售额最高的产品是什么？' },
        { text: '各区域销售对比' },
        { text: '客户转化率趋势' }
      ]
    }
  },
  methods: {
    handleExampleClick(query) {
      addExampleLog('click', query, {
        total: this.exampleQueries.length,
        position: this.exampleQueries.findIndex(q => q.text === query)
      });
      this.$emit('query', query);
    }
  },
  mounted() {
    addExampleLog('update', 'Example questions component mounted', {
      total: this.exampleQueries.length
    });
  }
}
</script>

<style scoped>
.examples {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.example {
  background-color: #f0f7ff;
  color: #1890ff;
  padding:6px 12px;
  border-radius:16px;
  font-size:13px;
  cursor: pointer;
}

.example:hover {
  background-color: #e6f7ff;
}
</style>