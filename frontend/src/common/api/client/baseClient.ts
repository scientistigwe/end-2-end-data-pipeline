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
  NestedRouteKey
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
  AUTH = 'AUTH',
  DECISIONS = 'DECISIONS',
  REPORTS = 'REPORTS',
  DATA_SOURCES = 'DATA_SOURCES',
  PIPELINES = 'PIPELINES',
  MONITORING = 'MONITORING',
  ANALYTICS = 'ANALYTICS',
  SETTINGS = 'SETTINGS',
  RECOMMENDATIONS = 'RECOMMENDATIONS',
  STAGING = 'STAGING'
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
  private serviceConfigs: Map<ServiceType, ServiceConfig> = new Map();
  private cache: Map<string, CacheEntry<any>> = new Map();
  private retryConfig = RETRY_CONFIG;
  private static requestCounter = 0;
  private inFlightRequests = new Map<string, Promise<any>>();

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

  // Type-safe request methods that integrate with APIRoutes
  public async get<T>(
    module: RouteKey,
    route: SubRouteKey<typeof module>,
    params?: RouteParams,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    const endpoint = RouteHelper.getRoute(module, route, params);
    return this.executeGet<T>(endpoint, config);
  }

  public async post<T>(
    module: RouteKey,
    route: SubRouteKey<typeof module>,
    data?: unknown,
    params?: RouteParams,
    config?: ApiRequestConfig
  ): Promise<T> {
    const endpoint = RouteHelper.getRoute(module, route, params);
    return this.executePost<T>(endpoint, data, config);
  }

  public async put<T>(
    module: RouteKey,
    route: SubRouteKey<typeof module>,
    data?: unknown,
    params?: RouteParams,
    config?: ApiRequestConfig
  ): Promise<T> {
    const endpoint = RouteHelper.getRoute(module, route, params);
    return this.executePut<T>(endpoint, data, config);
  }

  public async delete<T>(
    module: RouteKey,
    route: SubRouteKey<typeof module>,
    params?: RouteParams,
    config?: ApiRequestConfig
  ): Promise<T> {
    const endpoint = RouteHelper.getRoute(module, route, params);
    return this.executeDelete<T>(endpoint, config);
  }

  // Type-safe nested route request methods
  public async getFromNested<T, M extends RouteKey, S extends SubRouteKey<M>, R extends NestedRouteKey<M, S>>(
    module: M,
    section: S,
    route: R,
    params?: RouteParams,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    const endpoint = RouteHelper.getNestedRoute(module, section, route, params);
    return this.executeGet<T>(endpoint, config);
  }

  public async postToNested<T, M extends RouteKey, S extends SubRouteKey<M>, R extends NestedRouteKey<M, S>>(
    module: M,
    section: S,
    route: R,
    data?: unknown,
    params?: RouteParams,
    config?: ApiRequestConfig
  ): Promise<T> {
    const endpoint = RouteHelper.getNestedRoute(module, section, route, params);
    return this.executePost<T>(endpoint, data, config);
  }

  // Base request execution methods
  public async executeGet<T>(
    endpoint: string,
    config?: ApiRequestConfig & { cacheDuration?: number }
  ): Promise<ApiResponse<T>> {
    try {
      const { cacheDuration = 0, ...restConfig } = config ?? {};
      
      if (cacheDuration > 0) {
        const cached = this.getFromCache<T>(endpoint, restConfig);
        if (cached) return { success: true, data: cached };
      }

      const response = await this.request<T>('GET', endpoint, restConfig);
      
      if (cacheDuration > 0) {
        this.setCache(endpoint, response, cacheDuration);
      }

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
    return this.request<T>('POST', endpoint, config, data);
  }

  public async executePut<T>(
    endpoint: string,
    data?: unknown,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('PUT', endpoint, config, data);
  }

  public async executeDelete<T>(
    endpoint: string,
    config?: ApiRequestConfig
  ): Promise<T> {
    return this.request<T>('DELETE', endpoint, config);
  }

  // Cache management
  private getFromCache<T>(endpoint: string, config?: ApiRequestConfig): T | null {
    const cacheKey = this.getCacheKey(endpoint, config);
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() < cached.expiresAt) {
      return cached.data;
    }
    
    this.cache.delete(cacheKey);
    return null;
  }

  private setCache<T>(endpoint: string, data: T, duration: number): void {
    const cacheKey = this.getCacheKey(endpoint);
    this.cache.set(cacheKey, {
      data,
      expiresAt: Date.now() + duration * 1000
    });
  }

  private getCacheKey(endpoint: string, config?: ApiRequestConfig): string {
    return `${endpoint}${config ? JSON.stringify(config) : ''}`;
  }

  // Configuration and initialization
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

  // Interceptors setup
  private setupInterceptors(): void {
    this.setupRequestInterceptor();
    this.setupResponseInterceptor();
    this.client.defaults.withCredentials = true;
  }

  private setupRequestInterceptor(): void {
    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const headers = new AxiosHeaders(config.headers);
      const serviceType = this.getServiceTypeFromUrl(config.url || '');
      
      if (serviceType) {
        const serviceConfig = this.serviceConfigs.get(serviceType);
        if (serviceConfig?.headers) {
          Object.entries(serviceConfig.headers).forEach(([key, value]) => {
            headers.set(key, value);
          });
        }
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
        
        // Check if this is a refresh request or if we've already tried to retry
        if (this.isRefreshRequest(config.url) || config._retry) {
          return Promise.reject(error);
        }
  
        // Handle both 401 Unauthorized and 403 Forbidden as auth issues
        if (error.response?.status === HTTP_STATUS.UNAUTHORIZED || 
            error.response?.status === HTTP_STATUS.FORBIDDEN) {
          
          // If we're already unauthenticated, don't try to refresh - just notify UI
          if (error.response?.data?.message === 'Not authenticated') {
            window.dispatchEvent(new Event('auth:logout'));
            return Promise.reject(error);
          }

          // If this is an auth API, don't trigger token refresh - let the auth components handle it
          if (config.url?.includes('/auth/')) {
            return Promise.reject(error);
          }
          
          // Otherwise, try to refresh
          config._retry = true;
          
          return this.handleUnauthorizedError(config);
        }
  
        return Promise.reject(error);
      }
    );
  }

  // Auth handling
  private async handleUnauthorizedError(config: RetryableRequestConfig) {
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
      // Try to get a new token
      const response = await this.client.post('/auth/refresh', null, {
        withCredentials: true,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      // Log successful refresh for debugging
      logger.info('Authentication refreshed successfully');
      
      // If the API returns a token directly, you might want to store it here
      // localStorage.setItem('auth_token', response.data.token);
      
      return response.data;
    } catch (error) {
      logger.error('Refresh authentication failed:', error);
      throw error;
    }
  }

  // Helper methods
  private getServiceTypeFromUrl(url: string): ServiceType | undefined {
    for (const serviceType of Object.values(ServiceType)) {
      if (url.toLowerCase().includes(serviceType.toLowerCase())) {
        return serviceType;
      }
    }
    return undefined;
  }

  private isRefreshRequest(url?: string): boolean {
    return url?.includes('/auth/refresh') || false;
  }

  private async enqueueRefreshRequest(): Promise<unknown> {
    return new Promise((resolve, reject) => {
      this.refreshQueue.push({ resolve, reject });
    });
  }

  private processRefreshQueue(error: any): void {
    this.refreshQueue.forEach(promise => {
      if (error) {
        promise.reject(error);
      } else {
        promise.resolve(null);
      }
    });
    this.refreshQueue = [];
  }

  private handleAuthenticationFailure(): void {
    this.clearAuthenticationState();
    window.dispatchEvent(new Event('auth:sessionExpired'));
  }

  private clearAuthenticationState(): void {
    this.cache.clear();
    window.dispatchEvent(new Event('auth:logout'));
  }

  // Base request method
  private async request<T>(
    method: HttpMethod,
    endpoint: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<T> {
    const requestId = ++BaseClient.requestCounter;
    console.log(`[${requestId}] Request started: ${method} ${endpoint}`);
    
    // Create cache key for deduplicating in-flight requests
    const cacheKey = `${method}:${endpoint}:${JSON.stringify(config)}`;
    
    // Check if we already have an in-flight request for this exact request
    if (this.inFlightRequests.has(cacheKey)) {
        console.log(`[${requestId}] Reusing in-flight request for: ${method} ${endpoint}`);
        return this.inFlightRequests.get(cacheKey) as Promise<T>;
    }
    
    // Actual request execution logic
    const executeRequest = async (): Promise<T> => {
        try {
            const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};
            
            console.log(`[${requestId}] Request config:`, {
                method,
                endpoint,
                config: axiosConfig
            });

            const cleanEndpoint = endpoint.replace(/^\/+/, '');
            const normalizedEndpoint = cleanEndpoint.replace(/^api\/v1\//, '');

            const requestConfig: AxiosRequestConfig = {
                method: method.toLowerCase(),
                url: normalizedEndpoint,
                data,
                withCredentials: true, // Critical for cookies
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache',
                    ...(axiosConfig?.headers || {})
                },
                validateStatus: (status) => true, // Handle all status codes manually
                ...axiosConfig,
                onUploadProgress
            };

            const response = await this.client.request(requestConfig);
            
            console.log(`[${requestId}] Response received:`, {
                status: response.status,
                statusText: response.statusText
            });

            // Handle non-2xx status codes
            if (response.status >= 400) {
                throw {
                    response: response,
                    isAxiosError: true,
                    message: response.data?.message || 'Request failed'
                };
            }

            console.log(`[${requestId}] Request complete: ${method} ${endpoint}`);
            return response.data;
        } catch (error) {
            console.error(`[${requestId}] Request failed: ${method} ${endpoint}`, error);

            if (axios.isAxiosError(error) && error.response) {
                console.error(`[${requestId}] Error details:`, {
                    status: error.response.status,
                    statusText: error.response.statusText,
                    data: error.response.data
                });
            }

            throw this.handleApiError(error);
        }
    };
    
    // Create the promise and store it
    const promise = executeRequest();
    this.inFlightRequests.set(cacheKey, promise);
    
    try {
        return await promise;
    } finally {
        // Clean up the in-flight request
        this.inFlightRequests.delete(cacheKey);
    }
  }

  // Error handling
  private handleApiError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        logger.error('Network Error:', {
          message: 'No response received from server',
          error: error
        });
        return new Error('Network error: Unable to connect to the server. Please check your internet connection.');
      }
  
      const errorResponse = error.response.data as ApiErrorResponse;
      const status = error.response.status;
      const headers = error.response.headers;
  
      // Log detailed error information
      logger.error('API Error:', {
        status,
        endpoint: error.config?.url,
        method: error.config?.method?.toUpperCase(),
        data: errorResponse,
        headers,
        fullError: error
      });
  
      switch (status) {
        case HTTP_STATUS.BAD_REQUEST:
          return new Error(
            errorResponse?.error?.message || 
            errorResponse?.message || 
            'The request was invalid. Please check your input and try again.'
          );
  
        case HTTP_STATUS.UNAUTHORIZED:
          if (errorResponse?.error?.code === 'token_expired') {
            window.dispatchEvent(new Event('auth:token_expired'));
            return new Error('Your session has expired. Please log in again.');
          }
          window.dispatchEvent(new Event('auth:logout'));
          return new Error(
            errorResponse?.message || 
            'Authentication failed. Please log in again.'
          );
  
        case HTTP_STATUS.FORBIDDEN:
          return new Error(
            errorResponse?.message || 
            'You do not have permission to perform this action. Please contact support if you believe this is an error.'
          );
  
        case HTTP_STATUS.NOT_FOUND:
          return new Error(
            errorResponse?.message || 
            'The requested resource was not found. Please check the URL and try again.'
          );
  
        case HTTP_STATUS.CONFLICT:
          return new Error(
            errorResponse?.message || 
            'This operation could not be completed due to a conflict with existing data.'
          );
  
        case HTTP_STATUS.TOO_MANY_REQUESTS:
          return new Error(
            errorResponse?.message || 
            'Too many requests. Please wait a moment before trying again.'
          );
  
        case HTTP_STATUS.INTERNAL_SERVER_ERROR:
          logger.error('Server Error:', errorResponse);
          return new Error(
            errorResponse?.message || 
            'An unexpected server error occurred. Our team has been notified.'
          );
  
        case HTTP_STATUS.SERVICE_UNAVAILABLE:
          return new Error(
            errorResponse?.message || 
            'The service is temporarily unavailable. Please try again later.'
          );
  
        default:
          // Handle other status codes
          if (status >= 500) {
            logger.error('Unhandled Server Error:', {
              status,
              response: errorResponse
            });
            return new Error(
              errorResponse?.message || 
              'A server error occurred. Our team has been notified.'
            );
          }
  
          if (status >= 400) {
            return new Error(
              errorResponse?.error?.message || 
              errorResponse?.message || 
              'The request could not be completed. Please try again.'
            );
          }
  
          return new Error(
            errorResponse?.error?.message || 
            errorResponse?.message || 
            error.message || 
            'An unexpected error occurred. Please try again.'
          );
      }
    }
  
    // Handle non-Axios errors
    if (error instanceof Error) {
      logger.error('Non-Axios Error:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      return error;
    }
  
    // Handle unknown errors
    logger.error('Unknown Error:', error);
    return new Error('An unexpected error occurred. Please try again later.');
  }
}

export const baseAxiosClient = BaseClient.getInstance();