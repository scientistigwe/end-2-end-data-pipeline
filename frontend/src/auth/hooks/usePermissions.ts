// src/auth/hooks/usePermissions.ts
import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { selectUser, selectUserPermissions, selectUserRole } from '../store/selectors';
import { USER_ROLES } from '../constants';
import type { Permission } from '../types/permissions';
import { RoleType } from '../types/auth';

export interface UsePermissionsReturn {
  role: string | undefined;
  permissions: string[];
  isAdmin: boolean;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
  checkPermissions: (config: {
    permissions: Permission[];
    requireAll?: boolean;
  }) => boolean;
}

export function usePermissions(): UsePermissionsReturn {
  const user = useSelector(selectUser);
  const role = useSelector(selectUserRole) as RoleType | undefined;
  const permissions = useSelector(selectUserPermissions);
  
  const isAdmin = useMemo(() => role === USER_ROLES.ADMIN, [role]);

  const hasPermission = useMemo(() => 
    (permission: Permission): boolean => {
      if (!user) return false;
      if (isAdmin) return true;
      return permissions.includes(permission);
    },
    [user, isAdmin, permissions]
  );

  const hasAnyPermission = useMemo(() => 
    (requiredPermissions: Permission[]): boolean => {
      if (!user) return false;
      if (isAdmin) return true;
      return requiredPermissions.some(permission => 
        hasPermission(permission)
      );
    },
    [user, isAdmin, hasPermission]
  );

  const hasAllPermissions = useMemo(() => 
    (requiredPermissions: Permission[]): boolean => {
      if (!user) return false;
      if (isAdmin) return true;
      return requiredPermissions.every(permission => 
        hasPermission(permission)
      );
    },
    [user, isAdmin, hasPermission]
  );

  const checkPermissions = useMemo(() => 
    ({ permissions: requiredPermissions, requireAll = true }: {
      permissions: Permission[];
      requireAll?: boolean;
    }): boolean => {
      if (!user) return false;
      if (isAdmin) return true;
      return requireAll 
        ? hasAllPermissions(requiredPermissions)
        : hasAnyPermission(requiredPermissions);
    },
    [user, isAdmin, hasAllPermissions, hasAnyPermission]
  );

  return {
    role,
    permissions,
    isAdmin,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    checkPermissions
  };
}

