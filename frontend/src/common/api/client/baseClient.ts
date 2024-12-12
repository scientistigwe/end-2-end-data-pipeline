// common/api/client/baseClient.ts
import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  CreateAxiosDefaults,
  AxiosProgressEvent,
  AxiosHeaders,
  InternalAxiosRequestConfig
} from 'axios';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import { handleApiError } from '../utils/errorHandlers';
import { formatEndpoint } from '../utils/formatters';

export class BaseClient {
  protected client: AxiosInstance;

  constructor(config?: CreateAxiosDefaults) {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_URL || '/api/v1',
      timeout: 30000,
      headers: new AxiosHeaders({
        'Content-Type': 'application/json'
      }),
      ...config
    } as CreateAxiosDefaults);

    this.setupInterceptors();
  }

  protected setupInterceptors() {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => config,
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error) => Promise.reject(handleApiError(error))
    );
  }

  protected async request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    url: string,
    config?: ApiRequestConfig,
    data?: unknown
  ): Promise<ApiResponse<T>> {
    try {
      const finalUrl = config?.routeParams ? 
        formatEndpoint(url, config.routeParams) : 
        url;

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

  // Convenience methods
  protected async get<T>(url: string, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('get', url, config);
  }

  protected async post<T>(url: string, data?: unknown, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('post', url, config, data);
  }

  protected async put<T>(url: string, data?: unknown, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('put', url, config, data);
  }

  protected async delete<T>(url: string, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('delete', url, config);
  }
}

export const baseAxiosClient = new BaseClient();