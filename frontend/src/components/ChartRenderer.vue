<template>
  <div class="chart-container">
    <div class="chart-placeholder">
      <div class="chart-title">{{ chartTitle }}</div>
      <div 
        v-for="(item, index) in data" 
        :key="index" 
        class="chart-bar"
        :style="{ height: (item.value / maxValue * 100) + '%' }"
      >
        <span class="chart-label">{{ item.label }}</span>
        <span class="chart-value">{{ formatCurrency(item.value) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
// 创建日志函数
const createChartLog = () => {
  const logKey = 'chartRendererLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load chart logs from localStorage');
  }
  return { logs, logKey };
};

const addChartLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'update':
      console.groupCollapsed('%cChart Data Updated', 'color: #1890ff; font-weight: bold');
      console.log('Title:', message);
      console.log('Data count:', data?.data?.length);
      console.log('Max value:', data?.maxValue);
      console.log('Data:', data?.data);
      console.groupEnd();
      break;
    case 'format':
      console.groupCollapsed('%cCurrency Formatted', 'color: #52c41a; font-weight: bold');
      console.log('Original value:', message);
      console.log('Formatted result:', data);
      console.groupEnd();
      break;
    case 'render':
      console.groupCollapsed('%cChart Rendered', 'color: #666; font-weight: bold');
      console.log('Component rendered with title:', message);
      console.log('Data structure:', data?.data);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createChartLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save chart logs to localStorage');
  }
};

export default {
  name: 'ChartRenderer',
  props: {
    chartTitle: String,
    data: Array,
    maxValue: Number
  },
  methods: {
    formatCurrency(value) {
      addChartLog('format', value, typeof value === 'number' ? '¥' + value.toLocaleString() : value);
      if (typeof value !== 'number') return value;
      return '¥' + value.toLocaleString();
    }
  },
  watch: {
    // 监听数据变化并记录
    data: {
      handler(newData, oldData) {
        addChartLog('update', this.chartTitle, {
          data: newData,
          maxValue: this.maxValue,
          oldData: oldData
        });
      },
      deep: true
    },
    chartTitle: {
      handler(newTitle) {
        addChartLog('update', newTitle, {
          data: this.data,
          maxValue: this.maxValue
        });
      }
    },
    maxValue: {
      handler(newMax) {
        addChartLog('update', this.chartTitle, {
          data: this.data,
          maxValue: newMax
        });
      }
    }
  },
  mounted() {
    addChartLog('render', this.chartTitle, {
      data: this.data,
      maxValue: this.maxValue
    });
  }
}
</script>

<style scoped>
.chart-container {
  padding:20px;
  background-color: #fff;
  border-radius:12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.chart-placeholder {
  display: flex;
  align-items: flex-end;
  height:300px;
  gap:15px;
  padding:20px 0;
}

.chart-title {
  text-align: center;
  font-size:18px;
  font-weight:600;
  margin-bottom:15px;
}

.chart-bar {
  flex:1;
  background: linear-gradient(to top, #1890ff, #0978e0);
  border-radius:8px 8px 0 0;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  min-width:40px;
  color: white;
  font-size:12px;
}

.chart-label {
  margin-top:8px;
  font-size:12px;
}

.chart-value {
  margin-bottom:8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-placeholder {
    flex-direction: column;
    height: 200px;
  }
  
  .chart-bar {
    min-width: 60px;
  }
}
</style>