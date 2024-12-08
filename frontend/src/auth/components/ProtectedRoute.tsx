// src/auth/components/ProtectedRoute.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { AUTH_ROUTES } from '../constants';
import type { Permission } from '../types/permissions';
import { PermissionGuard } from './PermissionGuard'; // Add this import

interface ProtectedRouteProps {
  children: React.ReactNode;
  permissions?: Permission[];
  requireAll?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  permissions = [],
  requireAll = true
}) => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to={AUTH_ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  if (permissions.length > 0) {
    return (
      <PermissionGuard
        permissions={permissions}
        requireAll={requireAll}
        fallback={<Navigate to="/" replace />}
      >
        {children}
      </PermissionGuard>
    );
  }

  return <>{children}</>;
};