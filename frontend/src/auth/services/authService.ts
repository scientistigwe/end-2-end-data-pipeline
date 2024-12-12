// src/auth/services/authService.ts
import { authApi } from '../api/authApi';
import { authUtils } from '../utils/authUtils';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens 
} from '../types/auth';
import type { User } from '@/common/types/user';

interface AuthResult {
  user: User;
  tokens: AuthTokens;
}

class AuthService {
  private static instance: AuthService;

  private constructor() {}

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  async login(credentials: LoginCredentials): Promise<AuthResult> {
    try {
      const response = await authApi.login(credentials);
      const { user, ...tokens } = response.data;
      authUtils.setTokens(tokens);
      return { user, tokens };
    } catch (error) {
      authUtils.clearTokens();
      throw error;
    }
  }

  async register(data: RegisterData): Promise<User> {
    const response = await authApi.register(data);
    return response.data.user;
  }

  async refreshSession(): Promise<AuthTokens | null> {
    const currentTokens = authUtils.getTokens();
    if (!currentTokens?.refreshToken) return null;

    try {
      const response = await authApi.refreshToken(currentTokens.refreshToken);
      const newTokens = response.data;
      authUtils.setTokens(newTokens);
      return newTokens;
    } catch (error) {
      authUtils.clearTokens();
      return null;
    }
  }

  async validateSession(): Promise<boolean> {
    const tokens = authUtils.getTokens();
    if (!tokens?.accessToken) return false;

    if (authUtils.isTokenExpired(tokens.accessToken)) {
      const newTokens = await this.refreshSession();
      return !!newTokens;
    }

    return true;
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await authApi.getCurrentUser();
      return response.data;
    } catch {
      return null;
    }
  }

  async logout(): Promise<void> {
    try {
      await authApi.logout();
    } finally {
      authUtils.clearTokens();
    }
  }
}

export const authService = AuthService.getInstance();

