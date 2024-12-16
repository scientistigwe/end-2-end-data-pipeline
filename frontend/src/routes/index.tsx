import { lazy, useEffect } from "react";
import {
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { useAuth } from "../auth/hooks/useAuth";
import { ProtectedRoute } from "../auth/components/ProtectedRoute";

// Route constants for use throughout the app
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

// Lazy load all page components
const LoginPage = lazy(() => import("../auth/pages/LoginPage"));
const RegisterPage = lazy(() => import("../auth/pages/RegisterPage"));
const ForgotPasswordPage = lazy(
  () => import("../auth/pages/ForgotPasswordPage")
);
const ProfilePage = lazy(() => import("../auth/pages/ProfilePage"));
const AnalysisDashboardPage = lazy(
  () => import("@/analysis/pages/AnalysisDashboardPage")
);
const AnalysisPage = lazy(() => import("@/analysis/pages/AnalysisPage"));
const DataSourcesPage = lazy(
  () => import("../dataSource/pages/DataSourcesPage")
);
const DecisionsPage = lazy(() => import("../decisions/pages/DecisionsPage"));
const DecisionDashboardPage = lazy(
  () => import("../decisions/pages/DecisionDashboardPage")
);
const MonitoringPage = lazy(() => import("@/monitoring/pages/MonitoringPage"));
const PipelineDashboardPage = lazy(
  () => import("../pipeline/pages/PipelineDashboardPage")
);
const PipelineDetailsPage = lazy(
  () => import("../pipeline/pages/PipelineDetailsPage")
);
const PipelinesPage = lazy(() => import("../pipeline/pages/PipelinesPage"));
const ReportsPage = lazy(() => import("../reports/pages/ReportsPage"));
const ReportDetailsPage = lazy(
  () => import("../reports/pages/ReportDetailsPage")
);
const ReportGenerationPage = lazy(
  () => import("../reports/pages/ReportGenerationPage")
);
const ScheduledReportsPage = lazy(
  () => import("../reports/pages/ScheduledReportsPage")
);
const RecommendationsPage = lazy(
  () => import("../recommendations/pages/RecommendationsPage")
);
const SettingsPage = lazy(() => import("../settings/pages/SettingsPage"));

export const AppRoutes = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoggingIn } = useAuth();

  useEffect(() => {
    if (
      !isLoggingIn &&
      !isAuthenticated &&
      !location.pathname.startsWith("/auth")
    ) {
      navigate(ROUTES.LOGIN, {
        replace: true,
        state: { from: location.pathname },
      });
    } else if (isAuthenticated && location.pathname === ROUTES.HOME) {
      navigate(ROUTES.DASHBOARD, { replace: true });
    }
  }, [isAuthenticated, isLoggingIn, location.pathname, navigate]);

  if (isLoggingIn) {
    return null;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path={ROUTES.LOGIN} element={<LoginPage />} />
      <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
      <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPasswordPage />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        {/* Home/Dashboard */}
        <Route path={ROUTES.HOME} element={<AnalysisDashboardPage />} />
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

        {/* Standalone Routes */}
        <Route path={ROUTES.DATA_SOURCES} element={<DataSourcesPage />} />
        <Route path={ROUTES.MONITORING} element={<MonitoringPage />} />
        <Route
          path={ROUTES.RECOMMENDATIONS}
          element={<RecommendationsPage />}
        />
      </Route>

      {/* Catch all - 404 */}
      <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
    </Routes>
  );
};
