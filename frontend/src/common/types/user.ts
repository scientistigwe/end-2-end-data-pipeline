// src/common/types/user.ts
export type UserRole = 'user' | 'admin' | 'manager';
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
  preferences?: Record<string, unknown>;
  }
