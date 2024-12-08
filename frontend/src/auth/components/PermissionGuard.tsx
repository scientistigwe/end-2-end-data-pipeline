// src/auth/components/PermissionGuard.tsx
import React from 'react';
import { usePermissions } from '../hooks/usePermissions';
import type { Permission } from '../types/permissions';

interface PermissionGuardProps {
  permissions: Permission[];
  requireAll?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions,
  requireAll = true,
  children,
  fallback = null
}) => {
  const { hasAllPermissions, hasAnyPermission } = usePermissions();
  
  const hasAccess = requireAll
    ? hasAllPermissions(permissions)
    : hasAnyPermission(permissions);

  if (!hasAccess) return <>{fallback}</>;
  
  return <>{children}</>;
};
