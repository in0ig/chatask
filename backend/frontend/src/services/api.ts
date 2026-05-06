import axios from 'axios';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证头等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// API 服务
export const ApiService = {
  // 会话相关API
  getAllSessions() {
    return apiClient.get('/sessions');
  },
  
  // 数据源相关API
  getDataSources() {
    return apiClient.get('/datasources');
  },
  
  // 数据表相关API
  getDataTables() {
    return apiClient.get('/datatables');
  },
  
  // 表关联相关API
  getTableRelations() {
    return apiClient.get('/table-relations');
  },
  
  // 创建数据源
  createDataSource(data) {
    return apiClient.post('/datasources', data);
  },
  
  // 更新数据源
  updateDataSource(id, data) {
    return apiClient.put(`/datasources/${id}`, data);
  },
  
  // 删除数据源
  deleteDataSource(id) {
    return apiClient.delete(`/datasources/${id}`);
  },
  
  // 激活/停用数据源
  toggleDataSourceActive(id, isActive) {
    return apiClient.patch(`/datasources/${id}/active`, { is_active: isActive });
  },
  
  // 创建数据表
  createDataTable(data) {
    return apiClient.post('/datatables', data);
  },
  
  // 更新数据表
  updateDataTable(id, data) {
    return apiClient.put(`/datatables/${id}`, data);
  },
  
  // 删除数据表
  deleteDataTable(id) {
    return apiClient.delete(`/datatables/${id}`);
  },
  
  // 同步表
  syncTables() {
    return apiClient.post('/datatables/sync');
  },
  
  // 创建表关联
  createTableRelation(data) {
    return apiClient.post('/table-relations', data);
  },
  
  // 更新表关联
  updateTableRelation(id, data) {
    return apiClient.put(`/table-relations/${id}`, data);
  },
  
  // 删除表关联
  deleteTableRelation(id) {
    return apiClient.delete(`/table-relations/${id}`);
  },
};

export default ApiService;