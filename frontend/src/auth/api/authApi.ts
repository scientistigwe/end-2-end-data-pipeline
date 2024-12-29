// auth/api/authApi.ts
import { baseAxiosClient } from '@/common/api/client/baseClient';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import type {
  AuthTokens,
  LoginResponse,
  RegisterResponse,
  LoginCredentials,
  RegisterData,
  ResetPasswordData,
  ChangePasswordData,
  VerifyEmailData,
  ProfileUpdateData
} from '../types/auth';
import type { User } from '@/common/types/user';

const AUTH_STORAGE_KEY = 'auth_tokens';

class AuthApi {
  private client = baseAxiosClient;

  constructor() {
    this.setupAuthHeaders();
  }

  private setupAuthHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'auth'
    });
  }

  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await this.client.executePost<LoginResponse>('/auth/login', credentials);
    if (response.tokens) {
      this.setAuthTokens(response.tokens);
    }
    return response;
  }

  async register(data: RegisterData): Promise<RegisterResponse> {
    const response = await this.client.executePost<RegisterResponse>('/auth/register', data);
    if (response.tokens) {
      this.setAuthTokens(response.tokens);
    }
    return response;
  }

  async refreshToken(refresh_token: string): Promise<AuthTokens> {
    const response = await this.client.executePost<{ tokens: AuthTokens }>('/auth/refresh', {
      refresh_token
    });
    return response.tokens;
  }

  async logout(): Promise<void> {
    try {
      await this.client.executePost<void>('/auth/logout');
    } finally {
      this.clearAuth();
    }
  }

  async getProfile(): Promise<User> {
    const response = await this.client.executeGet<User>('/auth/profile');
    return response;
  }

  async updateProfile(data: ProfileUpdateData): Promise<User> {
    const response = await this.client.executePut<User>('/auth/profile', data);
    return response;
  }

  async verifyEmail(data: VerifyEmailData): Promise<void> {
    await this.client.executePost<void>('/auth/verify-email', data);
  }

  async changePassword(data: ChangePasswordData): Promise<void> {
    await this.client.executePost<void>('/auth/change-password', data);
  }

  async resetPassword(data: ResetPasswordData): Promise<void> {
    await this.client.executePost<void>('/auth/reset-password', data);
  }

  private setAuthTokens(tokens: AuthTokens): void {
    storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
  }

  private clearAuth(): void {
    storageUtils.removeItem(AUTH_STORAGE_KEY);
  }

  isAuthenticated(): boolean {
    const tokens = storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
    return !!tokens?.access_token;
  }
}

export const authApi = new AuthApi();