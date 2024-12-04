// src/routes/index.tsx
import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useSelector } from "react-redux";
import { MainLayout } from "../components/layout/MainLayout";
import { AuthLayout } from "../components/auth/AuthLayout";
import { ProtectedRoute } from "../routes/ProtectedRoute";
import { selectIsAuthenticated } from "../store/slices/authSlice";

// Auth Pages
import { LoginForm } from "../components/auth/LoginForm";
import { RegisterForm } from "../components/auth/RegisterForm";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";

// Main Pages
import { DashboardPage } from "../pages/DashboardPage";
import { DataSourcesPage } from "../pages/DataSourcesPage";
import { PipelinesPage } from "../pages/PipelinesPage";
import { AnalysisPage } from "../pages/AnalysisPage";
import { MonitoringPage } from "../pages/MonitoringPage";
import { ReportsPage } from "../pages/ReportsPage";
import { SettingsPage } from "../pages/SettingsPage";

// Error Pages
import { NotFound } from "./../components/errors/NotFound";
import { ServerError } from "./../components/errors/ServerError";

export const AppRoutes: React.FC = () => {
  const location = useLocation();
  const isAuthenticated = useSelector(selectIsAuthenticated);

  // Auth routes - using a layout specifically for auth pages
  if (!isAuthenticated && !location.pathname.startsWith("/auth")) {
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
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/sources/*"
          element={
            <ProtectedRoute>
              <DataSourcesPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/pipelines/*"
          element={
            <ProtectedRoute>
              <PipelinesPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/analysis/*"
          element={
            <ProtectedRoute>
              <AnalysisPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/monitoring/*"
          element={
            <ProtectedRoute>
              <MonitoringPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/reports/*"
          element={
            <ProtectedRoute>
              <ReportsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/settings/*"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />

        {/* Error Routes */}
        <Route path="/500" element={<ServerError />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </MainLayout>
  );
};
