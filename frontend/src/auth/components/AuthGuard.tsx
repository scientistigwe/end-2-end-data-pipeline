// auth/components/AuthGuard.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStatus } from '../hooks/useAuthStatus';
import { AUTH_API_CONFIG } from '../api/config';

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth: boolean;
  redirectTo?: string;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requireAuth,
  redirectTo = AUTH_API_CONFIG.endpoints.LOGIN
}) => {
  const location = useLocation();
  const { isAuthenticated, isInitialized } = useAuthStatus();

  if (!isInitialized) {
    return <div>Loading...</div>; // Or your loading component
  }

  if (requireAuth && !isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  if (!requireAuth && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};