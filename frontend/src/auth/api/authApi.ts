// auth/api/authApi.ts
import { AuthClient } from './authClient';
import { AUTH_API_CONFIG } from './config';
import type { ApiResponse } from '@/common/types/api';
import type { StorageUtils } from '@/common/api/utils/storage';
import type {
  AuthTokens,
  LoginCredentials,
  RegisterData,
  ResetPasswordData,
  ChangePasswordData,
  VerifyEmailData
} from '../types/auth';
import type { User } from '@/common/types/user';

const AUTH_STORAGE_KEY = 'auth_tokens';

class AuthApi extends AuthClient {
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthTokens & { user: User }>> {
    const response = await this.post<AuthTokens & { user: User }>(
      AUTH_API_CONFIG.endpoints.LOGIN,
      credentials
    );
    
    if (response.data?.accessToken) {
      StorageUtils.setItem(AUTH_STORAGE_KEY, response.data);
    }
    
    return response;
  }

  async register(data: RegisterData): Promise<ApiResponse<{ user: User }>> {
    return this.post(AUTH_API_CONFIG.endpoints.REGISTER, data);
  }

  async logout(): Promise<ApiResponse<void>> {
    const response = await this.post<void>(AUTH_API_CONFIG.endpoints.LOGOUT);
    StorageUtils.removeItem(AUTH_STORAGE_KEY);
    return response;
  }

  async verifyEmail(data: VerifyEmailData): Promise<ApiResponse<void>> {
    return this.post(AUTH_API_CONFIG.endpoints.VERIFY_EMAIL, data);
  }

  async forgotPassword(email: string): Promise<ApiResponse<void>> {
    return this.post(AUTH_API_CONFIG.endpoints.FORGOT_PASSWORD, { email });
  }

  async resetPassword(data: ResetPasswordData): Promise<ApiResponse<void>> {
    return this.post(AUTH_API_CONFIG.endpoints.RESET_PASSWORD, data);
  }

  async changePassword(data: ChangePasswordData): Promise<ApiResponse<void>> {
    return this.post(AUTH_API_CONFIG.endpoints.CHANGE_PASSWORD, data);
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.get<User>(AUTH_API_CONFIG.endpoints.PROFILE);
  }

  async updateProfile(data: Partial<User>): Promise<ApiResponse<User>> {
    return this.put<User>(AUTH_API_CONFIG.endpoints.PROFILE, data);
  }
}

// Create singleton instance
export const authApi = new AuthApi();

