import { defineStore } from 'pinia'

// 创建日志函数
const createStoreLog = () => {
  const logKey = 'storeLogs';
  let logs = [];
  try {
    const stored = localStorage.getItem(logKey);
    if (stored) {
      logs = JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load store logs from localStorage');
  }
  return { logs, logKey };
};

const addStoreLog = (type: string, message: string, data: any = null) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  // 输出到控制台
  switch(type) {
    case 'state-change':
      console.groupCollapsed('%cState Changed', 'color: #1890ff; font-weight: bold');
      console.log('Property:', message);
      console.log('Old value:', data?.oldValue);
      console.log('New value:', data?.newValue);
      console.log('Action:', data?.action);
      console.groupEnd();
      break;
    case 'action-start':
      console.groupCollapsed('%cAction Started', 'color: #52c41a; font-weight: bold');
      console.log('Action:', message);
      console.log('Parameters:', data?.params);
      console.groupEnd();
      break;
    case 'action-success':
      console.groupCollapsed('%cAction Successful', 'color: #52c41a; font-weight: bold');
      console.log('Action:', message);
      console.log('Result:', data?.result);
      console.groupEnd();
      break;
    case 'action-error':
      console.groupCollapsed('%cAction Error', 'color: red; font-weight: bold');
      console.log('Action:', message);
      console.log('Error:', data?.error);
      console.log('Parameters:', data?.params);
      console.groupEnd();
      break;
    case 'api-request':
      console.groupCollapsed('%cAPI Request', 'color: #1890ff; font-weight: bold');
      console.log('Endpoint:', message);
      console.log('Method:', data?.method);
      console.log('Payload:', data?.payload);
      console.groupEnd();
      break;
    case 'api-response':
      console.groupCollapsed('%cAPI Response', 'color: #52c41a; font-weight: bold');
      console.log('Endpoint:', message);
      console.log('Status:', data?.status);
      console.log('Response:', data?.response);
      console.groupEnd();
      break;
    case 'api-error':
      console.groupCollapsed('%cAPI Error', 'color: red; font-weight: bold');
      console.log('Endpoint:', message);
      console.log('Error:', data?.error);
      console.log('Status:', data?.status);
      console.groupEnd();
      break;
    default:
      console.log(`[${type}]`, message, data);
  }
  
  // 存储到localStorage模拟文件
  const { logs, logKey } = createStoreLog();
  logs.push(logEntry);
  // 限制日志数量，避免内存溢出
  if (logs.length > 500) {
    logs.shift();
  }
  try {
    localStorage.setItem(logKey, JSON.stringify(logs));
  } catch (e) {
    console.warn('Failed to save store logs to localStorage');
  }
};

// 导入所有模块
import { useChatStore } from './modules/chat'
import { useDataPrepStore } from './modules/dataPrep'
import { useUIStore } from './modules/ui'
import { useConfigStore } from './modules/config'

// 导出所有 store
export {
  useChatStore,
  useDataPrepStore,
  useUIStore,
  useConfigStore
}

// 主 store 保持兼容性
export const useChatbiStore = defineStore('chatbi', {
  state: () => ({
    currentQuery: '',
    isLoading: false,
    errorMessage: '',
    result: null,
    aiExplanation: '',
    dataSources: [],
    activeDataSource: null,
    historyQueries: [
      '上月销售额最高的产品是什么？',
      '各区域销售对比',
      '客户转化率趋势'
    ],
    sessions: [
      { id: 'sess_1', name: '新会话' },
      { id: 'sess_2', name: '会话1' }
    ],
    currentSession: null as { id: string; name: string } | null
  }),
  getters: {
    hasActiveDataSource(): boolean {
      return this.activeDataSource !== null;
    }
  },
  actions: {
    async processQuery(query: string) {
      addStoreLog('action-start', 'processQuery', { params: { query } });
      
      if (!query.trim()) {
        addStoreLog('action-error', 'processQuery', { 
          error: 'Empty query', 
          params: { query } 
        });
        return;
      }
      
      if (!this.hasActiveDataSource) {
        this.errorMessage = '请先上传并激活一个数据源';
        addStoreLog('action-error', 'processQuery', { 
          error: 'No active data source', 
          params: { query } 
        });
        return;
      }
      
      this.isLoading = true;
      this.errorMessage = '';
      this.result = null;
      this.aiExplanation = '';
      
      addStoreLog('state-change', 'isLoading', { 
        oldValue: false, 
        newValue: true, 
        action: 'processQuery' 
      });
      addStoreLog('state-change', 'errorMessage', { 
        oldValue: this.errorMessage, 
        newValue: '', 
        action: 'processQuery' 
      });
      addStoreLog('state-change', 'result', { 
        oldValue: this.result, 
        newValue: null, 
        action: 'processQuery' 
      });
      addStoreLog('state-change', 'aiExplanation', { 
        oldValue: this.aiExplanation, 
        newValue: '', 
        action: 'processQuery' 
      });
      
      try {
        addStoreLog('api-request', '/query', { 
          method: 'POST', 
          payload: { text: query } 
        });
        
        const response = await fetch('/api/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ text: query })
        });
        
        addStoreLog('api-response', '/query', { 
          status: response.status, 
          response: response 
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          const errorMessage = errorData.details || '查询处理失败';
          addStoreLog('api-error', '/query', { 
            error: errorMessage, 
            status: response.status 
          });
          throw new Error(errorMessage);
        }
        
        const data = await response.json();
        this.result = data.result;
        this.aiExplanation = data.result.raw.length > 0 ? 
          `根据销售数据分析，${data.result.data[0].label} 是${data.result.chartTitle}中表现最佳的产品...` :
          '已成功解析您的查询并返回相关数据。';
        
        addStoreLog('state-change', 'result', { 
          oldValue: null, 
          newValue: this.result, 
          action: 'processQuery' 
        });
        addStoreLog('state-change', 'aiExplanation', { 
          oldValue: '', 
          newValue: this.aiExplanation, 
          action: 'processQuery' 
        });
        
        // 添加到历史记录
        if (!this.historyQueries.includes(query)) {
          const oldHistoryLength = this.historyQueries.length;
          this.historyQueries.unshift(query);
          if (this.historyQueries.length > 5) {
            this.historyQueries.pop();
          }
          addStoreLog('state-change', 'historyQueries', { 
            oldValue: oldHistoryLength, 
            newValue: this.historyQueries.length, 
            action: 'processQuery' 
          });
        }
        
        addStoreLog('action-success', 'processQuery', { 
          result: 'Query processed successfully', 
          params: { query } 
        });
      } catch (error) {
        this.errorMessage = error.message;
        addStoreLog('state-change', 'errorMessage', { 
          oldValue: '', 
          newValue: this.errorMessage, 
          action: 'processQuery' 
        });
        addStoreLog('action-error', 'processQuery', { 
          error: error.message, 
          params: { query } 
        });
      } finally {
        this.isLoading = false;
        addStoreLog('state-change', 'isLoading', { 
          oldValue: true, 
          newValue: false, 
          action: 'processQuery' 
        });
      }
    },
    async uploadFile(file: File) {
      addStoreLog('action-start', 'uploadFile', { params: { fileName: file?.name, fileSize: file?.size } });
      
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        addStoreLog('api-request', '/datasources/upload', { 
          method: 'POST', 
          payload: { file: file?.name } 
        });
        
        const response = await fetch('/api/datasources/upload', {
          method: 'POST',
          body: formData
        });
        
        addStoreLog('api-response', '/datasources/upload', { 
          status: response.status, 
          response: response 
        });
        
        if (!response.ok) {
          const error = '文件上传失败';
          addStoreLog('api-error', '/datasources/upload', { 
            error: error, 
            status: response.status 
          });
          throw new Error(error);
        }
        
        const dataSource = await response.json();
        const oldSourcesLength = this.dataSources.length;
        this.dataSources.push(dataSource);
        this.activeDataSource = dataSource;
        
        addStoreLog('state-change', 'dataSources', { 
          oldValue: oldSourcesLength, 
          newValue: this.dataSources.length, 
          action: 'uploadFile' 
        });
        addStoreLog('state-change', 'activeDataSource', { 
          oldValue: this.activeDataSource, 
          newValue: dataSource, 
          action: 'uploadFile' 
        });
        
        addStoreLog('action-success', 'uploadFile', { 
          result: 'File uploaded successfully', 
          params: { fileName: file?.name } 
        });
      } catch (error) {
        this.errorMessage = error.message;
        addStoreLog('state-change', 'errorMessage', { 
          oldValue: this.errorMessage, 
          newValue: error.message, 
          action: 'uploadFile' 
        });
        addStoreLog('action-error', 'uploadFile', { 
          error: error.message, 
          params: { fileName: file?.name } 
        });
      }
    },
    async activateDataSource(sourceId: string) {
      addStoreLog('action-start', 'activateDataSource', { params: { sourceId } });
      
      try {
        addStoreLog('api-request', `/api/datasources/${sourceId}/activate`, { 
          method: 'PUT', 
          payload: { sourceId } 
        });
        
        const response = await fetch(`/api/datasources/${sourceId}/activate`, {
          method: 'PUT'
        });
        
        addStoreLog('api-response', `/api/datasources/${sourceId}/activate`, { 
          status: response.status, 
          response: response 
        });
        
        if (!response.ok) {
          const error = '激活数据源失败';
          addStoreLog('api-error', `/api/datasources/${sourceId}/activate`, { 
            error: error, 
            status: response.status 
          });
          throw new Error(error);
        }
        
        const data = await response.json();
        if (data.success) {
          const oldActive = this.activeDataSource;
          this.activeDataSource = this.dataSources.find(s => s.id === sourceId);
          this.result = null;
          this.aiExplanation = '';
          
          addStoreLog('state-change', 'activeDataSource', { 
            oldValue: oldActive, 
            newValue: this.activeDataSource, 
            action: 'activateDataSource' 
          });
          addStoreLog('state-change', 'result', { 
            oldValue: this.result, 
            newValue: null, 
            action: 'activateDataSource' 
          });
          addStoreLog('state-change', 'aiExplanation', { 
            oldValue: this.aiExplanation, 
            newValue: '', 
            action: 'activateDataSource' 
          });
          
          addStoreLog('action-success', 'activateDataSource', { 
            result: 'Data source activated successfully', 
            params: { sourceId } 
          });
        }
      } catch (error: any) {
        this.errorMessage = error?.message || 'Unknown error';
        addStoreLog('state-change', 'errorMessage', { 
          oldValue: this.errorMessage, 
          newValue: error?.message || 'Unknown error', 
          action: 'activateDataSource' 
        });
        addStoreLog('action-error', 'activateDataSource', { 
          error: error?.message || 'Unknown error', 
          params: { sourceId } 
        });
      }
    },
    switchSession(session: any) {
      addStoreLog('action-start', 'switchSession', { params: { sessionId: session?.id } });
      
      const oldSession = this.currentSession;
      this.currentSession = session;
      
      addStoreLog('state-change', 'currentSession', { 
        oldValue: oldSession, 
        newValue: this.currentSession, 
        action: 'switchSession' 
      });
      
      addStoreLog('action-success', 'switchSession', { 
        result: 'Session switched successfully', 
        params: { sessionId: session?.id } 
      });
    },
    createNewSession() {
      addStoreLog('action-start', 'createNewSession');
      
      const newSession = { id: `sess_${Date.now()}`, name: '新会话' };
      const oldSessionsLength = this.sessions.length;
      this.sessions.unshift(newSession);
      this.currentSession = newSession;
      
      addStoreLog('state-change', 'sessions', { 
        oldValue: oldSessionsLength, 
        newValue: this.sessions.length, 
        action: 'createNewSession' 
      });
      addStoreLog('state-change', 'currentSession', { 
        oldValue: this.currentSession, 
        newValue: newSession, 
        action: 'createNewSession' 
      });
      
      addStoreLog('action-success', 'createNewSession', { 
        result: 'New session created successfully', 
        params: { sessionId: newSession.session_id } 
      });
    }
  }
})