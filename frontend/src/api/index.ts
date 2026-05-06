import axios from 'axios';
import { dataSourceApi } from './dataSourceApi';
import { dataTableApi } from './dataTableApi';
import { dictionaryApi } from './dictionaryApi';
import { relationApi } from './relationApi';
import { fieldMappingApi } from './fieldMappingApi';

// Export all APIs for unified access
export {
  dataSourceApi,
  dataTableApi,
  dictionaryApi,
  relationApi,
  fieldMappingApi
};

// Initialize axios instance with default configuration
const apiClient = axios.create({
  baseURL: '/api',  // Vite proxy will forward /api/* to backend
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor: Add authentication token and logging
apiClient.interceptors.request.use(
  (config) => {
    // Add authentication token from localStorage
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log request details
    console.log('[API Request]', config.method?.toUpperCase(), config.url, config.data);
    
    // Validate request parameters
    if (config.data && typeof config.data === 'object') {
      // Add parameter validation here as needed
    }
    
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor: Handle responses and errors uniformly
apiClient.interceptors.response.use(
  (response) => {
    // Log response details
    console.log('[API Response]', response.status, response.config.url, response.data);
    
    // Transform response data to consistent format
    if (response.data && response.data.success === false) {
      // Handle business errors
      throw new Error(response.data.message || 'Business error occurred');
    }
    
    // Return the data part of the response
    return response.data;
  },
  (error) => {
    console.error('[API Response Error]', error);
    
    // Handle different types of errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Authentication error
          localStorage.removeItem('authToken');
          window.location.href = '/login';
          return Promise.reject(new Error('Authentication failed. Please log in again.'));
        case 403:
          // Authorization error
          return Promise.reject(new Error('Access denied. You do not have permission to perform this action.'));
        case 404:
          return Promise.reject(new Error('Resource not found.'));
        case 500:
          return Promise.reject(new Error('Server error. Please try again later.'));
        default:
          return Promise.reject(new Error(data?.message || 'An error occurred'));
      }
    } else if (error.request) {
      // Network error (no response received)
      return Promise.reject(new Error('Network error. Please check your connection.'));
    } else {
      // Other errors
      return Promise.reject(new Error(error.message || 'Unknown error occurred'));
    }
  }
);

// Export the configured axios instance for direct use if needed
export { apiClient };