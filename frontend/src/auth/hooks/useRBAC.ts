// src/auth/hooks/useRBAC.ts
import { usePermissions } from './usePermissions';
import { checkRoleHierarchy, getRolePermissions, isValidRole } from '../utils/rbac';
import type { User, RoleType } from '../types/auth';
import type { Permission } from '../types/rbac';

export const useRBAC = () => {
  const { role, permissions } = usePermissions();
  
  // Add type assertion or validation
  const validRole = role && isValidRole(role) ? role : undefined;

  const canManageUser = (targetUser: User) => {
    if (!validRole || !targetUser.role) return false;
    
    const canManageRole = checkRoleHierarchy(validRole, targetUser.role);
    if (!canManageRole) return false;

    return permissions.includes('manage:users');
  };

  const canAssignRole = (targetRole: RoleType) => {
    if (!validRole) return false;

    const canManageRole = checkRoleHierarchy(validRole, targetRole);
    if (!canManageRole) return false;

    return permissions.includes('manage:roles');
  };

  const canAccessFeature = (featurePermission: Permission) => {
    if (!validRole) return false;

    if (permissions.includes(featurePermission)) return true;

    const rolePermissions = getRolePermissions(validRole);
    return rolePermissions.includes(featurePermission);
  };

  return {
    canManageUser,
    canAssignRole,
    canAccessFeature,
  } as const;
};