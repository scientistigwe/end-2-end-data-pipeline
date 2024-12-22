// src/common/api/client/baseClient.ts
import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  CreateAxiosDefaults,
  AxiosHeaders,
  InternalAxiosRequestConfig,
  AxiosHeaderValue,
  RawAxiosRequestHeaders
} from 'axios';

import { 
  API_CONFIG, 
  ApiRequestConfig, 
  ApiResponse,
  DEFAULT_REQUEST_CONFIG,
  RETRY_CONFIG,
  ENV_CONFIG
} from './config';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

type HeadersType = Record<string, AxiosHeaderValue>;

export class BaseClient {
  protected client: AxiosInstance;
  private cache: Map<string, CacheEntry<any>>;

  constructor(config?: CreateAxiosDefaults) {
    this.cache = new Map();
    this.client = this.initializeClient(config);
    this.setupInterceptors();
  }

  private initializeClient(config?: CreateAxiosDefaults): AxiosInstance {
    const defaultHeaders: HeadersType = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };

    const baseURL = `${ENV_CONFIG.apiUrl}/api/${API_CONFIG.VERSION}`;

    return axios.create({
      baseURL,
      timeout: API_CONFIG.TIMEOUT,
      headers: defaultHeaders,
      withCredentials: true,
      validateStatus: (status) => status >= 200 && status < 300,
      ...DEFAULT_REQUEST_CONFIG,
      ...config
    });
  }

  protected async request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<T> {
    try {
      const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};
      
      const headers: RawAxiosRequestHeaders = {
        ...(axiosConfig?.headers as RawAxiosRequestHeaders || {}),
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      };

      const requestConfig: AxiosRequestConfig = {
        method,
        url: endpoint,
        data,
        ...axiosConfig,
        headers,
        onUploadProgress
      };

      const response = await this.client.request<ApiResponse<T>>(requestConfig);
      return response.data.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }
  private setupInterceptors(): void {
    this.setupRequestInterceptor();
    this.setupResponseInterceptor();
  }

  private setupRequestInterceptor(): void {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('token');
        const headers = new AxiosHeaders(config.headers);

        if (token) {
          headers.set('Authorization', `Bearer ${token}`);
        }

        config.headers = headers;
        return config;
      },
      (error) => Promise.reject(error)
    );
  }

  private setupResponseInterceptor(): void {
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (!error.config) return Promise.reject(error);

        if (this.shouldRefreshToken(error)) {
          return this.handleTokenRefresh(error);
        }

        if (this.shouldRetryRequest(error)) {
          return this.handleRequestRetry(error);
        }

        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private shouldRefreshToken(error: any): boolean {
    return (
      error.response?.status === 401 && 
      !error.config?._retry &&
      !!localStorage.getItem('refreshToken')
    );
  }

  private async handleTokenRefresh(error: any): Promise<any> {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      const response = await this.client.post<ApiResponse<{ token: string }>>('/auth/refresh', { refreshToken });
      const { token } = response.data.data;

      localStorage.setItem('token', token);
      error.config.headers = new AxiosHeaders({
        ...error.config.headers,
        Authorization: `Bearer ${token}`
      });

      return this.client(error.config);
    } catch (refreshError) {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      window.location.href = '/login';
      return Promise.reject(refreshError);
    }
  }

  private shouldRetryRequest(error: any): boolean {
    const retryCount = error.config?._retry || 0;
    return (
      retryCount < RETRY_CONFIG.count &&
      RETRY_CONFIG.statuses.includes(error.response?.status)
    );
  }

  private async handleRequestRetry(error: any): Promise<any> {
    error.config._retry = (error.config._retry || 0) + 1;
    const delay = RETRY_CONFIG.delay * Math.pow(2, error.config._retry - 1);
    await new Promise(resolve => setTimeout(resolve, delay));
    return this.client(error.config);
  }

  private handleApiError(error: any): Error {
    if (axios.isAxiosError(error)) {
      return new Error(error.response?.data?.message || error.message);
    }
    return error;
  }

  protected async get<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<T> {
    const { cacheDuration = 0, ...restConfig } = config ?? {};

    if (cacheDuration > 0) {
      const cached = this.getFromCache<T>(endpoint, restConfig, cacheDuration);
      if (cached) return cached;
    }

    const response = await this.request<T>('get', endpoint, restConfig);
    
    if (cacheDuration > 0) {
      this.setCache(endpoint, restConfig, response);
    }

    return response;
  }

  private getFromCache<T>(
    endpoint: string, 
    config: ApiRequestConfig, 
    duration: number
  ): T | null {
    const cacheKey = this.getCacheKey(endpoint, config);
    const cached = this.cache.get(cacheKey);
    
    if (cached && (Date.now() - cached.timestamp) < duration) {
      return cached.data;
    }

    return null;
  }

  private setCache<T>(
    endpoint: string, 
    config: ApiRequestConfig, 
    data: T
  ): void {
    const cacheKey = this.getCacheKey(endpoint, config);
    this.cache.set(cacheKey, { data, timestamp: Date.now() });
  }

  private getCacheKey(endpoint: string, config?: ApiRequestConfig): string {
    return `${endpoint}-${JSON.stringify(config)}`;
  }

  protected async post<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('post', endpoint, config, data);
  }

  protected async put<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('put', endpoint, config, data);
  }

  protected async delete<T>(
    endpoint: string,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('delete', endpoint, config);
  }

  public clearCache(): void {
    this.cache.clear();
  }
}

export const baseAxiosClient = new BaseClient();