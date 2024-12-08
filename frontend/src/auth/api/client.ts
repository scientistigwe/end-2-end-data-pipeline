// src/auth/api/client.ts
import axios, { 
    AxiosInstance, 
    AxiosRequestConfig, 
    CreateAxiosDefaults,
    AxiosHeaders,
    InternalAxiosRequestConfig
  } from 'axios';
  import { API_CONFIG } from './config';
  import type { ApiResponse, ApiRequestConfig } from '../types/api';
  import type {
    User,
    AuthTokens,
    LoginCredentials,
    RegisterData,
    ResetPasswordData,
    ChangePasswordData,
    VerifyEmailData
  } from '../types/auth';
  
  export class AuthApiClient {
    private client: AxiosInstance;
    private readonly TOKEN_KEY = 'auth_tokens';
  
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
          const tokens = this.getStoredTokens();
          if (tokens?.accessToken) {
            if (!config.headers) {
              config.headers = new AxiosHeaders();
            }
            config.headers.set('Authorization', `Bearer ${tokens.accessToken}`);
          }
          return config;
        },
        (error) => Promise.reject(this.handleAuthError(error))
      );
  
      this.client.interceptors.response.use(
        (response) => response,
        async (error) => {
          const originalRequest = error.config;
          if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            try {
              const tokens = this.getStoredTokens();
              if (tokens?.refreshToken) {
                const newTokens = await this.refreshToken(tokens.refreshToken);
                this.setTokens(newTokens);
                originalRequest.headers.Authorization = `Bearer ${newTokens.accessToken}`;
                return this.client(originalRequest);
              }
            } catch (refreshError) {
              this.clearTokens();
              window.dispatchEvent(new Event('auth:logout'));
            }
          }
          return Promise.reject(this.handleAuthError(error));
        }
      );
    }
  
    private handleAuthError(error: any): Error {
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.message || error.message;
        switch (error.response?.status) {
          case 401:
            return new Error('Authentication failed: Invalid credentials');
          case 403:
            return new Error('Authorization failed: Insufficient permissions');
          case 404:
            return new Error('User not found');
          case 422:
            return new Error(`Validation error: ${errorMessage}`);
          default:
            return new Error(`Authentication error: ${errorMessage}`);
        }
      }
      return error;
    }
  
    private async request<T>(
      method: 'get' | 'post' | 'put' | 'delete',
      url: string,
      config?: Omit<ApiRequestConfig, 'method'>,
      data?: unknown
    ): Promise<ApiResponse<T>> {
      const { routeParams, ...axiosConfig } = config ?? {};
      
      try {
        const requestConfig: AxiosRequestConfig = {
          method,
          url,
          data,
          ...axiosConfig
        };
  
        const response = await this.client.request<ApiResponse<T>>(requestConfig);
        return response.data;
      } catch (error) {
        throw this.handleAuthError(error);
      }
    }
  
    // Token Management Methods
    public setTokens(tokens: AuthTokens): void {
      localStorage.setItem(this.TOKEN_KEY, JSON.stringify(tokens));
    }
  
    public getStoredTokens(): AuthTokens | null {
      const tokens = localStorage.getItem(this.TOKEN_KEY);
      return tokens ? JSON.parse(tokens) : null;
    }
  
    public clearTokens(): void {
      localStorage.removeItem(this.TOKEN_KEY);
    }
  
    public isTokenExpired(token: string): boolean {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return Date.now() >= payload.exp * 1000;
      } catch {
        return true;
      }
    }
  
    // Auth API Methods
    public async login(credentials: LoginCredentials): Promise<ApiResponse<AuthTokens & { user: User }>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.LOGIN, {}, credentials);
    }
  
    public async register(data: RegisterData): Promise<ApiResponse<{ user: User }>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.REGISTER, {}, data);
    }
  
    public async refreshToken(token: string): Promise<ApiResponse<AuthTokens>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.REFRESH, {}, { token });
    }
  
    public async logout(): Promise<ApiResponse<void>> {
      const result = await this.request('post', API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
      this.clearTokens();
      return result;
    }
  
    public async getCurrentUser(): Promise<ApiResponse<User>> {
      return this.request('get', API_CONFIG.ENDPOINTS.AUTH.PROFILE);
    }
  
    public async updateProfile(data: Partial<User>): Promise<ApiResponse<User>> {
      return this.request('put', API_CONFIG.ENDPOINTS.AUTH.PROFILE, {}, data);
    }
  
    public async changePassword(data: ChangePasswordData): Promise<ApiResponse<void>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.CHANGE_PASSWORD, {}, data);
    }
  
    public async verifyEmail(data: VerifyEmailData): Promise<ApiResponse<void>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.VERIFY_EMAIL, {}, data);
    }
  
    public async forgotPassword(email: string): Promise<ApiResponse<void>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.FORGOT_PASSWORD, {}, { email });
    }
  
    public async resetPassword(data: ResetPasswordData): Promise<ApiResponse<void>> {
      return this.request('post', API_CONFIG.ENDPOINTS.AUTH.RESET_PASSWORD, {}, data);
    }
  }
  
  export const authClient = new AuthApiClient();