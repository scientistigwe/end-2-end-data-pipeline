// src/auth/utils/rbac.ts
import type { Permission, RoleHierarchy, RolePermissions } from '../types/rbac';
import type { RoleType } from '../types/auth';

export const ROLE_HIERARCHY: RoleHierarchy = {
  admin: ['admin', 'manager', 'user'],
  manager: ['manager', 'user'],
  user: ['user']
} as const;

export const ROLE_PERMISSIONS: RolePermissions = {
  admin: [
    'view:users',
    'manage:users',
    'manage:roles',
    'manage:admins',
    'delete:users',
    'view:audit',
    'manage:settings'
  ],
  manager: [
    'view:users',
    'manage:users',
    'view:audit'
  ],
  user: [
    'view:profile',
    'manage:profile'
  ]
} as const;

export const isValidRole = (role: unknown): role is RoleType => {
  return typeof role === 'string' && Object.keys(ROLE_HIERARCHY).includes(role);
};

export const isValidPermission = (permission: unknown): permission is Permission => {
  return typeof permission === 'string' && 
    Object.values(ROLE_PERMISSIONS)
      .flat()
      .includes(permission as Permission);
};

export const checkRoleHierarchy = (userRole: RoleType, requiredRole: RoleType): boolean => {
  return ROLE_HIERARCHY[userRole]?.includes(requiredRole) ?? false;
};

export const getRolePermissions = (role: RoleType): Permission[] => {
  return [...ROLE_PERMISSIONS[role]];
};

export const hasPermission = (role: RoleType, permission: Permission): boolean => {
  return getRolePermissions(role).includes(permission);
};

export const getRolesWithPermission = (permission: Permission): RoleType[] => {
  return (Object.entries(ROLE_PERMISSIONS) as [RoleType, Permission[]][])
    .filter(([_, permissions]) => permissions.includes(permission))
    .map(([role]) => role);
};

export const isRoleSuperiorTo = (role1: RoleType, role2: RoleType): boolean => {
  return checkRoleHierarchy(role1, role2) && role1 !== role2;
};

export const getCombinedPermissions = (roles: RoleType[]): Permission[] => {
  const permissions = roles.flatMap(role => ROLE_PERMISSIONS[role]);
  return [...new Set(permissions)];
};

