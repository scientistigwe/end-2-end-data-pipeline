// auth/api/authApi.ts
import axios from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { HTTP_STATUS, ApiErrorResponse } from '@/common/types/api';
import type {
  LoginResponseData,
  RegisterResponseData,
  LoginApiResponse,
  RegisterApiResponse,
  AuthBaseResponse,
  isAuthError,
} from '../types/api';
import type {
  LoginCredentials,
  RegisterData,
  ProfileUpdateData,
  ChangePasswordData,
  ResetPasswordData,
  VerifyEmailData,
} from '../types/auth';
import type { User } from '@/common/types/user';

class AuthApi {
  private client = baseAxiosClient;

  constructor() {
    // Log the full base URL 
    console.log('Full Base URL:', this.client.getAxiosInstance().defaults.baseURL);
    
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
      // Log the exact route being used
      const loginRoute = this.client.createRoute('AUTH', 'LOGIN');
      console.log('Login Route:', loginRoute);
      console.log('Full Login URL:', `${this.client.getAxiosInstance().defaults.baseURL}${loginRoute}`);
      console.log('Login Credentials:', credentials);

      const response = await this.client.executePost<LoginApiResponse>(
        loginRoute,
        credentials,
        { 
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        }
      );
      
      console.log('Login Response:', response);
      
      window.dispatchEvent(new Event('auth:login'));
      return response.data;
    } catch (error) {
      console.error('Detailed Login Error:', {
        error,
        response: (error as any).response,
        message: (error as any).message
      });
      throw this.handleAuthError(error);
    }
  }


  async getProfile(): Promise<User> {
    try {
        const response = await this.client.executeGet<AuthBaseResponse<User>>(
            this.client.createRoute('AUTH', 'PROFILE'),
            { 
                withCredentials: true,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }
        );

        if (!response.data?.user) {
            throw new Error('Invalid profile response format');
        }
        return response.data.user;
    } catch (error) {
        console.error('Get profile error:', error);
        throw this.handleAuthError(error);
    }
  }

  private handleAuthError(error: unknown): Error {
    if (axios.isAxiosError(error)) {
        const errorResponse = error.response?.data as ApiErrorResponse;
        
        if (error.response?.status === HTTP_STATUS.UNAUTHORIZED) {
            // Check if the error response has a token_expired error code
            if (errorResponse?.error?.code === 'token_expired') {
                window.dispatchEvent(new Event('auth:token_expired'));
            } else {
                window.dispatchEvent(new Event('auth:logout'));
            }
            return new Error('Authentication failed. Please log in again.');
        }

        // Handle the error message based on the API error response structure
        return new Error(
            errorResponse?.error?.message || 
            errorResponse?.message || 
            'Authentication failed'
        );
    }
    return error instanceof Error ? error : new Error('An unexpected error occurred');
  }

  async refresh(): Promise<void> {
    try {
        await this.client.executePost<void>(
            this.client.createRoute('AUTH', 'REFRESH'),
            undefined,
            {
                withCredentials: true,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }
        );
        
        // Optional: Dispatch refresh success event
        window.dispatchEvent(new Event('auth:refresh'));
    } catch (error) {
        console.error('Token refresh error:', error);
        throw this.handleAuthError(error);
    }
  }
  
  async checkAuthStatus(): Promise<User | null> {
    try {
      const user = await this.getProfile();
      return user;
    } catch (error) {
      return null;
    }
  }

  async logout(): Promise<void> {
      try {
          await this.client.executePost<void>(
              this.client.createRoute('AUTH', 'LOGOUT'),
              undefined,
              { withCredentials: true }
          );
      } finally {
          window.dispatchEvent(new Event('auth:logout'));
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
      
      if (!response.data || !response.data.user) {
        console.error('Invalid response structure:', response);
        throw new Error('Invalid response format from server');
      }
      
      // Dispatch auth success event
      window.dispatchEvent(new Event('auth:register'));
      
      return response.data; // Return the data property
    } catch (error) {
      console.error('Registration API error details:', {
        error,
        response: (error as any).response?.data, // Type assertion to avoid unknown error
        status: (error as any).response?.status // Type assertion to avoid unknown error
      });
      throw this.handleAuthError(error);
    }
  }

  async updateProfile(data: ProfileUpdateData): Promise<User> {
    const response = await this.client.executePut<AuthBaseResponse<User>>(
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