// auth/hooks/usePermissions.ts
import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { selectUser, selectUserPermissions } from '../store/selectors';
import { CORE_PERMISSIONS } from '../types/permissions';
import type { Permission } from '../types';

export interface UsePermissionsReturn {
  permissions: Permission[];
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
}

export function usePermissions(): UsePermissionsReturn {
  const user = useSelector(selectUser);
  // Cast the permissions to Permission[] type since we know they're valid
  const userPermissions = useSelector(selectUserPermissions) as Permission[];

  const isSuperAdmin = useMemo(() => 
    userPermissions.includes(CORE_PERMISSIONS.MANAGE_ALL),
    [userPermissions]
  );

  const hasPermission = useMemo(() => 
    (permission: Permission): boolean => {
      if (!user) return false;
      if (isSuperAdmin) return true;
      return userPermissions.includes(permission);
    },
    [user, userPermissions, isSuperAdmin]
  );

  const hasAnyPermission = useMemo(() => 
    (requiredPermissions: Permission[]): boolean => {
      if (!user) return false;
      if (isSuperAdmin) return true;
      return requiredPermissions.some(permission => 
        userPermissions.includes(permission)
      );
    },
    [user, userPermissions, isSuperAdmin]
  );

  const hasAllPermissions = useMemo(() => 
    (requiredPermissions: Permission[]): boolean => {
      if (!user) return false;
      if (isSuperAdmin) return true;
      return requiredPermissions.every(permission => 
        userPermissions.includes(permission)
      );
    },
    [user, userPermissions, isSuperAdmin]
  );

  return {
    permissions: userPermissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions
  };
}