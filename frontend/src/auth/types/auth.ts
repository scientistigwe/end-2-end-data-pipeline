// frontend\src\auth\types\auth.ts
import type { ApiResponse, ApiError } from '@/common/types/api';
import type { User } from '@/common/types/user';
import type { BaseSessionInfo } from '@/common/types/auth';
import type { AxiosError } from 'axios';

// Auth Tokens Interface
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Auth Status and State
export type AuthStatus = 'authenticated' | 'unauthenticated' | 'loading';

export interface AuthState {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  isLoading: boolean;
  initialized: boolean;
}

// Request Types
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  username: string;
  firstName: string;
  lastName: string;
  phoneNumber?: string;
  department?: string;
  timezone?: string;
  locale?: string;
  preferences?: Record<string, any>;
}

export interface ProfileUpdateData {
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  department?: string;
  timezone?: string;
  locale?: string;
  profileImage?: string;
  preferences?: Record<string, any>;
}

export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
}

export interface ResetPasswordData {
  token: string;
  newPassword: string;
}

export interface VerifyEmailData {
  token: string;
}

// Response Types
export interface AuthBaseResponse {
  success: boolean;
  message: string;
}

export interface AuthResponse extends AuthBaseResponse {
  data: {
    user: User;
    tokens: AuthTokens;
  };
}

export interface AuthApiResponse<T> extends ApiResponse<T> {
  success: boolean;
  message: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Request Types
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  username: string;
  firstName: string;
  lastName: string;
}

// Response Types
export interface LoginResponseData {
  user: User;
  logged_in_at: string;
}

export interface RegisterResponseData {
  user: User;
  registered_at: string;
}

export interface RegisterApiResponse {
  user: User;
  tokens: AuthTokens;
  registered_at: string;
}

export interface LoginApiResponse {
  user: User;
  tokens: AuthTokens;
  logged_in_at: string;
}

export type LoginResponse = ApiResponse<LoginResponseData>;
export type RegisterResponse = ApiResponse<RegisterResponseData>;

// Error Types
export interface ValidationErrors {
  [field: string]: string[];
}

export interface ApiErrorData {
  success: false;
  message: string;
  error?: {
    details?: ValidationErrors;
    code?: string;
  };
}

export type AuthAxiosError = AxiosError<ApiErrorData>;

export interface AuthValidationErrors {
  [field: string]: string[];
}

export interface AuthApiError extends ApiError {
  details?: AuthValidationErrors;
}

export interface AuthErrorResponse {
  response: {
    data: {
      success: false;
      message: string;
      error?: AuthApiError;
    };
    status: number;
  };
}

// Session Types
export interface AuthSessionInfo extends BaseSessionInfo {
  deviceInfo?: string;
  ipAddress?: string;
}

// Context Type
export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (credentials: LoginCredentials) => Promise<LoginResponseData>;
  register: (data: RegisterData) => Promise<RegisterResponseData>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<User>;
  
  isLoggingIn: boolean;
  isRegistering: boolean;
  isUpdatingProfile: boolean;
}
