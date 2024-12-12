  // src/pipeline/api/client.ts
  import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
  import { API_CONFIG } from './config';
  
  export class ApiClient {
    private client: AxiosInstance;
  
    constructor() {
      this.client = axios.create({
        baseURL: API_CONFIG.BASE_PATH,
        timeout: API_CONFIG.TIMEOUT,
        headers: {
          'Content-Type': 'application/json'
        }
      });
  
      this.setupInterceptors();
    }
  
    private setupInterceptors(): void {
      this.client.interceptors.request.use(
        (config) => {
          // Add auth token if available
          const token = localStorage.getItem('authToken');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
          return config;
        },
        (error) => Promise.reject(error)
      );
  
      this.client.interceptors.response.use(
        (response) => response,
        this.handleError
      );
    }
  
    private handleError(error: any): Promise<never> {
      if (error.response?.status === 401) {
        // Handle unauthorized access
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  
    protected async request<T>(
      method: string,
      url: string,
      config?: AxiosRequestConfig
    ): Promise<T> {
      const response = await this.client.request<T>({
        method,
        url,
        ...config
      });
      return response.data;
    }
  }
  