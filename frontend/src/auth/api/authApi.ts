import { baseAxiosClient } from '@/common/api/client/baseClient';
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

  // Token Management
  private setAuthTokens(tokens: AuthTokens): void {
    storageUtils.setItem(AUTH_STORAGE_KEY, tokens);
  }

  private getAuthTokens(): AuthTokens | null {
    return storageUtils.getItem<AuthTokens>(AUTH_STORAGE_KEY);
  }

  private clearAuth(): void {
    storageUtils.removeItem(AUTH_STORAGE_KEY);
  }

  // Authentication Methods
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.client.executePost<AuthResponse>(
      this.client.createRoute('AUTH', 'LOGIN'),
      credentials
    );
    
    const { accessToken, refreshToken, expiresIn } = response;
    this.setAuthTokens({ accessToken, refreshToken, expiresIn });
    return response;
  }

  async register(data: RegisterData): Promise<{ user: User }> {
    return this.client.executePost<{ user: User }>(
      this.client.createRoute('AUTH', 'REGISTER'),
      data
    );
  }

  async logout(): Promise<void> {
    const response = await this.client.executePost<void>(
      this.client.createRoute('AUTH', 'LOGOUT')
    );
    this.clearAuth();
    return response;
  }

  // Email Verification
  async verifyEmail(data: VerifyEmailData): Promise<void> {
    return this.client.executePost<void>(
      this.client.createRoute('AUTH', 'VERIFY_EMAIL'),
      data
    );
  }

  // Password Management
  async forgotPassword(email: string): Promise<void> {
    return this.client.executePost<void>(
      this.client.createRoute('AUTH', 'FORGOT_PASSWORD'),
      { email }
    );
  }

  async resetPassword(data: ResetPasswordData): Promise<void> {
    return this.client.executePost<void>(
      this.client.createRoute('AUTH', 'RESET_PASSWORD'),
      data
    );
  }

  async changePassword(data: ChangePasswordData): Promise<void> {
    return this.client.executePost<void>(
      this.client.createRoute('AUTH', 'CHANGE_PASSWORD'),
      data
    );
  }

  // Profile Management
  async getProfile(): Promise<User> {
    return this.client.executeGet<User>(
      this.client.createRoute('AUTH', 'PROFILE')
    );
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    return this.client.executePut<User>(
      this.client.createRoute('AUTH', 'PROFILE'),
      data
    );
  }

  // Auth State Management
  isAuthenticated(): boolean {
    const tokens = this.getAuthTokens();
    return !!tokens?.accessToken;
  }

  // Session Management
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
      this.clearAuth();
      window.dispatchEvent(new Event('auth:sessionExpired'));
      throw new Error('Session is invalid');
    }
  }

  onSessionExpired(callback: () => void): () => void {
    const handler = () => callback();
    window.addEventListener('auth:sessionExpired', handler);
    return () => window.removeEventListener('auth:sessionExpired', handler);
  }
}

// Export singleton instance
export const authApi = new AuthApi();