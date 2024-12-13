// auth/api/authClient.ts
import { BaseClient } from '@/common/api/client/baseClient';
import type { InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@/common/types/api';
import { AUTH_API_CONFIG } from './config';
import { storageUtils } from '@/common/utils/storage/storageUtils';
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
        const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
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
          const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
          
          if (tokens?.refreshToken) {
            try {
              const response = await this.refreshToken(tokens.refreshToken);
              const newTokens = response.data;
              storageUtils.setItem(AUTH_STORAGE_KEY, newTokens);
              originalRequest.headers.set('Authorization', `Bearer ${newTokens.accessToken}`);
              return this.client(originalRequest);
            } catch {
              storageUtils.removeItem(AUTH_STORAGE_KEY);
              window.dispatchEvent(new CustomEvent('auth:sessionExpired'));
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  public async refreshToken(token: string): Promise<ApiResponse<AuthTokens>> {
    return this.post(AUTH_API_CONFIG.endpoints.REFRESH, { token });
  }
}