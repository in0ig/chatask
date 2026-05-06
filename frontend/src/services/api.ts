import axios from 'axios';

// 创建axios实例
const service = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 在发送请求之前做些什么
    console.log('Request:', config);
    
    // 添加认证头
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 参数验证
    if (config.method?.toUpperCase() === 'POST' || config.method?.toUpperCase() === 'PUT') {
      if (config.data && typeof config.data === 'object') {
        // 验证必填字段 - 只对创建和更新数据源的请求进行验证，不包括测试连接
        if (config.url?.includes('/datasources') && 
            !config.url?.includes('/datasources/test') && 
            config.data.name === undefined) {
          throw new Error('数据源名称不能为空');
        }
        // 注意：只对创建表的请求验证 sourceId，不对更新请求验证
        if (config.url?.includes('/tables') && config.method?.toUpperCase() === 'POST' && config.data.sourceId === undefined) {
          throw new Error('数据源ID不能为空');
        }
      }
    }
    
    return config;
  },
  (error) => {
    // 对请求错误做些什么
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    // 对响应数据做点什么
    console.log('Response:', response);
    
    // 数据转换：统一处理响应格式
    if (response.data && response.data.code !== undefined) {
      // 如果返回的是标准格式 {code: 200, data: ..., message: ''}
      if (response.data.code === 200) {
        return response.data.data;
      } else {
        // 业务错误
        throw new Error(response.data.message || '请求失败');
      }
    }
    
    // 如果没有code字段，直接返回数据
    return response.data;
  },
  (error) => {
    // 对响应错误做点什么
    console.error('Response error:', error);
    
    // 网络错误
    if (!error.response) {
      return Promise.reject(new Error('网络连接失败，请检查网络设置'));
    }
    
    // 认证错误
    if (error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      return Promise.reject(new Error('登录已过期，请重新登录'));
    }
    
    // 业务错误
    if (error.response.data && error.response.data.message) {
      return Promise.reject(new Error(error.response.data.message));
    }
    
    // 默认错误
    return Promise.reject(new Error('请求失败'));
  }
);

export default service;

// Knowledge Base API
export const knowledgeBaseApi = {
  getKnowledgeBases: () => service.get('/knowledge-bases'),
  createKnowledgeBase: (data) => service.post('/knowledge-bases', data),
  updateKnowledgeBase: (id, data) => service.put(`/knowledge-bases/${id}`, data),
  deleteKnowledgeBase: (id) => service.delete(`/knowledge-bases/${id}`)
};

// Knowledge Item API
export const knowledgeItemApi = {
  getItemsByKnowledgeBase: (knowledgeBaseId) => service.get(`/knowledge-items/knowledge-base/${knowledgeBaseId}/items`),
  createKnowledgeItem: (data) => service.post('/knowledge-items', data),
  updateKnowledgeItem: (id, data) => service.put(`/knowledge-items/${id}`, data),
  deleteKnowledgeItem: (id) => service.delete(`/knowledge-items/${id}`)
};

// 表关联 API
export const tableRelationApi = {
  getAll: (params?: Record<string, any>) => service.get('/table-relations', { params }),
  get: (id: number) => service.get(`/table-relations/${id}`),
  create: (data: any) => service.post('/table-relations', data),
  update: (id: number, data: any) => service.put(`/table-relations/${id}`, data),
  delete: (id: number) => service.delete(`/table-relations/${id}`)
};
