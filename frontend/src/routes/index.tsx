// src/routes/index.tsx
import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { MainLayout } from "../components/layout/MainLayout";
import { AuthLayout } from "../auth/components/AuthLayout";
import {
  RequireAuth,
  RequirePermission,
  RequireRole,
} from "../auth/components/middleware/AuthMiddleware";

// Auth Pages
import { LoginForm } from "../auth/components/LoginForm";
import { RegisterForm } from "../auth/components/RegisterForm";
import { ForgotPasswordPage } from "../auth/pages/ForgotPasswordPage";

// Main Pages
import { DashboardPage } from "../analysis/pages/DashboardPage";
import { DataSourcesPage } from "../dataSource/pages/DataSourcesPage";
import { PipelinesPage } from "../pipeline/PipelinesPage";
import { AnalysisPage } from "../analysis/pages/AnalysisPage";
import { MonitoringPage } from "../monitoring/pages/MonitoringPage";
import { ReportsPage } from "../reports/pages/ReportsPage";
import { SettingsPage } from "../settings/pages/SettingsPage";

// Error Pages
import { NotFound } from "../common/components/errors/NotFound";
import { ServerError } from "../common/components/errors/ServerError";

export const AppRoutes: React.FC = () => {
  const location = useLocation();

  // Auth routes - using a layout specifically for auth pages
  if (location.pathname.startsWith("/auth")) {
    return (
      <AuthLayout>
        <Routes>
          <Route path="/auth/login" element={<LoginForm />} />
          <Route path="/auth/register" element={<RegisterForm />} />
          <Route
            path="/auth/forgot-password"
            element={<ForgotPasswordPage />}
          />
          <Route path="*" element={<Navigate to="/auth/login" replace />} />
        </Routes>
      </AuthLayout>
    );
  }

  // Protected routes - all wrapped in MainLayout
  return (
    <MainLayout>
      <Routes>
        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/auth/*" element={<Navigate to="/dashboard" replace />} />

        {/* Main Routes */}
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />

        <Route
          path="/sources/*"
          element={
            <RequireAuth>
              <DataSourcesPage />
            </RequireAuth>
          }
        />

        <Route
          path="/pipelines/*"
          element={
            <RequireAuth>
              <PipelinesPage />
            </RequireAuth>
          }
        />

        <Route
          path="/analysis/*"
          element={
            <RequirePermission permission="view_analytics">
              <AnalysisPage />
            </RequirePermission>
          }
        />

        <Route
          path="/monitoring/*"
          element={
            <RequireAuth>
              <MonitoringPage />
            </RequireAuth>
          }
        />

        <Route
          path="/reports/*"
          element={
            <RequireAuth>
              <ReportsPage />
            </RequireAuth>
          }
        />

        <Route
          path="/settings/*"
          element={
            <RequireRole role="admin">
              <SettingsPage />
            </RequireRole>
          }
        />

        {/* Error Routes */}
        <Route path="/500" element={<ServerError />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </MainLayout>
  );
};
