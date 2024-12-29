import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { MainLayout } from "@/common/components/layout/MainLayout";
import { AuthLayout } from "@/auth/components/AuthLayout";
import { ProtectedRoute } from "@/auth/components/ProtectedRoute";
import { LoadingSpinner } from "@/common/components/navigation/LoadingSpinner";
import { useAppSelector } from "@/store/store";
import { selectIsAuthenticated } from "@/auth/store/selectors";

// Route constants
export const ROUTES = {
  HOME: "/",
  DASHBOARD: "/dashboard",
  LOGIN: "/login",
  REGISTER: "/register",
  FORGOT_PASSWORD: "/forgot-password",
  PROFILE: "/profile",
  SETTINGS: "/settings",
  ANALYSIS: "/analysis",
  DATA_SOURCES: "/data-sources",
  DECISIONS: "/decisions",
  MONITORING: "/monitoring",
  PIPELINES: "/pipelines",
  REPORTS: "/reports",
  RECOMMENDATIONS: "/recommendations",
} as const;

// Public Pages
const LandingPage = lazy(() => import("@/auth/pages/LandingPage"));
const LoginPage = lazy(() => import("@/auth/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/auth/pages/RegisterPage"));
const ForgotPasswordPage = lazy(() => import("@/auth/pages/ForgotPasswordPage"));

// Protected Pages
const ProfilePage = lazy(() => import("@/auth/pages/ProfilePage"));
const SettingsPage = lazy(() => import("@/settings/pages/SettingsPage"));

// Analysis Pages
const AnalysisDashboardPage = lazy(() => import("@/analysis/pages/AnalysisDashboardPage"));
const AnalysisPage = lazy(() => import("@/analysis/pages/AnalysisPage"));

// Pipeline Pages
const PipelinesPage = lazy(() => import("@/pipeline/pages/PipelinesPage"));
const PipelineDetailsPage = lazy(() => import("@/pipeline/pages/PipelineDetailsPage"));
const PipelineDashboardPage = lazy(() => import("@/pipeline/pages/PipelineDashboardPage"));

// Data Source Pages
const DataSourcesPage = lazy(() => import("@/dataSource/pages/DataSourcesPage"));
const DataSourceDetailsPage = lazy(() => import("@/dataSource/pages/DataSourceDetails")); // Updated import path

// Decisions Pages
const DecisionsPage = lazy(() => import("@/decisions/pages/DecisionsPage"));
const DecisionDashboardPage = lazy(() => import("@/decisions/pages/DecisionDashboardPage"));

// Monitoring Pages
const MonitoringPage = lazy(() => import("@/monitoring/pages/MonitoringPage"));

// Reports Pages
const ReportsPage = lazy(() => import("@/reports/pages/ReportsPage"));
const ReportDetailsPage = lazy(() => import("@/reports/pages/ReportDetailsPage"));
const ReportGenerationPage = lazy(() => import("@/reports/pages/ReportGenerationPage"));
const ScheduledReportsPage = lazy(() => import("@/reports/pages/ScheduledReportsPage"));

// Recommendations Pages
const RecommendationsPage = lazy(() => import("@/recommendations/pages/RecommendationsPage"));

export const AppRoutes = () => {
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        {/* Public Landing */}
        <Route path={ROUTES.HOME} element={<LandingPage />} />

        {/* Auth Routes - With AuthLayout */}
        <Route element={<AuthLayout />}>
          <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
          <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />
        </Route>

        {/* Protected Routes - With MainLayout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            {/* Dashboard */}
            <Route path={ROUTES.DASHBOARD} element={<AnalysisDashboardPage />} />

            {/* Profile & Settings */}
            <Route path={ROUTES.PROFILE} element={<ProfilePage />} />
            <Route path={ROUTES.SETTINGS} element={<SettingsPage />} />

            {/* Analysis Routes */}
            <Route path={ROUTES.ANALYSIS}>
              <Route index element={<AnalysisPage />} />
              <Route path="dashboard" element={<AnalysisDashboardPage />} />
            </Route>

            {/* Pipeline Routes */}
            <Route path={ROUTES.PIPELINES}>
              <Route index element={<PipelinesPage />} />
              <Route path=":id" element={<PipelineDetailsPage />} />
              <Route path="dashboard" element={<PipelineDashboardPage />} />
            </Route>

            {/* Data Sources Routes */}
            <Route path={ROUTES.DATA_SOURCES}>
              <Route index element={<DataSourcesPage />} />
              <Route path=":type" element={<DataSourcesPage />} />
              <Route path=":type/:id" element={<DataSourceDetailsPage />} />
            </Route>

            {/* Reports Routes */}
            <Route path={ROUTES.REPORTS}>
              <Route index element={<ReportsPage />} />
              <Route path=":id" element={<ReportDetailsPage />} />
              <Route path="generate" element={<ReportGenerationPage />} />
              <Route path="scheduled" element={<ScheduledReportsPage />} />
            </Route>

            {/* Decisions Routes */}
            <Route path={ROUTES.DECISIONS}>
              <Route index element={<DecisionsPage />} />
              <Route path="dashboard" element={<DecisionDashboardPage />} />
            </Route>

            {/* Monitoring Routes */}
            <Route path={ROUTES.MONITORING} element={<MonitoringPage />} />

            {/* Recommendations Routes */}
            <Route path={ROUTES.RECOMMENDATIONS} element={<RecommendationsPage />} />
          </Route>
        </Route>

        {/* Catch all */}
        <Route
          path="*"
          element={
            isAuthenticated ? (
              <Navigate to={ROUTES.DASHBOARD} replace />
            ) : (
              <Navigate to={ROUTES.HOME} replace />
            )
          }
        />
      </Routes>
    </Suspense>
  );
};