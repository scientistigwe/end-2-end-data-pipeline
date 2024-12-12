// src/routes/index.tsx
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../auth/components/ProtectedRoute';

// Auth Pages
import { LoginPage, RegisterPage, ForgotPasswordPage, ProfilePage } from '../auth/pages';

// Analysis Pages
import { DashboardPage as AnalysisDashboardPage } from '@/analysis/pages/DashboardPage';
import { AnalysisPage } from '@/analysis/pages/AnalysisPage';
// DataSource Pages
import { DataSourcesPage } from '../dataSource/pages';

// Decisions Pages
import { DecisionsPage, DashboardPage as DecisionDashboardPage } from '../decisions/pages';

// Monitoring Pages
import MonitoringPage from '@/monitoring/pages/MonitoringPage';

// Pipeline Pages
import { DashboardPage as PipelineDashboardPage 
} from '../pipeline/pages/DashboardPage';
import { PipelineDetailsPage
} from '../pipeline/pages/PipelineDetailsPage';
import { PipelinesPage } from '../pipeline/pages/PipelinesPage';

// Reports Pages
import { 
  ReportsPage, 
  ReportDetailsPage, 
  ReportGenerationPage, 
  ScheduledReportsPage 
} from '../reports/pages';

// Recommendations Pages
import { RecommendationsPage } from '../recommendations/pages';

// Settings Pages
import { SettingsPage } from '../settings/pages/SettingsPage';

export const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      
      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        {/* Dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<AnalysisDashboardPage />} />

        {/* Profile & Settings */}
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Analysis */}
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/analysis/dashboard" element={<AnalysisDashboardPage />} />

        {/* Data Sources */}
        <Route path="/data-sources" element={<DataSourcesPage />} />

        {/* Decisions */}
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/decisions/dashboard" element={<DecisionDashboardPage />} />

        {/* Monitoring */}
        <Route path="/monitoring" element={<MonitoringPage />} />

        {/* Pipeline */}
        <Route path="/pipelines">
          <Route index element={<PipelinesPage />} />
          <Route path=":id" element={<PipelineDetailsPage />} />
          <Route path="dashboard" element={<PipelineDashboardPage />} />
        </Route>

        {/* Reports */}
        <Route path="/reports">
          <Route index element={<ReportsPage />} />
          <Route path=":id" element={<ReportDetailsPage />} />
          <Route path="generate" element={<ReportGenerationPage />} />
          <Route path="scheduled" element={<ScheduledReportsPage />} />
        </Route>

        {/* Recommendations */}
        <Route path="/recommendations" element={<RecommendationsPage />} />
      </Route>

      {/* Catch all - 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};