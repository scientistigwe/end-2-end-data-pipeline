// auth/types/api.ts
import type { User } from '@/common/types/user';
import type { ApiResponse, ApiError, ApiMetadata } from '@/common/types/api';

// Auth-specific metadata
export interface AuthMetadata extends ApiMetadata {
    logged_in_at?: string;
    registered_at?: string;
    last_active?: string;
}

// auth/types/api.ts
// auth/types/api.ts
export interface LoginApiResponse {
  data: {
      data: {
          mfa_required: boolean;
          session_expires: string;
          tokens: {
              access_token: string;
              refresh_token: string;
          };
          user: {
              email: string;
              first_name: string;
              id: string;
              last_name: string;
              permissions: string[];
              role: string;
              status: string;
              username: string;
          };
      };
      message: string;
      success: boolean;
  };
  headers: AxiosHeaders;
  status: number;
  statusText: string;
}

export interface LoginResponseData {
  user: User;
  tokens: {
    access_token: string;
    refresh_token: string;
  };
  mfa_required: boolean;
  session_expires: string;
}

export interface RegisterResponseData {
    user: User;
    verification_email_sent: boolean;
}

// Extend base ApiResponse for auth-specific responses
export interface AuthApiResponse<T = unknown> extends ApiResponse<T> {
    meta?: AuthMetadata;
}

export type RegisterApiResponse = AuthApiResponse<{
    data: RegisterResponseData;
    message: string;
    success: boolean;
}>;

// Error Types
export interface AuthValidationError {
    field: string;
    message: string;
    code: string;
}

export interface AuthErrorDetail extends ApiError {
    validationErrors?: AuthValidationError[];
    field?: string;
    details?: Record<string, string[]>;
}

// Type Guards
export function isAuthError(error: unknown): error is AuthErrorDetail {
    return (
        typeof error === 'object' &&
        error !== null &&
        'code' in error &&
        'message' in error
    );
}

export function isAuthApiResponse<T>(response: unknown): response is AuthApiResponse<T> {
    return (
        typeof response === 'object' &&
        response !== null &&
        'success' in response &&
        'data' in response
    );
}

// Auth State Interface
export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: AuthErrorDetail | null;
    tokens?: {
        accessToken: string | null;
        refreshToken: string | null;
    };
    meta?: AuthMetadata;
}

// Auth Token Types
export interface AuthTokens {
    access_token: string;
    refresh_token: string;
}

// Auth Event Types
export type AuthEventType = 
    | 'LOGIN'
    | 'LOGOUT'
    | 'REGISTER'
    | 'REFRESH'
    | 'TOKEN_EXPIRED'
    | 'MFA_REQUIRED'
    | 'PROFILE_UPDATED';

export interface AuthEvent {
    type: AuthEventType;
    payload?: {
        userId?: string;
        message?: string;
        error?: AuthErrorDetail;
    };
}