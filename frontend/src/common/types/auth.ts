// src/common/types/auth.ts

import type { RoleType } from './user';

// Base Auth User Type
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

// Base Request Types
export interface BaseLoginCredentials {
  email: string;
  password: string;
}

// Make BaseRegisterData include all possible fields
export interface BaseRegisterData {
  email: string;
  password: string;
  confirm_password: string;  // Added here
  username: string;
  first_name: string;
  last_name: string;
  terms_accepted: boolean;   // Added here
  phone_number?: string;
  department?: string;
  timezone?: string;
  locale?: string;
  metadata?: Record<string, any>;
}

export interface BaseProfileUpdate {
  first_name?: string;
  last_name?: string;
  profile_image?: string;
  phone_number?: string;
  department?: string;
  timezone?: string;
  locale?: string;
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

// Context Types - Make methods generic
export interface BaseAuthContext<
  TLoginCreds = BaseLoginCredentials,
  TRegisterData = BaseRegisterData,
  TProfileUpdate = BaseProfileUpdate,
  TUser = BaseAuthUser
> {
  user: TUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (credentials: TLoginCreds) => Promise<boolean>;
  register: (data: TRegisterData) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (data: TProfileUpdate) => Promise<TUser>;
}