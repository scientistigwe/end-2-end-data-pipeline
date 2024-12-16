// src/auth/components/ProtectedRoute.tsx
import React, { useEffect } from "react";
import { useLocation, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { Permission } from "../types/permissions";
import { PermissionGuard } from "./PermissionGuard";

interface ProtectedRouteProps {
  permissions?: Permission[];
  requireAll?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  permissions = [],
  requireAll = true,
}) => {
  const { isAuthenticated, isLoggingIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isLoggingIn && !isAuthenticated) {
      navigate("/login", {
        replace: true,
        state: { from: location.pathname },
      });
    }
  }, [isAuthenticated, isLoggingIn, navigate, location.pathname]);

  if (isLoggingIn || !isAuthenticated) {
    return null;
  }

  if (permissions.length > 0) {
    return (
      <PermissionGuard
        permissions={permissions}
        requireAll={requireAll}
        fallback={null}
      >
        <Outlet />
      </PermissionGuard>
    );
  }

  return <Outlet />;
};
