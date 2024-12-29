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
  tokens: AuthTokens | null;
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

export interface LoginResponse {
  success: boolean;
  message: string;
  tokens: AuthTokens;
  user: User;
}

export interface RegisterResponse extends AuthApiResponse<{
  user: User;
  tokens: AuthTokens;
}> {}

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

// Profile Types
export interface ProfileUpdateData {
  firstName?: string;
  lastName?: string;
  email?: string;
  profileImage?: string;
}

// Session Types
export interface AuthSessionInfo extends BaseSessionInfo {
  deviceInfo?: string;
  ipAddress?: string;
}

// Context Type
export interface AuthContextType {
  user: User | null;
  error: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  register: (data: RegisterData) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<AuthTokens>;
  updateProfile: (data: ProfileUpdateData) => Promise<User>;
  changePassword: (data: ChangePasswordData) => Promise<void>;
  resetPassword: (data: ResetPasswordData) => Promise<void>;
  verifyEmail: (data: VerifyEmailData) => Promise<void>;
  handleAuthError: (error: unknown) => string;
}