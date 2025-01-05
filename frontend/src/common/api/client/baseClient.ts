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
  ErrorResponse,
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


export class BaseClient {
  private static instance: BaseClient | null = null;
  private static isRefreshing: boolean = false;
  protected client: AxiosInstance;
  private serviceConfigs: Map<string, ServiceConfig> = new Map();
  private cache: Map<string, CacheEntry<any>>;
  private retryConfig = RETRY_CONFIG;

  private constructor(config?: CreateAxiosDefaults) {
    this.cache = new Map();
    this.client = this.initializeClient(config);
    this.setupInterceptors();
  }

  public createRoute<T extends RouteKey>(
    module: T,
    route: SubRouteKey<T>,
    params?: RouteParams
  ): string {
    return this.getRoute(module, route, params);
  }

  public createNestedRoute<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T],
    R extends NestedRouteKey<T, S>
  >(
    module: T,
    section: S,
    route: R,
    params?: RouteParams
  ): string {
    return this.getNestedRoute(module, section, route, params);
  }

  // Protected Methods
  protected getRoute<T extends RouteKey>(
    module: T,
    route: SubRouteKey<T>,
    params?: RouteParams
  ): string {
    return RouteHelper.getRoute(module, route, params);
  }

  protected getNestedRoute<
    T extends RouteKey,
    S extends keyof typeof APIRoutes[T],
    R extends NestedRouteKey<T, S>
  >(
    module: T,
    section: S,
    route: R,
    params?: RouteParams
  ): string {
    return RouteHelper.getNestedRoute(module, section, route, params);
  }

  public static getInstance(config?: CreateAxiosDefaults): BaseClient {
    if (!BaseClient.instance) {
      BaseClient.instance = new BaseClient(config);
    }
    return BaseClient.instance;
  }

  public setDefaultHeaders(headers: Record<string, string>): void {
    Object.entries(headers).forEach(([key, value]) => {
      if (this.client.defaults.headers.common) {
        this.client.defaults.headers.common[key] = value;
      }
    });
  }

  public setServiceConfig(config: ServiceConfig): void {
    if (!config.service) {
      console.warn('Attempting to set service config without service type');
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

  public getAxiosInstance(): AxiosInstance {
    return this.client;
  }

  public clearCache(): void {
    this.cache.clear();
  }

  // Public API Methods
  public async executeGet<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    const response = await this.get<T>(endpoint, config);
    return {
      data: response,
      status: HTTP_STATUS.OK,
      message: undefined
    };
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

  // Protected Methods
  protected async request<T>(
    method: HttpMethod,
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<T> {
    try {
      const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};
      
      const cleanEndpoint = endpoint.replace(/^\/+/, '');
      const normalizedEndpoint = cleanEndpoint.replace(/^api\/v1\//, '');

      const headers: RawAxiosRequestHeaders = {
        ...(axiosConfig?.headers as RawAxiosRequestHeaders || {}),
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      };

      const requestConfig: AxiosRequestConfig = {
        method: method.toLowerCase(),
        url: normalizedEndpoint,
        data,
        withCredentials: true,
        ...axiosConfig,
        headers,
        onUploadProgress
      };

      const response = await this.client.request(requestConfig);
      return response.data?.data ?? response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // Private Methods
  private initializeClient(config?: CreateAxiosDefaults): AxiosInstance {
    const defaultHeaders: HeadersType = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };

    const clientConfig: CreateAxiosDefaults = {
      baseURL: API_CONFIG.FULL_BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: defaultHeaders,
      withCredentials: true,
      validateStatus: (status: number): boolean => {
        return status >= HTTP_STATUS.OK && status < HTTP_STATUS.MULTIPLE_CHOICES;
      },
      ...DEFAULT_REQUEST_CONFIG,
      ...config
    };

    return axios.create(clientConfig);
  }

  private setupInterceptors(): void {
    this.setupRequestInterceptor();
    this.setupResponseInterceptor();
  }

  private setupRequestInterceptor(): void {
    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const headers = new AxiosHeaders(config.headers);
      
      // Always ensure withCredentials is true for cookie handling
      config.withCredentials = true;

      // Add service-specific headers
      const url = config.url || '';
      const serviceType = this.getServiceForRequest(url);
      const serviceConfig = serviceType ? this.serviceConfigs.get(serviceType) : undefined;

      if (serviceConfig) {
        headers.set('X-Service', serviceConfig.service);
        
        if (serviceConfig.headers) {
          Object.entries(serviceConfig.headers).forEach(([key, value]) => {
            headers.set(key, value);
          });
        }
      }

      config.headers = headers;
      return config;
    });
  }

  private setupResponseInterceptor(): void {
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: unknown) => {
        if (!axios.isAxiosError(error) || !error.config) {
          return Promise.reject(error);
        }

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

  private async handleTokenRefresh(error: unknown): Promise<AxiosResponse> {
    if (!axios.isAxiosError(error)) {
      throw error;
    }

    if (BaseClient.isRefreshing) {
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          if (error.config) {
            resolve(this.client(error.config));
          } else {
            reject(new Error('Invalid error configuration'));
          }
        }, 1000);
      });
    }

    try {
      BaseClient.isRefreshing = true;
      
      // Call refresh endpoint - tokens handled by HTTP-only cookies
      await this.request<void>(
        'POST',
        'auth/refresh',
        { withCredentials: true }
      );

      if (error.config) {
        return this.client(error.config);
      }
      
      throw new Error('Invalid error configuration');
    } catch (refreshError) {
      window.dispatchEvent(new Event('auth:sessionExpired'));
      throw refreshError;
    } finally {
      BaseClient.isRefreshing = false;
    }
  }

  private shouldRefreshToken(error: unknown): boolean {
    if (!axios.isAxiosError(error)) return false;
    
    const config = error.config as RetryableRequestConfig;
    const isRefreshRequest = config?.url?.includes('auth/refresh');
    
    return (
      error.response?.status === HTTP_STATUS.UNAUTHORIZED && 
      !isRefreshRequest &&
      !(config?._retry ?? 0)
    );
  }

  private shouldRetryRequest(error: unknown): boolean {
    if (!axios.isAxiosError(error)) return false;
    
    const config = error.config as RetryableRequestConfig;
    const retryCount = config?._retry ?? 0;
    const status = error.response?.status as RetryStatus;
    const method = (error.config?.method?.toUpperCase() ?? '') as HttpMethod;

    return !!(
      status &&
      method &&
      retryCount < this.retryConfig.count &&
      this.retryConfig.statuses.includes(status) &&
      (!this.retryConfig.methods || this.retryConfig.methods.includes(method))
    );
  }

  private async handleRequestRetry(error: unknown): Promise<AxiosResponse> {
    if (!axios.isAxiosError(error) || !error.config) {
      throw error;
    }

    const config = error.config as RetryableRequestConfig;
    config._retry = (config._retry ?? 0) + 1;
    
    const delay = Math.min(
      this.retryConfig.delay * Math.pow(this.retryConfig.backoffFactor || 2, config._retry - 1),
      this.retryConfig.maxDelay || 30000
    );
    
    await new Promise(resolve => setTimeout(resolve, delay));
    return this.client(config);
  }

  private handleApiError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        return new Error('Network error: Please check your connection');
      }

      const errorResponse = error.response.data as ErrorResponse;
      console.error('API Error:', errorResponse);

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

  private getServiceForRequest(url: string): ServiceType | undefined {
    if (url.startsWith('auth/')) return ServiceType.AUTH;
    if (url.startsWith('pipelines')) return ServiceType.PIPELINE;
    if (url.startsWith('data-sources')) return ServiceType.DATA_SOURCES;
    if (url.startsWith('decisions')) return ServiceType.DECISIONS;
    if (url.startsWith('reports')) return ServiceType.REPORTS;
    if (url.startsWith('monitoring')) return ServiceType.MONITORING;
    if (url.startsWith('analysis')) return ServiceType.ANALYSIS;
    if (url.startsWith('settings')) return ServiceType.SETTINGS;
    if (url.startsWith('recommendations')) return ServiceType.RECOMMENDATIONS;
    return undefined;
  }

  // HTTP Methods
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

  private async post<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('POST', endpoint, config, data);
  }

  private async put<T>(
    endpoint: string,
    data?: unknown, 
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('PUT', endpoint, config, data);
  }

  private async patch<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('PATCH', endpoint, config, data);
  }

  private async delete<T>(
    endpoint: string,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('DELETE', endpoint, config);
  }

  // Cache Methods
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
}

export const baseAxiosClient = BaseClient.getInstance();