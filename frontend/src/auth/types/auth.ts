// auth/types/auth.ts
import type { User } from '@/common/types/user';
import type { Role } from './roles';

// Core auth status
export type AuthStatus = 'authenticated' | 'unauthenticated' | 'loading';

// Token management
export interface AuthTokens {
  accessToken: string | null;
  refreshToken: string | null;
  expiresIn: number | null;
}

// Core auth state interface
export interface AuthState {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  tokens: AuthTokens;
  isLoading: boolean;
  initialized: boolean;
}

// Authentication operations
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  username?: string;
}

// Password management
export interface PasswordOperations {
  resetPassword: {
    email: string;
    token: string;
    newPassword: string;
  };
  changePassword: {
    currentPassword: string;
    newPassword: string;
  };
  verifyPassword: {
    password: string;
  };
}

// Session management
export interface SessionInfo {
  lastActive: string;
  deviceInfo?: string;
  ipAddress?: string;
}

// Auth preferences
export interface AuthPreferences {
  enableTwoFactor: boolean;
  notifyOnNewLogin: boolean;
  sessionTimeout?: number;
}

// Auth events for tracking
export type AuthEventType = 
  | 'login' 
  | 'logout' 
  | 'password_reset' 
  | 'token_refresh'
  | 'session_expired';

export interface AuthEvent {
  type: AuthEventType;
  timestamp: string;
  userId?: string;
  metadata?: Record<string, any>;
}

export interface ResetPasswordData {
  email: string;
  token: string;
  newPassword: string;
}

export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
}

export interface VerifyEmailData {
  token: string;
}