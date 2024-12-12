// auth/types/api.ts
import type { ApiResponse, ApiError } from '@/common/types/api';
import type { User } from '@/common/types/user';
import type { LoginCredentials, RegisterData } from './auth';

// Auth-specific API responses
export interface AuthApiResponse<T = unknown> extends ApiResponse<T> {
  tokens?: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

// Login specific response
export interface LoginResponse extends AuthApiResponse<User> {
  tokens: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

// API Request types
export interface LoginRequest {
  credentials: LoginCredentials;
}

export interface RegisterRequest {
  userData: RegisterData;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface PasswordResetRequest {
  email: string;
  token: string;
  newPassword: string;
}

export interface RoleUpdateRequest {
  userId: string;
  roleId: string;
}

// API Error types specific to auth
export interface AuthApiError extends Omit<ApiError, 'code'> {
  code: 'INVALID_CREDENTIALS' | 'EMAIL_EXISTS' | 'TOKEN_EXPIRED' | 'INVALID_TOKEN';
}

// Response types for specific auth operations
export interface TokenValidationResponse {
  valid: boolean;
  expired: boolean;
}

export interface EmailVerificationResponse extends AuthApiResponse<void> {
  verified: boolean;
}

export interface PasswordChangeResponse extends AuthApiResponse<void> {
  success: boolean;
}