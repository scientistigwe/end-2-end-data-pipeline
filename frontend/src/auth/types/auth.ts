// auth/types/auth.ts
import type { ApiResponse, ApiError } from '@/common/types/api';
import type { User } from '@/common/types/user';
import type { 
  BaseAuthError, 
  BaseSessionInfo, 
  BaseAuthContext,
  BaseLoginCredentials,
  BaseRegisterData,
  BaseAuthResponse
} from '@/common/types/auth';
import type { AxiosError } from 'axios';

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
  rememberMe?: boolean;
}

export interface RegisterData extends BaseRegisterData {
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
export interface LoginResponseData extends BaseAuthResponse {
  user: User;
  logged_in_at: string;
}

export interface RegisterResponseData extends BaseAuthResponse {
  user: User;
  registered_at: string;
}

// API Response Types
export interface ApiBaseResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
  error?: ApiErrorData;
  meta?: {
    timestamp: string;
    requestId?: string;
  };
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

export interface AuthApiError extends ApiError {
  details?: ValidationErrors;
}

// Session Types
export interface AuthSessionInfo extends BaseSessionInfo {
  deviceInfo?: string;
  ipAddress?: string;
}

// Context Types
export interface AuthContextValue extends BaseAuthContext {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isInitialized: boolean;

  // Auth operations
  login: (credentials: LoginCredentials) => Promise<boolean>;
  register: (data: RegisterData) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (data: ProfileUpdateData) => Promise<User>;
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