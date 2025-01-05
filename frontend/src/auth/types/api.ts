// auth/types/api.ts
import type { User } from '@/common/types/user';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens, 
  AuthValidationErrors 
} from './auth';

// Base API Response Structure
export interface ApiBaseResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
  status?: number;
}

// Error Types
export interface ApiErrorDetail {
  code: number;
  description: string;
  name: string;
  message: string;
}

export interface ApiErrorResponse {
  success: false;
  message: string;
  error?: ApiErrorDetail;
  details?: AuthValidationErrors;
}

// Auth Response Types
interface BaseAuthResponse {
  user: User;
  tokens: AuthTokens;
}

interface LoginResponseData extends BaseAuthResponse {
  logged_in_at: string;
}

interface RegisterResponseData extends BaseAuthResponse {
  registered_at: string;
}

export type LoginApiResponse = ApiBaseResponse<LoginResponseData>;
export type RegisterApiResponse = ApiBaseResponse<RegisterResponseData>;

// Auth Request Types
export interface LoginRequest extends LoginCredentials {
  rememberMe?: boolean;
}

export interface RegisterRequest extends RegisterData {}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// Auth Error Types
export interface AuthApiError extends Error {
  response: {
    data: ApiErrorResponse;
    status: number;
  };
}

// Generic Auth API Response Type
export interface AuthApiResponse<T = unknown> extends ApiBaseResponse<T> {
  tokens?: AuthTokens;
}

// Response Type Guards
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
): response is AuthApiResponse<T> {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    'data' in response &&
    Boolean(response.success)
  );
}