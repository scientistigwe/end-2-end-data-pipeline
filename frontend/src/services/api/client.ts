// src/services/api/client.ts
import axios from 'axios';
import { API_CONFIG } from './config';
import {
  requestInterceptor,
  requestErrorInterceptor,
  responseInterceptor,
  responseErrorInterceptor
} from './interceptors';

const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add request interceptors
apiClient.interceptors.request.use(
  requestInterceptor,
  requestErrorInterceptor
);

// Add response interceptors
apiClient.interceptors.response.use(
  responseInterceptor,
  responseErrorInterceptor
);

// Helper function to replace URL parameters
const replaceUrlParams = (url: string, params: Record<string, string>) => {
  let finalUrl = url;
  Object.keys(params).forEach(key => {
    finalUrl = finalUrl.replace(`:${key}`, params[key]);
  });
  return finalUrl;
};

// API client wrapper with typed methods
export const createApiClient = () => ({
  get: async <T>(url: string, params?: Record<string, string>) => {
    const finalUrl = params ? replaceUrlParams(url, params) : url;
    return apiClient.get<any, ApiResponse<T>>(finalUrl);
  },

  post: async <T>(url: string, data?: any, params?: Record<string, string>) => {
    const finalUrl = params ? replaceUrlParams(url, params) : url;
    return apiClient.post<any, ApiResponse<T>>(finalUrl, data);
  },

  put: async <T>(url: string, data?: any, params?: Record<string, string>) => {
    const finalUrl = params ? replaceUrlParams(url, params) : url;
    return apiClient.put<any, ApiResponse<T>>(finalUrl, data);
  },

  delete: async <T>(url: string, params?: Record<string, string>) => {
    const finalUrl = params ? replaceUrlParams(url, params) : url;
    return apiClient.delete<any, ApiResponse<T>>(finalUrl);
  }
});

export const api = createApiClient();
