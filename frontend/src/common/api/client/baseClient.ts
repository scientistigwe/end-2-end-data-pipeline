import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  CreateAxiosDefaults,
  AxiosHeaders,
  InternalAxiosRequestConfig,
  RawAxiosRequestHeaders,
  AxiosResponse
} from 'axios';

import { 
  APIRoutes,
  RouteHelper,
  RouteParams,
  RouteKey,
  SubRouteKey,
  NestedRouteKey,
  RouteConfig,
  getRoutePath
} from '../routes';

import { 
  ApiRequestConfig,
  ApiResponse,
  HttpMethod,
  HTTP_STATUS,
  ApiErrorResponse,
  RetryableRequestConfig,
  CacheEntry,
  HeadersType,
  RetryStatus
} from '../../types/api';

import { 
  API_CONFIG, 
  DEFAULT_REQUEST_CONFIG,
  RETRY_CONFIG,
} from './config';
import { logger } from '@/common/utils/logger';

export enum ServiceType {
  AUTH = 'auth',
  DECISIONS = 'decisions',
  REPORTS = 'reports',
  DATA_SOURCES = 'data-sources',
  PIPELINE = 'pipeline',
  MONITORING = 'monitoring',
  ANALYSIS = 'analysis',
  SETTINGS = 'settings',
  RECOMMENDATIONS = 'recommendations'
}

interface ServiceConfig {
  service: ServiceType;
  headers?: Record<string, string>;
}

interface RefreshQueueItem {
  resolve: (value: unknown) => void;
  reject: (error: unknown) => void;
}

export class BaseClient {
  private static instance: BaseClient | null = null;
  private isRefreshing: boolean = false;
  private refreshQueue: RefreshQueueItem[] = [];
  protected client: AxiosInstance;
  private serviceConfigs: Map<string, ServiceConfig> = new Map();
  private cache: Map<string, CacheEntry<any>>;
  private retryConfig = RETRY_CONFIG;

  private constructor(config?: CreateAxiosDefaults) {
    this.cache = new Map();
    this.client = this.initializeClient(config);
    this.setupInterceptors();
  }

  public getAxiosInstance(): AxiosInstance {
    return this.client;
}

  public static getInstance(config?: CreateAxiosDefaults): BaseClient {
    if (!BaseClient.instance) {
      BaseClient.instance = new BaseClient(config);
    }
    return BaseClient.instance;
  }

  // Request Methods
  public async executeGet<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    try {
      const response = await this.get<T>(endpoint, config);
      return { success: true, data: response };
    } catch (error) {
      if (error instanceof Error) {
        return {
          success: false,
          data: {} as T,
          message: error.message,
          error: { code: 'REQUEST_FAILED', message: error.message }
        };
      }
      throw error;
    }
  }

  public async executePost<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.post<T>(endpoint, data, config);
  }

  public async executePut<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.put<T>(endpoint, data, config);
  }

  public async executePatch<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.patch<T>(endpoint, data, config);
  }

  public async executeDelete<T>(
    endpoint: string,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.delete<T>(endpoint, config);
  }

  // Route Methods
  public createRoute<T extends RouteKey>(
    module: T,
    route: SubRouteKey<T>,
    params?: RouteParams
  ): string {
    return this.getRoute(module, route, params);
  }

  protected getRoute<T extends RouteKey>(
    module: T,
    route: SubRouteKey<T>,
    params?: RouteParams
  ): string {
    return RouteHelper.getRoute(module, route, params);
  }

  // Configuration Methods
  public setServiceConfig(config: ServiceConfig): void {
    if (!config.service) {
      logger.warn('Attempting to set service config without service type');
      return;
    }
    
    this.serviceConfigs.set(config.service, {
      service: config.service,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(config.headers || {})
      }
    });
  }

  private initializeClient(config?: CreateAxiosDefaults): AxiosInstance {
    const defaultHeaders: HeadersType = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    const clientConfig: CreateAxiosDefaults = {
      baseURL: API_CONFIG.FULL_BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: defaultHeaders,
      withCredentials: true,
      validateStatus: (status: number): boolean => 
        status >= HTTP_STATUS.OK && status < HTTP_STATUS.MULTIPLE_CHOICES,
      ...DEFAULT_REQUEST_CONFIG,
      ...config
    };

    return axios.create(clientConfig);
  }

  // Interceptor Setup
  private setupInterceptors(): void {
    this.setupRequestInterceptor();
    this.setupResponseInterceptor();
  }

  private setupRequestInterceptor(): void {
    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const headers = new AxiosHeaders(config.headers);
      const url = config.url || '';
      const serviceType = this.getServiceForRequest(url);
      
      headers.set('Accept', 'application/json');
      headers.set('Content-Type', 'application/json');
      
      if (serviceType) {
        headers.set('X-Service', serviceType);
      }

      config.withCredentials = true;
      config.headers = headers;
      
      return config;
    });
  }

  private setupResponseInterceptor(): void {
    this.client.interceptors.response.use(
      response => response,
      async error => {
        if (!axios.isAxiosError(error) || !error.config) {
          return Promise.reject(error);
        }

        const config = error.config as RetryableRequestConfig;
        
        // Don't retry if it's a refresh request or already retried
        if (this.isRefreshRequest(config.url) || config._retry) {
          if (error.response?.status === HTTP_STATUS.UNAUTHORIZED) {
            this.handleAuthenticationFailure();
          }
          return Promise.reject(error);
        }

        if (error.response?.status === HTTP_STATUS.UNAUTHORIZED) {
          return this.handleUnauthorizedError(config, error);
        }

        return Promise.reject(error);
      }
    );
  }

  // Auth Handling
  private async handleUnauthorizedError(config: RetryableRequestConfig, error: any) {
    config._retry = true;

    if (this.isRefreshing) {
      try {
        await this.enqueueRefreshRequest();
        return this.client(config);
      } catch (error) {
        return Promise.reject(error);
      }
    }

    try {
      this.isRefreshing = true;
      await this.refreshAuthentication();
      this.processRefreshQueue(null);
      return this.client(config);
    } catch (error) {
      this.processRefreshQueue(error);
      this.handleAuthenticationFailure();
      return Promise.reject(error);
    } finally {
      this.isRefreshing = false;
    }
  }

  private async refreshAuthentication(): Promise<void> {
    try {
      await this.executePost(
        RouteHelper.getRoute('AUTH', 'REFRESH'),
        undefined,
        {
          withCredentials: true,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        }
      );
    } catch (error) {
      logger.error('Refresh authentication failed:', error);
      throw error;
    }
  }

  private enqueueRefreshRequest(): Promise<unknown> {
    return new Promise((resolve, reject) => {
      this.refreshQueue.push({ resolve, reject });
    });
  }

  private processRefreshQueue(error: any): void {
    if (error) {
      this.refreshQueue.forEach(promise => promise.reject(error));
    } else {
      this.refreshQueue.forEach(promise => promise.resolve(null));
    }
    this.refreshQueue = [];
  }

  private handleAuthenticationFailure(): void {
    this.clearAuthenticationState();
    this.processRefreshQueue(new Error('Authentication failed'));
    window.dispatchEvent(new Event('auth:sessionExpired'));
  }

  private clearAuthenticationState(): void {
    this.cache.clear();
    window.dispatchEvent(new Event('auth:logout'));
  }

  // Helper Methods
  private isRefreshRequest(url?: string): boolean {
    return url?.includes('/auth/refresh') || false;
  }

  private getServiceForRequest(url: string): ServiceType | undefined {
    if (url.startsWith('auth/')) return ServiceType.AUTH;
    if (url.startsWith('pipelines')) return ServiceType.PIPELINE;
    // ... other service types
    return undefined;
  }

  // HTTP Methods Implementation
  private async request<T>(
    method: HttpMethod,
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<T> {
    try {
      const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};
      
      const cleanEndpoint = endpoint.replace(/^\/+/, '');
      const normalizedEndpoint = cleanEndpoint.replace(/^api\/v1\//, '');

      const requestConfig: AxiosRequestConfig = {
        method: method.toLowerCase(),
        url: normalizedEndpoint,
        data,
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...(axiosConfig?.headers || {})
        },
        ...axiosConfig,
        onUploadProgress
      };

      const response = await this.client.request(requestConfig);
      return response.data?.data ?? response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  private async get<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<T> {
    const { cacheDuration = 0, ...restConfig } = config ?? {};
    
    if (cacheDuration > 0) {
      const cached = this.getFromCache<T>(endpoint, restConfig, cacheDuration);
      if (cached) return cached;
    }

    const response = await this.request<T>('GET', endpoint, restConfig);
    
    if (cacheDuration > 0) {
      this.setCache(endpoint, restConfig, response);
    }

    return response;
  }

  private post<T>(endpoint: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('POST', endpoint, config, data);
  }

  private put<T>(endpoint: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('PUT', endpoint, config, data);
  }

  private patch<T>(endpoint: string, data?: unknown, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('PATCH', endpoint, config, data);
  }

  private delete<T>(endpoint: string, config?: ApiRequestConfig): Promise<T> {
    return this.request<T>('DELETE', endpoint, config);
  }

  // Error Handling
  private handleApiError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        return new Error(
          error.message.includes('Network Error')
            ? 'Unable to connect to the server. Please check your connection.'
            : 'Network error: Please check your connection'
        );
      }

      const errorResponse = error.response.data as ApiErrorResponse;
      logger.error('API Error:', {
        status: error.response.status,
        data: errorResponse,
        headers: error.response.headers
      });

      switch (error.response.status) {
        case HTTP_STATUS.UNAUTHORIZED:
          return new Error('Authentication failed. Please log in again.');
        case HTTP_STATUS.FORBIDDEN:
          return new Error('You do not have permission to perform this action.');
        case HTTP_STATUS.NOT_FOUND:
          return new Error('The requested resource was not found.');
        case HTTP_STATUS.BAD_REQUEST:
          return new Error(errorResponse?.message || 'Invalid request');
        default:
          return new Error(
            errorResponse?.error?.message || 
            errorResponse?.message || 
            error.message || 
            'An unexpected error occurred'
          );
      }
    }

    return error instanceof Error ? error : new Error('An unexpected error occurred');
  }
}

export const baseAxiosClient = BaseClient.getInstance();