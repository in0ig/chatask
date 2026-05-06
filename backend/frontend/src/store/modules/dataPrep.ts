import { defineStore } from 'pinia';
import ApiService from '@/services/api';

export const useDataPrepStore = defineStore('dataPrep', {
  state: () => ({
    dataSources: [],
    dataTables: [],
    tableRelations: [],
    isLoading: false,
    error: null,
    activeTab: 'datasources',
    errorLog: [],
    retryCount: 0
  }),

  actions: {
    validateApiResponse(response, expectedFields = []) {
      // 验证响应是否为对象
      if (!response || typeof response !== 'object') {
        throw new Error('API响应格式无效：响应不是对象');
      }
      
      // 验证是否包含 data 字段
      if (!response.hasOwnProperty('data')) {
        throw new Error('API响应格式无效：缺少 data 字段');
      }
      
      // 验证 data 字段是否为数组或对象
      if (!Array.isArray(response.data) && typeof response.data !== 'object') {
        throw new Error('API响应格式无效：data 字段必须是数组或对象');
      }
      
      // 验证预期字段是否存在（如果提供）
      if (expectedFields.length > 0 && Array.isArray(response.data)) {
        if (response.data.length > 0) {
          const firstItem = response.data[0];
          if (typeof firstItem !== 'object') {
            throw new Error('API响应格式无效：data 数组中的元素必须是对象');
          }
          
          for (const field of expectedFields) {
            if (!firstItem.hasOwnProperty(field)) {
              throw new Error(`API响应格式无效：data 数组中的元素缺少必要字段 ${field}`);
            }
          }
        }
      }
      
      return true;
    },
    
    classifyError(error) {
      // 网络错误：连接失败、超时、DNS 解析失败等
      if (!error.response && error.code === 'ECONNABORTED') {
        return 'NETWORK_TIMEOUT';
      }
      
      if (!error.response && !error.code) {
        return 'NETWORK_CONNECTION_FAILED';
      }
      
      // 服务器错误：5xx 状态码
      if (error.response && error.response.status >= 500) {
        return 'SERVER_ERROR';
      }
      
      // 客户端错误：4xx 状态码
      if (error.response && error.response.status >= 400 && error.response.status < 500) {
        return 'CLIENT_ERROR';
      }
      
      // 数据格式错误：响应结构无效
      if (error.message.includes('API响应格式无效')) {
        return 'DATA_FORMAT_ERROR';
      }
      
      // 默认错误类型
      return 'UNKNOWN_ERROR';
    },
    
    shouldRetry(error) {
      // 只对网络错误和服务器错误进行重试
      const errorType = this.classifyError(error);
      return errorType === 'NETWORK_TIMEOUT' || 
             errorType === 'NETWORK_CONNECTION_FAILED' || 
             errorType === 'SERVER_ERROR';
    },
    
    formatErrorMessage(error) {
      const errorType = this.classifyError(error);
      
      switch (errorType) {
        case 'NETWORK_TIMEOUT':
          return '网络超时，请检查网络连接后重试';
        case 'NETWORK_CONNECTION_FAILED':
          return '网络连接失败，请检查网络连接后重试';
        case 'SERVER_ERROR':
          return '服务器内部错误，请稍后再试';
        case 'CLIENT_ERROR':
          return error.response?.data?.detail || '请求参数错误，请检查输入后重试';
        case 'DATA_FORMAT_ERROR':
          return '数据格式错误，系统无法解析响应，请稍后再试';
        default:
          return '未知错误，请稍后再试';
      }
    },
    async fetchAllData() {
      this.isLoading = true;
      this.error = null;
      this.retryCount = 0;
      
      const maxRetries = 3;
      const baseDelay = 1000; // 1秒
      
      const attemptFetch = async (retryCount) => {
        try {
          // 获取所有数据源
          const sourcesResponse = await ApiService.getDataSources();
          this.validateApiResponse(sourcesResponse, ['id', 'name', 'type', 'is_active']);
          // 确保 data 是数组类型，如果不是则使用空数组
          this.dataSources = Array.isArray(sourcesResponse.data) ? sourcesResponse.data : [];
          
          // 获取所有数据表
          const tablesResponse = await ApiService.getDataTables();
          this.validateApiResponse(tablesResponse, ['id', 'name', 'source_id', 'table_name']);
          // 确保 data 是数组类型，如果不是则使用空数组
          this.dataTables = Array.isArray(tablesResponse.data) ? tablesResponse.data : [];
          
          // 获取所有表关联
          const relationsResponse = await ApiService.getTableRelations();
          this.validateApiResponse(relationsResponse, ['id', 'from_table_id', 'to_table_id', 'relation_type']);
          // 确保 data 是数组类型，如果不是则使用空数组
          this.tableRelations = Array.isArray(relationsResponse.data) ? relationsResponse.data : [];
          
          // 清除之前的错误日志
          this.errorLog = [];
          
          return true;
        } catch (error) {
          // 记录错误上下文
          const errorContext = {
            timestamp: new Date().toISOString(),
            operation: 'fetchAllData',
            retryCount: retryCount,
            errorType: this.classifyError(error),
            message: error.message,
            stack: error.stack
          };
          
          // 添加到错误日志
          this.errorLog.push(errorContext);
          
          // 根据错误类型处理
          if (retryCount < maxRetries && this.shouldRetry(error)) {
            // 指数退避延迟
            const delay = baseDelay * Math.pow(2, retryCount);
            await new Promise(resolve => setTimeout(resolve, delay));
            
            // 递归重试
            return await attemptFetch(retryCount + 1);
          } else {
            // 最终失败，设置错误信息
            this.error = this.formatErrorMessage(error);
            throw error;
          }
        }
      };
      
      try {
        await attemptFetch(0);
      } finally {
        this.isLoading = false;
      }
    },
    
    async openAddDataSourceDialog() {
      // 模拟打开添加数据源对话框
      console.log('打开添加数据源对话框');
    },
    
    async openEditDataSourceDialog(source) {
      // 模拟打开编辑数据源对话框
      console.log('打开编辑数据源对话框', source);
    },
    
    async toggleDataSourceActive(id) {
      try {
        const source = this.dataSources.find(s => s.id === id);
        if (!source) return;
        
        const isActive = !source.is_active;
        await ApiService.toggleDataSourceActive(id, isActive);
        source.is_active = isActive;
        
      } catch (error) {
        console.error('Failed to toggle source active status:', error);
        this.error = error.response?.data?.detail || '切换数据源状态失败';
        throw error;
      }
    },
    
    async deleteDataSource(id) {
      try {
        await ApiService.deleteDataSource(id);
        this.dataSources = this.dataSources.filter(source => source.id !== id);
        
      } catch (error) {
        console.error('Failed to delete data source:', error);
        this.error = error.response?.data?.detail || '删除数据源失败';
        throw error;
      }
    },
    
    async openAddDataTableDialog() {
      // 模拟打开添加数据表对话框
      console.log('打开添加数据表对话框');
    },
    
    async openEditDataTableDialog(table) {
      // 模拟打开编辑数据表对话框
      console.log('打开编辑数据表对话框', table);
    },
    
    async openTableFieldsDialog(table) {
      // 模拟打开表字段对话框
      console.log('打开表字段对话框', table);
    },
    
    async deleteDataTable(id) {
      try {
        await ApiService.deleteDataTable(id);
        this.dataTables = this.dataTables.filter(table => table.id !== id);
        
      } catch (error) {
        console.error('Failed to delete data table:', error);
        this.error = error.response?.data?.detail || '删除数据表失败';
        throw error;
      }
    },
    
    async syncTables() {
      try {
        await ApiService.syncTables();
        // 重新加载数据表
        await this.fetchAllData();
        
      } catch (error) {
        console.error('Failed to sync tables:', error);
        this.error = error.response?.data?.detail || '同步表失败';
        throw error;
      }
    },
    
    async openAddTableRelationDialog() {
      // 模拟打开添加表关联对话框
      console.log('打开添加表关联对话框');
    },
    
    async openEditTableRelationDialog(relation) {
      // 模拟打开编辑表关联对话框
      console.log('打开编辑表关联对话框', relation);
    },
    
    async openTableRelationGraphDialog(relation) {
      // 模拟打开表关联图对话框
      console.log('打开表关联图对话框', relation);
    },
    
    async deleteTableRelation(id) {
      try {
        await ApiService.deleteTableRelation(id);
        this.tableRelations = this.tableRelations.filter(relation => relation.id !== id);
        
      } catch (error) {
        console.error('Failed to delete table relation:', error);
        this.error = error.response?.data?.detail || '删除表关联失败';
        throw error;
      }
    }
  }
});