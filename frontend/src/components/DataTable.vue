<template>
  <div class="data-table">
    <h4>详细数据</h4>
    <table>
      <thead>
        <tr>
          <th v-for="header in headers" :key="header">{{ header }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="index">
          <td 
            v-for="(cell, cellIndex) in row" 
            :key="cellIndex"
            :class="{ 'currency': isCurrencyColumn(cellIndex) }"
          >
            {{ formatCell(cell, cellIndex) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
// 创建日志函数
const createTableLog = () => {
  const logKey = 'dataTableLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load table logs from localStorage');
  }
  return { logs, logKey };
};

const addTableLog = (type, message, data = null) => {
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
      console.groupCollapsed('%cTable Data Updated', 'color: #1890ff; font-weight: bold');
      console.log('Headers count:', message);
      console.log('Rows count:', data?.rows?.length);
      console.log('Headers:', data?.headers);
      console.log('Rows:', data?.rows);
      console.groupEnd();
      break;
    case 'format':
      console.groupCollapsed('%cCell Formatted', 'color: #52c41a; font-weight: bold');
      console.log('Original value:', message);
      console.log('Column index:', data?.index);
      console.log('Formatted result:', data?.result);
      console.log('Is currency column:', data?.isCurrency);
      console.groupEnd();
      break;
    case 'render':
      console.groupCollapsed('%cTable Rendered', 'color: #666; font-weight: bold');
      console.log('Component rendered with headers:', message);
      console.log('Rows structure:', data?.rows);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createTableLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save table logs to localStorage');
  }
};

export default {
  name: 'DataTable',
  props: {
    headers: Array,
    rows: Array
  },
  methods: {
    isCurrencyColumn(index) {
      // 设第二列为货币列
      addTableLog('format', 'isCurrencyColumn check', {
        index: index,
        result: index === 1
      });
      return index === 1;
    },
    formatCell(value, index) {
      // 检查是否为货币列
      const isCurrency = this.isCurrencyColumn(index);
      let formattedValue = value;
      
      if (isCurrency && typeof value === 'number') {
        // 使用全局方法格式化货币（假设$root有formatCurrency方法）
        try {
          formattedValue = this.$root.formatCurrency ? this.$root.formatCurrency(value) : '¥' + value.toLocaleString();
        } catch (error) {
          formattedValue = '¥' + value.toLocaleString();
          addTableLog('error', 'Format currency failed', {
            value: value,
            index: index,
            error: error.message
          });
        }
      }
      
      addTableLog('format', value, {
        index: index,
        isCurrency: isCurrency,
        result: formattedValue
      });
      
      return formattedValue;
    }
  },
  watch: {
    // 监听数据变化并记录
    headers: {
      handler(newHeaders, oldHeaders) {
        addTableLog('update', newHeaders?.length || 0, {
          headers: newHeaders,
          rows: this.rows,
          oldHeaders: oldHeaders
        });
      },
      deep: true
    },
    rows: {
      handler(newRows, oldRows) {
        addTableLog('update', this.headers?.length || 0, {
          headers: this.headers,
          rows: newRows,
          oldRows: oldRows
        });
      },
      deep: true
    }
  },
  mounted() {
    addTableLog('render', this.headers?.length || 0, {
      headers: this.headers,
      rows: this.rows
    });
  }
}
</script>

<style scoped>
.data-table {
  padding:20px;
  background-color: #fff;
  border-radius:12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.data-table h4 {
  margin-bottom:15px;
  color: #333;
}

table {
  width:100%;
  border-collapse: collapse;
}

th, td {
  padding:12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background-color: #f8f9fa;
  font-weight:600;
  color: #333;
}

tr:hover {
  background-color: #f8f9fa;
}

.currency {
  color: #d4380d; /* 红色 */
}
</style>