import axios from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { HTTP_STATUS, ApiErrorResponse } from '@/common/types/api';
import { APIRoutes } from '@/common/api/routes';
import type {
    LoginResponseData,
    RegisterResponseData,
    LoginApiResponse,
    RegisterApiResponse,
    AuthBaseResponse,
} from '../types/api';
import type {
    LoginCredentials,
    RegisterData,
    ProfileUpdateData,
    ChangePasswordData,
    ResetPasswordData,
    VerifyEmailData,
    ForgotPasswordData,
    MFASetupData,
    MFAVerifyData
} from '../types/auth';
import type { User } from '@/common/types/user';

/**
 * Constants for API configuration and events
 */
const DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
} as const;

const AUTH_EVENTS = {
    LOGIN: 'auth:login',
    LOGOUT: 'auth:logout',
    REGISTER: 'auth:register',
    REFRESH: 'auth:refresh',
    TOKEN_EXPIRED: 'auth:token_expired',
    PASSWORD_RESET: 'auth:password_reset',
    EMAIL_VERIFIED: 'auth:email_verified',
    MFA_REQUIRED: 'auth:mfa_required',
    MFA_SETUP_COMPLETE: 'auth:mfa_setup_complete',
    PROFILE_UPDATED: 'auth:profile_updated'
} as const;

/**
 * Custom error class for authentication errors
 */
class AuthError extends Error {
    constructor(
        message: string,
        public readonly code?: string,
        public readonly status?: number,
        public readonly details?: Record<string, any>
    ) {
        super(message);
        this.name = 'AuthError';
    }
}

/**
 * Main AuthApi class that handles all authentication-related API calls
 */
import { ROUTES } from '@/routes';  // Import your routes


class AuthApi {
  private readonly client = baseAxiosClient;
  private navigate: any; 
  // Add method to set navigate function
  setNavigate(navigate: any) {
    this.navigate = navigate;
}
    private readonly defaultConfig = {
        withCredentials: true,
        headers: DEFAULT_HEADERS
    };

    constructor() {
        this.initializeClient();
    }

    /**
     * Initialize the API client with proper configuration
     */
    private initializeClient(): void {
        this.client.setServiceConfig({
            service: ServiceType.AUTH,
            headers: DEFAULT_HEADERS
        });

        const axiosInstance = this.client.getAxiosInstance();
        console.debug('Auth API Base URL:', axiosInstance.defaults.baseURL);
    }

    /**
     * Emit authentication-related events
     */
    private emitAuthEvent(eventType: keyof typeof AUTH_EVENTS, detail?: any): void {
        const event = detail 
            ? new CustomEvent(AUTH_EVENTS[eventType], { detail })
            : new Event(AUTH_EVENTS[eventType]);
        window.dispatchEvent(event);
    }

    /**
     * Generic request handler with proper error handling
     */
    private async request<T>(
      method: 'get' | 'post' | 'put' | 'delete',
      mainRoute: keyof typeof APIRoutes.AUTH,
      nestedRoute?: string,
      data?: unknown,
      config: { withCredentials?: boolean; headers?: Record<string, string> } = {}
  ): Promise<T> {
      const finalConfig = {
          ...this.defaultConfig,
          ...config,
          headers: {
              ...this.defaultConfig.headers,
              ...config.headers
          }
      };
  
      console.log('Making request with:', {
          method,
          mainRoute,
          nestedRoute,
          config: finalConfig
      });
  
      try {
          let response;
          if (nestedRoute) {
              response = await this.client.postToNested<T>(
                  'AUTH',
                  mainRoute,
                  nestedRoute,
                  data,
                  undefined,
                  finalConfig
              );
          } else {
              response = await this.client[method]<T>(
                  'AUTH',
                  mainRoute,
                  data,
                  undefined,
                  finalConfig
              );
          }
          
          console.log('Request successful, response:', response);
          return response;
      } catch (error) {
          console.error('Request failed:', { 
              method, 
              mainRoute, 
              nestedRoute, 
              error,
              errorType: error.constructor.name
          });
          throw this.handleAuthError(error);
      }
  }

    /**
     * Authentication Methods
     */
    async login(credentials: LoginCredentials): Promise<LoginResponseData> {
      try {
          const response = await this.request<LoginApiResponse>(
              'post',
              'LOGIN',
              undefined,
              credentials
          );
  
          // The response itself is the data we need
          const responseData = response;  // Changed from response?.data?.data
          
          if (!responseData || !responseData.tokens || !responseData.user) {
              console.error('Response validation failed:', {
                  hasResponseData: !!responseData,
                  hasUser: !!responseData?.user,
                  hasTokens: !!responseData?.tokens,
                  fullResponse: responseData
              });
              throw new AuthError(
                  'Invalid login response format', 
                  'INVALID_RESPONSE',
                  undefined,
                  { received: responseData }
              );
          }
  
          this.emitAuthEvent('LOGIN', { userId: responseData.user.id });
          return responseData;
      } catch (error) {
          console.error('Login failed:', error);
          throw this.handleAuthError(error);
      }
  }

  async register(data: RegisterData): Promise<RegisterResponseData> {
    try {
        this.validateRegistrationData(data);
        const requestData = this.prepareRegistrationData(data);

        const response = await this.request<RegisterResponseData>(
            'post',
            'REGISTER',
            undefined,
            requestData
        );

        // Access response directly like we did with login
        if (!response || !response.user) {
            console.error('Registration validation failed:', {
                hasResponse: !!response,
                hasUser: !!response?.user,
                fullResponse: response
            });
            throw new AuthError(
                'Registration failed', 
                'REGISTRATION_FAILED',
                undefined,
                { received: response }
            );
        }

        // Emit register event
        this.emitAuthEvent('REGISTER', { userId: response.user.id });

        // Navigate to dashboard
        if (this.navigate) {
            this.navigate(ROUTES.DASHBOARD);
        }

        return response;
    } catch (error) {
        console.error('Registration failed:', error);
        throw this.handleAuthError(error);
    }
}
  
    async logout(): Promise<void> {
        try {
            await this.request<void>('post', 'LOGOUT');
            this.emitAuthEvent('LOGOUT');
        } catch (error) {
            console.error('Logout failed:', error);
            // Still emit logout event even if the API call fails
            this.emitAuthEvent('LOGOUT');
            throw error;
        }
    }

    /**
     * Profile Methods
     */
    async getProfile(): Promise<User> {
        try {
            const response = await this.request<AuthBaseResponse<User>>(
                'get',
                'PROFILE',
                'GET'
            );

            if (!response.data?.user) {
                throw new AuthError('Invalid profile response format');
            }
            return response.data.user;
        } catch (error) {
            console.error('Get profile failed:', error);
            throw error;
        }
    }

    async updateProfile(data: ProfileUpdateData): Promise<User> {
        const response = await this.request<AuthBaseResponse<User>>(
            'put',
            'PROFILE',
            'UPDATE',
            data
        );
        
        if (!response.data) {
            throw new AuthError('Invalid profile update response format');
        }

        this.emitAuthEvent('PROFILE_UPDATED', { user: response.data });
        return response.data;
    }

    /**
     * Email Verification Methods
     */
    async verifyEmail(data: VerifyEmailData): Promise<void> {
        await this.request<void>(
            'post',
            'EMAIL',
            'VERIFY',
            data
        );
        this.emitAuthEvent('EMAIL_VERIFIED');
    }

    async resendVerificationEmail(email: string): Promise<void> {
        await this.request<void>(
            'post',
            'EMAIL',
            'RESEND',
            { email }
        );
    }

    /**
     * Password Management Methods
     */
    async changePassword(data: ChangePasswordData): Promise<void> {
        await this.request<void>(
            'post',
            'PASSWORD',
            'CHANGE',
            data
        );
    }

    async forgotPassword(data: ForgotPasswordData): Promise<void> {
        await this.request<void>(
            'post',
            'PASSWORD',
            'FORGOT',
            data
        );
    }

    async resetPassword(data: ResetPasswordData): Promise<void> {
        await this.request<void>(
            'post',
            'PASSWORD',
            'RESET',
            data
        );
        this.emitAuthEvent('PASSWORD_RESET');
    }

    /**
     * MFA (Multi-Factor Authentication) Methods
     */
    async setupMFA(data: MFASetupData): Promise<void> {
        const response = await this.request<void>(
            'post',
            'MFA',
            'SETUP',
            data
        );
        this.emitAuthEvent('MFA_SETUP_COMPLETE');
        return response;
    }

    async verifyMFA(data: MFAVerifyData): Promise<void> {
        await this.request<void>(
            'post',
            'MFA',
            'VERIFY',
            data
        );
    }

    /**
     * Token Management Methods
     */
    async refresh(): Promise<void> {
        try {
            await this.request<void>('post', 'REFRESH');
            this.emitAuthEvent('REFRESH');
        } catch (error) {
            console.error('Token refresh error:', error);
            throw error;
        }
    }

    async isAuthenticated(): Promise<boolean> {
        try {
            await this.request<void>('get', 'VERIFY');
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Helper Methods
     */
    private validateRegistrationData(data: RegisterData): void {
      const validations = {
          email: data.email?.trim() ? null : 'Email is required',
          password: data.password ? null : 'Password is required',
          confirm_password: data.confirm_password ? null : 'Password confirmation is required',
          passwords_match: data.password === data.confirm_password ? null : 'Passwords do not match',
          username: data.username?.trim() ? null : 'Username is required',
          first_name: data.first_name?.trim() ? null : 'First name is required',
          last_name: data.last_name?.trim() ? null : 'Last name is required',
          terms: data.terms_accepted ? null : 'Terms must be accepted'
      };
  
      const errors = Object.values(validations).filter(Boolean);
      if (errors.length > 0) {
          throw new AuthError(
              `Validation failed: ${errors.join(', ')}`,
              'VALIDATION_ERROR'
          );
      }
    }


    private prepareRegistrationData(data: RegisterData) {
        return {
            email: data.email?.trim(),
            password: data.password,
            confirm_password: data.confirm_password,
            username: data.username?.trim().toLowerCase(),
            first_name: data.first_name?.trim(),
            last_name: data.last_name?.trim(),
            terms_accepted: Boolean(data.terms_accepted),
            timezone: data.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
            locale: data.locale || navigator.language,
        };
    }

    private handleAuthError(error: unknown): Error {
        if (axios.isAxiosError(error)) {
            const errorResponse = error.response?.data as ApiErrorResponse;
            const status = error.response?.status;
            
            if (status === HTTP_STATUS.UNAUTHORIZED) {
                const errorCode = errorResponse?.error?.code;
                
                if (errorCode === 'token_expired') {
                    this.emitAuthEvent('TOKEN_EXPIRED');
                } else if (errorCode === 'mfa_required') {
                    this.emitAuthEvent('MFA_REQUIRED');
                } else {
                    this.emitAuthEvent('LOGOUT');
                }

                return new AuthError(
                    'Authentication failed. Please log in again.',
                    errorCode,
                    status
                );
            }

            if (errorResponse?.error?.details) {
                return new AuthError(
                    errorResponse.error.message || 'Validation error',
                    errorResponse.error.code,
                    status,
                    errorResponse.error.details
                );
            }

            return new AuthError(
                errorResponse?.error?.message || 
                errorResponse?.message || 
                'Authentication failed',
                errorResponse?.error?.code,
                status
            );
        }

        return error instanceof Error ? error : new AuthError('An unexpected error occurred');
    }
}

// Export singleton instance
export const authApi = new AuthApi();