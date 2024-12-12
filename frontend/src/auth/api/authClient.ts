// auth/api/authClient.ts
import { BaseClient } from '@/common/api/client/baseClient';
import type { InternalAxiosRequestConfig } from 'axios';
import { AUTH_API_CONFIG } from './config';
import { StorageUtils } from '@/common/utils/storage';
import type { AuthTokens } from '../types';

const AUTH_STORAGE_KEY = 'auth_tokens';

export class AuthClient extends BaseClient {
  constructor() {
    super({
      baseURL: AUTH_API_CONFIG.baseURL,
      timeout: AUTH_API_CONFIG.timeout
    });
  }

  protected override setupInterceptors() {
    super.setupInterceptors();
    
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const tokens = StorageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
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
          const tokens = StorageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
          
          if (tokens?.refreshToken) {
            try {
              const response = await this.refreshToken(tokens.refreshToken);
              const newTokens = response.data;
              StorageUtils.setItem(AUTH_STORAGE_KEY, newTokens);
              originalRequest.headers.set('Authorization', `Bearer ${newTokens.accessToken}`);
              return this.client(originalRequest);
            } catch {
              StorageUtils.removeItem(AUTH_STORAGE_KEY);
              window.dispatchEvent(new CustomEvent('auth:sessionExpired'));
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private async refreshToken(token: string): Promise<ApiResponse<AuthTokens>> {
    return this.post(AUTH_API_CONFIG.endpoints.REFRESH, { token });
  }
}

