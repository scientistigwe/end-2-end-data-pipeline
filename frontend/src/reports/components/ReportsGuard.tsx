// src/report/components/ReportsGuard.tsx
import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '@/auth/hooks/useAuth';

export const ReportsGuard: React.FC = () => {
  const { isAuthenticated, hasPermission } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!hasPermission('reports:view')) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
};
