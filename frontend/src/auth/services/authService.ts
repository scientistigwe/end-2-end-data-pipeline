// auth/pipeline/authService.ts
import { authApi } from '../api';
import { storageUtils } from '@/common/utils/storage/storageUtils';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens 
} from '../types';
import type { User } from '@/common/types/user';
import type { ApiResponse } from '@/common/types/api';

const AUTH_STORAGE_KEY = 'auth_tokens';

class AuthService {
  private static instance: AuthService;

  private constructor() {}

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthTokens & { user: User }>> {
    try {
      const response = await authApi.login(credentials);
      if (response.data) {
        storageUtils.setItem(AUTH_STORAGE_KEY, response.data);
      }
      return response;
    } catch (error) {
      storageUtils.removeItem(AUTH_STORAGE_KEY);
      throw error;
    }
  }

  async register(data: RegisterData): Promise<ApiResponse<{ user: User }>> {
    return authApi.register(data);
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return authApi.getCurrentUser();
  }

  async logout(): Promise<void> {
    try {
      await authApi.logout();
    } finally {
      storageUtils.removeItem(AUTH_STORAGE_KEY);
    }
  }

  getStoredTokens(): AuthTokens | null {
    return storageUtils.getItem(AUTH_STORAGE_KEY);
  }

  clearStoredTokens(): void {
    storageUtils.removeItem(AUTH_STORAGE_KEY);
  }
}

export const authService = AuthService.getInstance();