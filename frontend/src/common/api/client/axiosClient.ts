// src/common/api/client/axiosClient.ts
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

export class AxiosClient {
  private client: AxiosInstance;

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

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Token handling should be done by auth module
        return config;
      },
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
    config?: Omit<ApiRequestConfig, 'method'>,
    data?: unknown
  ): Promise<ApiResponse<T>> {
    const finalUrl = config?.routeParams ? 
      formatEndpoint(url, config.routeParams) : 
      url;
    
    const { routeParams, onUploadProgress, ...axiosConfig } = config ?? {};

    try {
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
}

export const axiosClient = new AxiosClient();

