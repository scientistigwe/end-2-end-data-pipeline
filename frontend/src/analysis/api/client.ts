// src/analysis/api/client.ts
import axios, { 
    AxiosInstance, 
    AxiosRequestConfig, 
    CreateAxiosDefaults,
    AxiosProgressEvent,
    AxiosHeaders,
    InternalAxiosRequestConfig
  } from 'axios';
  import { API_CONFIG } from './config';
  import type { ApiResponse, ApiRequestConfig } from '../../../../types';
  import { formatEndpoint } from '../../common/api/utils/utils';
  
  export class AnalysisApiClient {
    private client: AxiosInstance;
  
    constructor() {
      this.client = axios.create({
        baseURL: API_CONFIG.BASE_URL,
        timeout: API_CONFIG.TIMEOUT,
        headers: new AxiosHeaders({
          'Content-Type': 'application/json'
        })
      } as CreateAxiosDefaults);
  
      this.setupInterceptors();
    }
  
    private setupInterceptors() {
      this.client.interceptors.request.use(
        (config: InternalAxiosRequestConfig) => {
          const token = localStorage.getItem('analysis_token');
          if (token) {
            if (!config.headers) {
              config.headers = new AxiosHeaders();
            }
            config.headers.set('Authorization', `Bearer ${token}`);
          }
          return config;
        },
        (error) => Promise.reject(error)
      );
  
      this.client.interceptors.response.use(
        (response) => response,
        (error) => Promise.reject(this.handleAnalysisError(error))
      );
    }
  
    private handleAnalysisError(error: any): Error {
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.message || error.message;
        switch (error.response?.status) {
          case 400:
            return new Error(`Invalid analysis configuration: ${errorMessage}`);
          case 401:
            return new Error('Analysis authentication failed');
          case 404:
            return new Error('Analysis resource not found');
          case 429:
            return new Error('Analysis rate limit exceeded');
          case 500:
            return new Error('Analysis service error');
          default:
            return new Error(`Analysis API Error: ${errorMessage}`);
        }
      }
      return error;
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
        throw this.handleAnalysisError(error);
      }
    }
  
    // Utility method for handling analysis uploads with progress
    protected handleUploadProgress(
      onProgress?: (progress: number) => void
    ): AxiosRequestConfig {
      return {
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (progressEvent.total) {
            const progress = (progressEvent.loaded / progressEvent.total) * 100;
            onProgress?.(Math.round(progress));
          }
        }
      };
    }
  }
  
  export const analysisClient = new AnalysisApiClient();