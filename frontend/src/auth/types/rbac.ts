// src/auth/types/rbac.ts
import { RoleType } from './auth';

export type Permission =
  | 'view:users'
  | 'manage:users'
  | 'manage:roles'
  | 'manage:admins'
  | 'delete:users'
  | 'view:audit'
  | 'manage:settings'
  | 'view:profile'
  | 'manage:profile';

export type RoleHierarchy = Record<RoleType, RoleType[]>;
export type RolePermissions = Record<RoleType, Permission[]>;

