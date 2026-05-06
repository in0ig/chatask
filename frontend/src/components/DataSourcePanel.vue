<template>
  <div class="data-source">
    <h3>数据源</h3>
    <div 
      v-for="(source, index) in dataSources" 
      :key="source.id" 
      :class="['source-item', { active: activeSource && source.id === activeSource.id }]"
      @click="handleSourceActivate(source)"
    >
      <span>{{ source.name }}</span>
      <span class="source-status" :class="{ 'active-status': activeSource && source.id === activeSource.id }">✓</span>
    </div>
    
    <div class="upload-section">
      <input 
        type="file" 
        accept=".xlsx,.xls,.csv" 
        @change="handleFileUpload($event)" 
        id="file-upload" 
        style="display: none;"
      >
      <label for="file-upload" class="btn-primary upload-btn">上传Excel文件</label>
    </div>
    
    <!-- 新增：数据表选择按钮 -->
    <div class="table-select-section">
      <el-button 
        type="primary" 
        size="small" 
        @click="openTableSelector"
        class="table-select-btn"
      >
        选择数据表
      </el-button>
    </div>
  </div>
</template>

<script>
// 创建日志函数
const createDataSourceLog = () => {
  const logKey = 'dataSourcePanelLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load data source logs from localStorage');
  }
  return { logs, logKey };
};

const addDataSourceLog = (type, message, data = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'activate':
      console.groupCollapsed('%cData Source Activated', 'color: #1890ff; font-weight: bold');
      console.log('Source ID:', message);
      console.log('Source Name:', data?.name);
      console.log('Source Type:', data?.type);
      console.log('Previous active:', data?.previous);
      console.groupEnd();
      break;
    case 'upload':
      console.groupCollapsed('%cExcel File Uploaded', 'color: #52c41a; font-weight: bold');
      console.log('File name:', message);
      console.log('File size:', data?.size);
      console.log('File type:', data?.type);
      console.groupEnd();
      break;
    case 'upload-error':
      console.groupCollapsed('%cUpload Error', 'color: red; font-weight: bold');
      console.log('Error:', message);
      console.log('File info:', data?.file);
      console.groupEnd();
      break;
    case 'click':
      console.groupCollapsed('%cData Source Clicked', 'color: #666; font-weight: bold');
      console.log('Source ID:', message);
      console.log('Source Name:', data?.name);
      console.log('Total sources:', data?.total);
      console.groupEnd();
      break;
    case 'table-select':
      console.groupCollapsed('%cTable Selector Opened', 'color: #1890ff; font-weight: bold');
      console.log('Action:', message);
      console.log('Selected tables:', data?.selected);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createDataSourceLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save data source logs to localStorage');
  }
};

import TableSelectorModal from '@/components/TableSelectorModal.vue';
import { useUIStore } from '@/store/modules/ui';

export default {
  name: 'DataSourcePanel',
  components: {
    TableSelectorModal
  },
  props: {
    dataSources: Array,
    activeSource: Object
  },
  methods: {
    handleSourceActivate(source) {
      addDataSourceLog('activate', source.id, {
        name: source.name,
        type: source.type,
        previous: this.activeSource?.id || 'none'
      });
      this.$emit('activate', source);
    },
    handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) {
        addDataSourceLog('upload-error', 'No file selected', { file });
        return;
      }
      
      addDataSourceLog('upload', file.name, {
        size: file.size,
        type: file.type,
        lastModified: file.lastModified
      });
      
      this.$emit('upload', file);
      
      // 清空文件输入，以便可以重复上传同名文件
      event.target.value = '';
    },
    
    // 打开数据表选择弹窗
    openTableSelector() {
      const uiStore = useUIStore();
      uiStore.openDataSourceModal();
      addDataSourceLog('table-select', 'opened', { selected: [] });
    }
  },
  watch: {
    dataSources: {
      handler(newSources, oldSources) {
        if (newSources && oldSources && newSources.length !== oldSources.length) {
          addDataSourceLog('update', 'Data sources updated', {
            total: newSources.length,
            previous: oldSources.length
          });
        }
      },
      deep: true
    },
    activeSource: {
      handler(newActive, oldActive) {
        if (newActive || oldActive) {
          addDataSourceLog('update', 'Active source changed', {
            newActive: newActive?.id || 'none',
            oldActive: oldActive?.id || 'none'
          });
        }
      }
    }
  },
  mounted() {
    addDataSourceLog('update', 'Data source panel mounted', {
      total: this.dataSources.length,
      active: this.activeSource?.id || 'none'
    });
  }
}
</script>

<style scoped>
.data-source {
  margin-bottom:20px;
}

.source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding:10px 12px;
  margin-bottom:8px;
  border-radius:6px;
  cursor: pointer;
}

.source-item:hover {
  background-color: #f0f7ff;
}

.source-item.active {
  background-color: #e6f7ff;
  border-left:3px solid #1890ff;
}

.source-status {
  color: #1890ff;
  font-weight: bold;
}

.source-status.active-status {
  color: #1890ff;
}

.upload-section {
  margin-top:20px;
}

.upload-btn {
  width:100%;
  margin-top:10px;
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

.table-select-section {
  margin-top: 15px;
}

.table-select-btn {
  width: 100%;
  margin-top: 8px;
}
</style>