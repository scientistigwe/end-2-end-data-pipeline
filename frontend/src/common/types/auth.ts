// common/types/auth.ts
import type { RoleType } from './user';

// Base Auth User Type (core user properties)
export interface BaseAuthUser {
  id: string;
  email: string;
  username?: string;
  firstName: string;
  lastName: string;
  role: RoleType;
  permissions: string[];
  profileImage?: string;
  status: 'active' | 'inactive' | 'suspended';
  createdAt: string;
  updatedAt: string;
  lastLogin?: string;
  preferences?: Record<string, unknown>;
}

// Base Permission and Role Types
export type BasePermission = {
  id: string;
  name: string;
  description?: string;
};

export type BaseRole = {
  id: string;
  name: RoleType;
  description?: string;
  createdAt: string;
  updatedAt: string;
};

// Permission Check Interface
export interface BasePermissionCheck {
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
}

// Base Request Types
export interface BaseLoginCredentials {
  email: string;
  password: string;
}

export interface BaseRegisterData extends BaseLoginCredentials {
  username: string;
  firstName: string;
  lastName: string;
}

export interface BaseProfileUpdate {
  firstName?: string;
  lastName?: string;
  profileImage?: string;
  preferences?: Record<string, unknown>;
}

// Base Response Types
export interface BaseAuthResponse {
  success: boolean;
  message?: string;
  timestamp: string;
}

export interface BaseLoginResponse extends BaseAuthResponse {
  user: BaseAuthUser;
}

export interface BaseRegisterResponse extends BaseAuthResponse {
  user: BaseAuthUser;
}

// Error Types
export interface BaseAuthError {
  code: string;
  message: string;
  status: number;
}

// Session Types
export interface BaseSessionInfo {
  isActive: boolean;
  lastActive: string;
  expiresAt?: string;
}

// Context Types
export interface BaseAuthContext {
  user: BaseAuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (credentials: BaseLoginCredentials) => Promise<boolean>;
  register: (data: BaseRegisterData) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (data: BaseProfileUpdate) => Promise<BaseAuthUser>;
}