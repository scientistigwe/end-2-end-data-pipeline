// auth/api/authApi.ts
import { AxiosResponse } from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import type {
  AuthTokens,
  LoginResponse,
  RegisterResponse,
  LoginCredentials,
  RegisterData,
  ProfileUpdateData,
  ChangePasswordData,
  ResetPasswordData,
  VerifyEmailData,
  LoginResponseData,
  RegisterResponseData,
  LoginApiResponse,
  RegisterApiResponse,
} from '../types/auth';
import { isAuthError, type ApiErrorDetail, type ApiBaseResponse } from '../types/api';
import type { User } from '@/common/types/user';

class AuthApi {
  private client = baseAxiosClient;

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.AUTH,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
  }

  async login(credentials: LoginCredentials): Promise<LoginResponseData> {
    try {
      console.log('Sending login request with:', credentials);
      
      const response = await this.client.executePost<LoginApiResponse>(
        this.client.createRoute('AUTH', 'LOGIN'),
        credentials,
        {
          withCredentials: true // Enable cookie handling
        }
      );

      // Dispatch auth success event
      window.dispatchEvent(new Event('auth:login'));
      
      return response;
    } catch (error) {
      console.error('Login API error details:', error);
      throw this.handleAuthError(error);
    }
  }

  async register(data: RegisterData): Promise<RegisterResponseData> {
    try {
      console.log('Sending registration request:', data);
      
      const response = await this.client.executePost<RegisterApiResponse>(
        this.client.createRoute('AUTH', 'REGISTER'),
        data,
        {
          withCredentials: true
        }
      );
      
      if (!response || !response.user) {
        console.error('Invalid response structure:', response);
        throw new Error('Invalid response format from server');
      }
      
      // Dispatch auth success event
      window.dispatchEvent(new Event('auth:register'));
      
      return response;
    } catch (error) {
      console.error('Registration API error details:', {
        error,
        response: error.response?.data, 
        status: error.response?.status
      });
      throw this.handleAuthError(error);
    }
  }

  async refreshToken(): Promise<void> {
    try {
      await this.client.executePost<void>(
        this.client.createRoute('AUTH', 'REFRESH'),
        undefined,
        {
          withCredentials: true
        }
      );
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.handleAuthError(error);
      // Dispatch session expired event
      window.dispatchEvent(new Event('auth:sessionExpired'));
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await this.client.executePost<void>(
        this.client.createRoute('AUTH', 'LOGOUT'),
        undefined,
        {
          withCredentials: true
        }
      );
    } finally {
      // Dispatch logout event
      window.dispatchEvent(new Event('auth:logout'));
    }
  }

  async getProfile(): Promise<User> {
    const response = await this.client.executeGet<ApiBaseResponse<User>>(
      this.client.createRoute('AUTH', 'PROFILE'),
      {
        withCredentials: true
      }
    );
    
    if (!response.data) {
      throw new Error('Invalid profile response format');
    }
    return response.data;
  }

  async updateProfile(data: ProfileUpdateData): Promise<User> {
    const response = await this.client.executePut<ApiBaseResponse<User>>(
      this.client.createRoute('AUTH', 'PROFILE'),
      data,
      {
        withCredentials: true
      }
    );
    
    if (!response.data) {
      throw new Error('Invalid profile update response format');
    }
    return response.data;
  }

  async verifyEmail(data: VerifyEmailData): Promise<void> {
    await this.client.executePost<void>(
      this.client.createRoute('AUTH', 'VERIFY_EMAIL'),
      data,
      {
        withCredentials: true
      }
    );
  }

  async changePassword(data: ChangePasswordData): Promise<void> {
    await this.client.executePost<void>(
      this.client.createRoute('AUTH', 'CHANGE_PASSWORD'),
      data,
      {
        withCredentials: true
      }
    );
  }

  async resetPassword(data: ResetPasswordData): Promise<void> {
    await this.client.executePost<void>(
      this.client.createRoute('AUTH', 'RESET_PASSWORD'),
      data,
      {
        withCredentials: true
      }
    );
  }

  private handleAuthError(error: unknown): Error {
    if (isAuthError(error)) {
      const errorMessage = (error.response?.data?.error as ApiErrorDetail)?.message || 
                          error.response?.data?.message || 
                          'Authentication failed';
      return new Error(errorMessage);
    }
    return error instanceof Error ? error : new Error('An unexpected error occurred');
  }

  // Check authentication status by making a lightweight auth check request
  async isAuthenticated(): Promise<boolean> {
    try {
      await this.client.executeGet<void>(
        this.client.createRoute('AUTH', 'VERIFY'),
        {
          withCredentials: true
        }
      );
      return true;
    } catch (error) {
      return false;
    }
  }
}

export const authApi = new AuthApi();