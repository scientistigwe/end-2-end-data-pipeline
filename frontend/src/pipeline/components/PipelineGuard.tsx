// Updated src/pipeline/components/PipelineGuard.tsx
import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '@/auth/hooks/useAuth';
import type { Permission } from '@/auth/types/auth';

interface PipelineGuardProps {
  requiredPermission?: Permission;
}

export const PipelineGuard: React.FC<PipelineGuardProps> = ({ 
  requiredPermission = 'pipeline:view' 
}) => {
  const { isAuthenticated, hasPermission } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!hasPermission(requiredPermission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
};