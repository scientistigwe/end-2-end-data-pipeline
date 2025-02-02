// src/auth/types/auth.ts

import type { 
  BaseAuthError, 
  BaseSessionInfo, 
  BaseAuthContext,
  BaseLoginCredentials,
  BaseRegisterData,
  BaseLoginResponse,
  BaseRegisterResponse,
  BaseProfileUpdate
} from '@/common/types/auth';
import type { ApiResponse } from '@/common/types/api';
import type { User } from '@/common/types/user';

// Auth Status
export type AuthStatus = 'authenticated' | 'unauthenticated' | 'loading';

// State Types
export interface AuthState {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  isLoading: boolean;
  initialized: boolean;
}

// Request Types
export interface LoginCredentials extends BaseLoginCredentials {
  remember_me?: boolean;
  device_info?: Record<string, any>;
  mfa_code?: string;
}

// RegisterData now just adds optional fields to BaseRegisterData
export interface RegisterData extends BaseRegisterData {
  metadata?: Record<string, any>;
}

// ProfileUpdateData uses the same structure as BaseProfileUpdate
export type ProfileUpdateData = BaseProfileUpdate;

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ResetPasswordData {
  token: string;
  new_password: string;
  confirm_password: string;
}

export interface VerifyEmailData {
  token: string;
}

// Response Types
export interface LoginResponseData extends BaseLoginResponse {
  tokens: {
    access_token: string;
    refresh_token: string;
  };
  mfa_required?: boolean;
  session_expires?: string;
  permitted_actions?: string[];
}

export interface RegisterResponseData extends BaseRegisterResponse {
  tokens: {
    access_token: string;
    refresh_token: string;
  };
  verification_email_sent: boolean;
  next_steps?: string[];
}

// API Response Types
export interface AuthBaseResponse<T = any> extends ApiResponse<T> {}

export type LoginApiResponse = AuthBaseResponse<LoginResponseData>;
export type RegisterApiResponse = AuthBaseResponse<RegisterResponseData>;

// Error Types
export interface ValidationErrors {
  [field: string]: string[];
}

export interface AuthApiError extends BaseAuthError {
  details?: ValidationErrors;
}

// Session Types
export interface AuthSessionInfo extends BaseSessionInfo {
  device_info?: string;
  ip_address?: string;
}

// Context Types - Now uses generics properly
export interface AuthContextValue extends BaseAuthContext<
  LoginCredentials,
  RegisterData,
  ProfileUpdateData,
  User
> {
  // Additional state
  status: AuthStatus;
  isInitialized: boolean;

  // Extended auth operations
  changePassword: (data: ChangePasswordData) => Promise<boolean>;
  resetPassword: (data: ResetPasswordData) => Promise<boolean>;
  verifyEmail: (data: VerifyEmailData) => Promise<boolean>;

  // Loading states
  isLoggingIn: boolean;
  isRegistering: boolean;
  isUpdatingProfile: boolean;
  isChangingPassword: boolean;
  isResettingPassword: boolean;
  isVerifyingEmail: boolean;
}

// Type Guards
export function isAuthError(error: unknown): error is AuthApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error &&
    'status' in error
  );
}