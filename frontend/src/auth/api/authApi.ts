// src/services/api/authApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../common/types/api';
import type {
  User,
  AuthTokens,
  LoginCredentials,
  RegisterData,
  ResetPasswordData,
  ChangePasswordData,
  VerifyEmailData
} from '../types/auth';

class AuthApi extends BaseApiClient {
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthTokens & { user: User }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.LOGIN,
      {},
      credentials
    );
  }

  async register(data: RegisterData): Promise<ApiResponse<{ user: User }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.REGISTER,
      {},
      data
    );
  }

  async refreshToken(token: string): Promise<ApiResponse<AuthTokens>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.REFRESH,
      {},
      { token }
    );
  }

  async logout(): Promise<ApiResponse<void>> {
    return this.request('post', API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
  }

  async verifyEmail(data: VerifyEmailData): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.VERIFY_EMAIL,
      {},
      data
    );
  }

  async forgotPassword(email: string): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.FORGOT_PASSWORD,
      {},
      { email }
    );
  }

  async resetPassword(data: ResetPasswordData): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.AUTH.RESET_PASSWORD,
      {},
      data
    );
  }

  async changePassword(data: ChangePasswordData): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      `${API_CONFIG.ENDPOINTS.AUTH.PROFILE}/change-password`,
      {},
      data
    );
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request('get', `${API_CONFIG.ENDPOINTS.AUTH.PROFILE}`);
  }

  async updateProfile(data: Partial<User>): Promise<ApiResponse<User>> {
    return this.request(
      'put',
      `${API_CONFIG.ENDPOINTS.AUTH.PROFILE}`,
      {},
      data
    );
  }
}

export const authApi = new AuthApi();

