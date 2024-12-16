// src/common/api/client/baseClient.ts
import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  CreateAxiosDefaults,
  AxiosProgressEvent,
  AxiosHeaders,
  InternalAxiosRequestConfig
} from 'axios';
import {
  API_CONFIG,
  ApiRequestConfig,
  ApiResponse, 
  EndpointParams } from '@/common/api/client/config';
import { handleApiError } from '../../utils/errorHandlers';

export class BaseClient {
  protected client: AxiosInstance;
  private cache = new Map<string, { data: any; timestamp: number }>();

  constructor(config?: CreateAxiosDefaults) {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: new AxiosHeaders(API_CONFIG.DEFAULT_HEADERS),
      ...config
    } as CreateAxiosDefaults);

    this.setupInterceptors();
  }

  protected setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        const token = localStorage.getItem('token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        // Handle token refresh
        if (error.response?.status === 401 && !error.config?._retry) {
          error.config._retry = true;
          try {
            const refreshToken = localStorage.getItem('refreshToken');
            const response = await this.client.post(API_CONFIG.ENDPOINTS.AUTH.REFRESH, {
              refreshToken
            });
            
            const { token } = response.data;
            localStorage.setItem('token', token);
            
            error.config.headers['Authorization'] = `Bearer ${token}`;
            return this.client(error.config);
          } catch (refreshError) {
            // Handle refresh token failure
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }
        return Promise.reject(handleApiError(error));
      }
    );
  }

  protected formatEndpoint(endpoint: string, params?: EndpointParams): string {
    if (!params) return endpoint;
    
    let formattedEndpoint = endpoint;
    Object.entries(params).forEach(([key, value]) => {
      formattedEndpoint = formattedEndpoint.replace(`:${key}`, encodeURIComponent(value));
    });
    return formattedEndpoint;
  }

  protected async request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<ApiResponse<T>> {
    try {
      const finalUrl = config?.routeParams ? 
        this.formatEndpoint(endpoint, config.routeParams) : 
        endpoint;

      const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};

      const requestConfig: AxiosRequestConfig = {
        method,
        url: finalUrl,
        data,
        ...axiosConfig,
        onUploadProgress: onUploadProgress as ((progressEvent: AxiosProgressEvent) => void) | undefined
      };

      const response = await this.client.request<ApiResponse<T>>(requestConfig);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  // Convenience methods with caching support
  protected async get<T>(
    endpoint: string, 
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    const { cacheDuration, ...restConfig } = config ?? {};
    
    if (cacheDuration) {
      const cacheKey = `${endpoint}-${JSON.stringify(restConfig)}`;
      const cached = this.cache.get(cacheKey);
      
      if (cached && Date.now() - cached.timestamp < cacheDuration) {
        return cached.data;
      }
      
      const response = await this.request<T>('get', endpoint, restConfig);
      this.cache.set(cacheKey, { data: response, timestamp: Date.now() });
      return response;
    }
    
    return this.request<T>('get', endpoint, restConfig);
  }

  protected async post<T>(
    endpoint: string, 
    data?: unknown, 
    config?: ApiRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('post', endpoint, config, data);
  }

  protected async put<T>(
    endpoint: string, 
    data?: unknown, 
    config?: ApiRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('put', endpoint, config, data);
  }

  protected async delete<T>(
    endpoint: string, 
    config?: ApiRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>('delete', endpoint, config);
  }

  // Cache management methods
  protected clearCache(): void {
    this.cache.clear();
  }

  protected clearCacheEntry(endpoint: string, config?: ApiRequestConfig): void {
    const cacheKey = `${endpoint}-${JSON.stringify(config)}`;
    this.cache.delete(cacheKey);
  }
}

export const baseAxiosClient = new BaseClient();