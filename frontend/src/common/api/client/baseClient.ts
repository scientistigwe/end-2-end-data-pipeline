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

export class BaseClient {
  private static instance: BaseClient | null = null;
  protected client: AxiosInstance;
  private cache: Map<string, CacheEntry<any>>;
  private retryConfig = RETRY_CONFIG;

  private constructor(config?: CreateAxiosDefaults) {
    this.cache = new Map();
    this.client = this.initializeClient(config);
    this.setupInterceptors();
  }

  public static getInstance(config?: CreateAxiosDefaults): BaseClient {
    if (!BaseClient.instance) {
      BaseClient.instance = new BaseClient(config);
    }
    return BaseClient.instance;
  }

  // Public Methods for API Consumers
  public setDefaultHeaders(headers: Record<string, string>): void {
    Object.entries(headers).forEach(([key, value]) => {
      if (this.client.defaults.headers.common) {
        this.client.defaults.headers.common[key] = value;
      }
    });
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

  // Public HTTP Methods
  public async executeGet<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<T> {
    return this.get<T>(endpoint, config);
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

  public clearCache(): void {
    this.cache.clear();
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

  public getAxiosInstance(): AxiosInstance {
    return this.client;
  }

  protected resolveRoute<T extends RouteKey>(
    config: RouteConfig<T>
  ): string {
    return getRoutePath(config);
  }

  protected async request<T>(
    method: HttpMethod,
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
): Promise<T> {
    try {
        const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};
        
        // Remove any leading slash to prevent double slashes
        const cleanEndpoint = endpoint.replace(/^\/+/, '');
        
        // Remove duplicate api/v1 if it exists in the endpoint
        const normalizedEndpoint = cleanEndpoint.replace(/^api\/v1\//, '');

        const headers: RawAxiosRequestHeaders = {
            ...(axiosConfig?.headers as RawAxiosRequestHeaders || {}),
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        };

        const requestConfig: AxiosRequestConfig = {
            method: method.toLowerCase(),
            url: normalizedEndpoint, // Use the normalized endpoint
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

    console.log('Initializing API client with config:', clientConfig);
    return axios.create(clientConfig);
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
        
        console.log('Making request:', {
          method: config.method,
          url: config.url,
          baseURL: config.baseURL,
          headers: config.headers
        });
        
        return config;
      },
      (error: Error) => Promise.reject(error)
    );
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

  private shouldRefreshToken(error: unknown): boolean {
    if (!axios.isAxiosError(error)) return false;
    
    const config = error.config as RetryableRequestConfig;
    return (
      error.response?.status === HTTP_STATUS.UNAUTHORIZED && 
      !(config?._retry ?? 0) &&
      !!localStorage.getItem('refreshToken')
    );
  }

  private async handleTokenRefresh(error: unknown): Promise<AxiosResponse> {
    if (!axios.isAxiosError(error)) {
      throw error;
    }

    try {
      const refreshToken = localStorage.getItem('refreshToken');
      const response = await this.request<{ token: string }>(
        'POST',
        this.createRoute('AUTH', 'REFRESH'),
        undefined,
        { refreshToken }
      );

      const { token } = response;
      localStorage.setItem('token', token);

      if (error.config) {
        const config = error.config as RetryableRequestConfig;
        config.headers = new AxiosHeaders({
          ...config.headers,
          Authorization: `Bearer ${token}`
        });

        return this.client(config);
      }
      
      throw new Error('Invalid error configuration');
    } catch (refreshError) {
      this.handleAuthFailure();
      throw refreshError;
    }
  }

  private handleAuthFailure(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    window.dispatchEvent(new Event('auth:sessionExpired'));
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
    console.error('API Error:', error);
  
    if (axios.isAxiosError(error)) {
      const errorResponse = error.response?.data as ErrorResponse;
      console.log('Full error response:', error.response?.data);
      return new Error(
        errorResponse?.error?.message || 
        errorResponse?.message || 
        error.message || 
        'An unexpected error occurred'
      );
    }

    if (error instanceof Error) {
      return error;
    }

    return new Error('An unexpected error occurred');
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