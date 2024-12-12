// src/auth/types/auth.ts
import { User } from "../../common/types/user";

export type AuthStatus = 'authenticated' | 'unauthenticated' | 'loading';

  
export interface AuthTokens {
    accessToken: string | null;
    refreshToken: string | null;
    expiresIn: number | null;
  }
  

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

export interface AuthState {
    user: User | null;
    status: AuthStatus;
    error: string | null;
    tokens: AuthTokens;
    isLoading: boolean | null;
}

export type Permission = 
  | 'pipeline:view' 
  | 'pipeline:create' 
  | 'pipeline:edit' 
  | 'pipeline:delete'
  | 'pipeline:execute';
