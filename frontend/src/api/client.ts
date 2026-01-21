/**
 * API Client - Axios Configuration
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// Use relative path to leverage Vite proxy, or fallback to direct API URL
// In development, Vite proxy will forward /api requests to backend
// In production, use full API URL from env or default
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // In development, use relative path to leverage Vite proxy
  if (import.meta.env.DEV) {
    return ''; // Empty string means use current origin, Vite proxy handles /api
  }
  // In production, use default API URL
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// Create Axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for long-running operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available (for future use)
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // If response has success field, return data directly
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data;
    }
    // If response.data exists, return it wrapped in success response
    if (response.data) {
      return {
        success: true,
        data: response.data,
      };
    }
    return response;
  },
  (error: AxiosError) => {
    // Handle errors
    if (error.response) {
      // Server responded with error status
      const errorData = error.response.data as any;
      
      if (errorData && typeof errorData === 'object') {
        // API error format
        const errorMessage = errorData.message || errorData.error || '请求失败';
        const apiError = new Error(errorMessage);
        (apiError as any).code = errorData.error || 'UNKNOWN_ERROR';
        (apiError as any).status = error.response.status;
        (apiError as any).error_id = errorData.error_id;  // 保存错误ID
        (apiError as any).data = errorData.data;
        (apiError as any).detail = errorData.detail;  // 保存detail信息（用于友好错误提示）
        (apiError as any).response = error.response;  // 保存完整响应以便前端处理
        return Promise.reject(apiError);
      }
      
      // Generic HTTP error
      const httpError = new Error(error.message || '请求失败');
      (httpError as any).status = error.response.status;
      return Promise.reject(httpError);
    } else if (error.request) {
      // Request made but no response
      const networkError = new Error('网络错误，请检查网络连接');
      (networkError as any).isNetworkError = true;
      return Promise.reject(networkError);
    } else {
      // Error setting up request
      return Promise.reject(error);
    }
  }
);

export default apiClient;
