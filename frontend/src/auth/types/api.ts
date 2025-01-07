// auth/types/api.ts
import type { User } from '@/common/types/user';
import type { 
  ApiResponse, 
  ApiError,
  ApiErrorResponse,
  ValidationError 
} from '@/common/types/api';
import type { 
  LoginCredentials, 
  RegisterData, 
  ValidationErrors 
} from './auth';

// Auth-specific API Response Types
export interface AuthBaseResponse<T = unknown> extends ApiResponse<T> {
  user: User;
}

// Auth-specific Response Data Types
export interface BaseAuthResponse {
  user: User;
}

export interface LoginResponseData extends BaseAuthResponse {
  logged_in_at: string;
}

export interface RegisterResponseData extends BaseAuthResponse {
  registered_at: string;
}

// Auth-specific API Response Types
export type LoginApiResponse = AuthBaseResponse<LoginResponseData>;
export type RegisterApiResponse = AuthBaseResponse<RegisterResponseData>;

// Auth-specific Error Types
export interface AuthApiError extends ApiError {
  response: {
    data: ApiErrorResponse;
    status: number;
  };
}

// Auth-specific Request Types
export interface LoginRequest extends LoginCredentials {
  rememberMe?: boolean;
}

export interface RegisterRequest extends RegisterData {}

// Type Guards
export function isAuthError(error: unknown): error is AuthApiError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'response' in error &&
    typeof (error as any).response?.data === 'object' &&
    !(error as any).response?.data?.success
  );
}

export function isValidAuthResponse<T>(
  response: unknown
): response is AuthBaseResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    'data' in response &&
    'user' in response &&
    Boolean(response.success)
  );
}