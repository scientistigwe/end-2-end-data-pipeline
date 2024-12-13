// auth/hooks/useRBAC.ts
import { useMemo } from 'react';
import { usePermissions } from './usePermissions';
import type { User } from '@/common/types/user';
import type { Permission, RoleType } from '../types';
import { CORE_PERMISSIONS } from '../types/permissions';

export interface RBACCheckOptions {
 requireAll?: boolean;
 checkHierarchy?: boolean;
}

export function useRBAC() {
 const { permissions, hasPermission } = usePermissions();

 // Check if user can manage another user based on roles and permissions
 const canManageUser = useMemo(() => 
   (targetUser: User, options: RBACCheckOptions = {}): boolean => {
     // Super admin can manage all users
     if (permissions.includes(CORE_PERMISSIONS.MANAGE_ALL)) return true;

     // Must have basic user management permission
     if (!hasPermission(CORE_PERMISSIONS.MANAGE_USERS)) return false;

     // Additional role-specific logic could be added here
     return true;
   },
   [permissions, hasPermission]
 );

 // Check if user can perform specific role operations
 const canManageRole = useMemo(() => 
   (targetRole: RoleType, operation: 'assign' | 'modify' | 'delete'): boolean => {
     // Super admin can manage all roles
     if (permissions.includes(CORE_PERMISSIONS.MANAGE_ALL)) return true;

     // Must have role management permission
     if (!hasPermission(CORE_PERMISSIONS.MANAGE_ROLES)) return false;

     // Additional role-specific checks could be added here
     return true;
   },
   [permissions, hasPermission]
 );

 // Check if user can access specific features
 const canAccessFeature = useMemo(() => 
   (requiredPermissions: Permission | Permission[], options: RBACCheckOptions = {}): boolean => {
     const { requireAll = false } = options;

     // Convert single permission to array
     const permissionsToCheck = Array.isArray(requiredPermissions) 
       ? requiredPermissions 
       : [requiredPermissions];

     // Super admin can access all features
     if (permissions.includes(CORE_PERMISSIONS.MANAGE_ALL)) return true;

     return requireAll
       ? permissionsToCheck.every(perm => hasPermission(perm))
       : permissionsToCheck.some(perm => hasPermission(perm));
   },
   [permissions, hasPermission]
 );

 // Check general resource access
 const canAccessResource = useMemo(() => 
   (resource: string, action: 'view' | 'create' | 'edit' | 'delete'): boolean => {
     const permission = `${action}:${resource}` as Permission;
     return hasPermission(permission);
   },
   [hasPermission]
 );

 return {
   canManageUser,
   canManageRole,
   canAccessFeature,
   canAccessResource
 } as const;
}

