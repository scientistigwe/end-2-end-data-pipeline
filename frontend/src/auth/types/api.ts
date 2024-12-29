// auth/types/api.ts
import type { User } from '@/common/types/user';
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens, 
  AuthValidationErrors 
} from './auth';

// Base API Response types
export interface ApiBaseResponse {
  success: boolean;
  message?: string;
}

export interface ApiErrorDetail {
  code: number;
  description: string;
  name: string;
}

export interface ApiErrorResponse extends ApiBaseResponse {
  error?: ApiErrorDetail;
  details?: AuthValidationErrors;
}

// Auth API Responses
export interface AuthApiResponse<T = unknown> extends ApiBaseResponse {
  data?: T;
  tokens?: AuthTokens;
}

export interface LoginApiResponse extends AuthApiResponse {
  user: User;
  tokens: AuthTokens;
}

export interface RegisterApiResponse extends AuthApiResponse {
  user: User;
  tokens: AuthTokens;
}

// Request types
export interface LoginRequest extends LoginCredentials {
  rememberMe?: boolean;
}

export interface RegisterRequest extends RegisterData {}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// Error type
export interface AuthApiError extends Error {
  response: {
    data: ApiErrorResponse;
    status: number;
  };
}