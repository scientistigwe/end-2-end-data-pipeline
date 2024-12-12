// auth/types/rbac.ts
import type { Permission } from './permissions';
import type { RoleType } from './roles';

// Role-Based Access Control (RBAC) core types
export interface RBACRole {
  id: string;
  name: RoleType;
  description?: string;
  permissions: Permission[];
  parentRole?: RoleType; // For role inheritance
  priority: number; // For role precedence
}

// Role hierarchy management
export type RoleHierarchy = Record<RoleType, RoleType[]>;

// Role permissions mapping
export type RolePermissions = Record<RoleType, Permission[]>;

// RBAC Configuration
export interface RBACConfig {
  hierarchy: RoleHierarchy;
  permissions: RolePermissions;
  enforceHierarchy: boolean;
}

// RBAC Check Results
export interface RBACCheckResult {
  allowed: boolean;
  reason?: string;
  requiredPermissions?: Permission[];
  userPermissions?: Permission[];
}

// RBAC Operations
export interface RBACOperations {
  checkAccess: (userId: string, permission: Permission) => Promise<boolean>;
  getUserPermissions: (userId: string) => Promise<Permission[]>;
  getRolePermissions: (role: RoleType) => Permission[];
  hasRole: (userId: string, role: RoleType) => Promise<boolean>;
  inheritedPermissions: (role: RoleType) => Permission[];
}

// Default RBAC configuration
export const DEFAULT_ROLE_HIERARCHY: RoleHierarchy = {
  admin: ['manager', 'user'],
  manager: ['user'],
  user: []
};

// Helper functions
export const rbacHelpers = {
  isValidRole: (role: string): role is RoleType => {
    return Object.keys(DEFAULT_ROLE_HIERARCHY).includes(role);
  },
  
  getInheritedRoles: (role: RoleType): RoleType[] => {
    return DEFAULT_ROLE_HIERARCHY[role] || [];
  },
  
  combinePermissions: (roles: RoleType[], permissions: RolePermissions): Permission[] => {
    return [...new Set(roles.flatMap(role => permissions[role] || []))];
  }
};