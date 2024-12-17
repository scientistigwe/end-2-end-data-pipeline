// src/auth/api/authApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { InternalAxiosRequestConfig } from 'axios';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import type {
  AuthTokens,
  AuthResponse,
  LoginCredentials,
  RegisterData,
  ResetPasswordData,
  ChangePasswordData,
  VerifyEmailData
} from '../types/auth';
import type { User } from '@/common/types/user';
import type { ApiResponse } from '@/common/types/api';

const AUTH_STORAGE_KEY = 'auth_tokens';

class AuthApi extends BaseClient {
  constructor() {
    super({
      baseURL: import.meta.env.VITE_AUTH_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'auth'
      }
    });

    this.setupAuthInterceptors();
  }

  private setupAuthInterceptors() {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const tokens = this.getAuthTokens();
        if (tokens?.accessToken) {
          config.headers.set('Authorization', `Bearer ${tokens.accessToken}`);
        }
        return config;
      }
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          const tokens = this.getAuthTokens();
          
          if (tokens?.refreshToken) {
            try {
              const response = await this.refreshToken(tokens.refreshToken);
              const newTokens = response.data;
              this.setAuthTokens(newTokens);
              originalRequest.headers.set('Authorization', `Bearer ${newTokens.accessToken}`);
              return this.client(originalRequest);
            } catch {
              this.handleAuthFailure();
            }
          } else {
            this.handleAuthFailure();
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth Token Management
  private setAuthTokens(tokens: AuthTokens): void {
    storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
  }

  public async refreshToken(token: string) {
    return this.post<AuthTokens>(
      this.getRoute('AUTH', 'REFRESH'),
      { token }
    );
  }

  private handleAuthFailure(): void {
    this.clearAuth();
    window.dispatchEvent(new CustomEvent('auth:sessionExpired'));
  }

  // Authentication Methods
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthResponse>> {
    const response = await this.post<AuthResponse>(
      this.getRoute('AUTH', 'LOGIN'),
      credentials
    );
    
    if (response.data) {
      const { user, ...tokens } = response.data;
      this.setAuthTokens(tokens);
    }
    
    return response;
  }

  async register(data: RegisterData): Promise<ApiResponse<{ user: User }>> {
    return this.post(this.getRoute('AUTH', 'REGISTER'), data);
  }

  async logout(): Promise<ApiResponse<void>> {
    const response = await this.post<void>(this.getRoute('AUTH', 'LOGOUT'));
    this.clearAuth();
    return response;
  }

  // Email Verification
  async verifyEmail(data: VerifyEmailData): Promise<ApiResponse<void>> {
    return this.post(this.getRoute('AUTH', 'VERIFY_EMAIL'), data);
  }

  // Password Management
  async forgotPassword(email: string): Promise<ApiResponse<void>> {
    return this.post(this.getRoute('AUTH', 'FORGOT_PASSWORD'), { email });
  }

  async resetPassword(data: ResetPasswordData): Promise<ApiResponse<void>> {
    return this.post(this.getRoute('AUTH', 'RESET_PASSWORD'), data);
  }

  async changePassword(data: ChangePasswordData): Promise<ApiResponse<void>> {
    return this.post(this.getRoute('AUTH', 'CHANGE_PASSWORD'), data);
  }

  // Profile Management
  async getProfile(): Promise<ApiResponse<User>> {
    return this.get<User>(this.getRoute('AUTH', 'PROFILE'));
  }

  async updateProfile(data: Partial<User>): Promise<ApiResponse<User>> {
    return this.put<User>(this.getRoute('AUTH', 'PROFILE'), data);
  }

  // Auth State Management
  isAuthenticated(): boolean {
    const tokens = this.getAuthTokens();
    return !!tokens?.accessToken;
  }

  getAuthTokens(): AuthTokens | null {
    return storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
  }

  clearAuth(): void {
    storageUtils.removeItem(AUTH_STORAGE_KEY);
  }

  // Helper Methods
  async validateSession(): Promise<boolean> {
    try {
      await this.getProfile();
      return true;
    } catch {
      return false;
    }
  }

  async ensureAuthenticated(): Promise<void> {
    if (!this.isAuthenticated()) {
      throw new Error('User is not authenticated');
    }
    
    const isValid = await this.validateSession();
    if (!isValid) {
      this.handleAuthFailure();
      throw new Error('Session is invalid');
    }
  }

  onSessionExpired(callback: () => void): () => void {
    const handler = () => callback();
    window.addEventListener('auth:sessionExpired', handler);
    return () => window.removeEventListener('auth:sessionExpired', handler);
  }
}

export const authApi = new AuthApi();