// src/auth/types/auth.ts
export type UserRole = 'user' | 'admin' | 'manager';
export type AuthStatus = 'authenticated' | 'unauthenticated' | 'loading';
export type RoleType = 'admin' | 'manager' | 'user';

export interface User {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: RoleType;
    permissions: string[];
    profileImage?: string;
    lastLogin?: string;
    createdAt: string;
}

export interface AuthTokens {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
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
    tokens: {
        accessToken: string | null;
        refreshToken: string | null;
    };
}



export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  permissions: string[];
  profileImage?: string;
  lastLogin?: string;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

