import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  CreateAxiosDefaults,
  AxiosProgressEvent,
  AxiosHeaders,
  InternalAxiosRequestConfig
} from 'axios';
import { API_CONFIG } from './config';
import { ApiRequestConfig, ApiResponse } from './../../types';
import { formatEndpoint } from './utils';

export class BaseApiClient {
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
        const token = localStorage.getItem('token');
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
      (error) => Promise.reject(error)
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
      if (axios.isAxiosError(error)) {
        throw new Error(`API Error: ${error.response?.data?.message || error.message}`);
      }
      throw error;
    }
  }
}