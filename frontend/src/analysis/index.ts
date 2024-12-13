// src/analysis/index.ts

// Components
export { AnalysisForm } from './components/forms/AnalysisForm';
export * from './components/reports/QualityReport';
export * from './components/reports/InsightReport';
export { AnalysisStatus } from './components/status/AnalysisStatus';

// Pages
export * from './pages/AnalysisPage';
export * from './pages/DashboardPage';

// Hooks
export { useAnalysis } from './hooks/useAnalysis';
export { useAnalysisDetails } from './hooks/useAnalysisDetails';

// Types
export type {
  AnalysisConfig,
  AnalysisResult,
  AnalysisState,
  AnalysisError,
  QualityConfig,
  QualityReport,
  QualityIssue,
  InsightConfig,
  InsightReport,
  Pattern,
  Anomaly,
  Correlation,
  Trend,
  ExportOptions,
  BaseAnalysisOptions,
  CustomRule
} from './types/analysis';

export {
  AnalysisStatus as AnalysisStatusType,
  AnalysisType,
  analysisConfigSchema,
  qualityConfigSchema,
  insightConfigSchema
} from './types/analysis';

export type {
  TimeSeriesDataPoint,
  TimeSeriesData,
  AggregatedMetric,
  ChartData,
  HeatmapData
} from './types/visualization';

// Context & Provider
export { AnalysisContext, useAnalysisContext } from './context/AnalysisContext';
export { AnalysisProvider } from './providers/AnalysisProvider';

// Store
export {
  setAnalysis,
  removeAnalysis,
  setQualityReport,
  setInsightReport,
  setSelectedAnalysis,
  setLoading,
  setError,
  updateAnalysisProgress
} from './store/analysisSlice';

export {
  selectActiveAnalyses,
  selectQualityReports,
  selectInsightReports,
  selectSelectedAnalysisId,
  selectSelectedAnalysis,
  selectSelectedQualityReport,
  selectSelectedInsightReport
} from './store/selectors';

// Utils
export {
  formatAnalysisConfig,
  getStatusColor,
  getStatusBadgeClass,
  formatMetricValue,
  getConfidenceLevelColor,
  formatAnalysisDuration
} from './utils/formatters';

export {
  validateAnalysisConfig,
  calculateProgress,
  shouldRetryAnalysis,
  calculateCorrelationStrength,
  groupAnomaliesBySeverity,
  calculateAnalysisMetrics,
  downloadAnalysisReport
} from './utils/analysisUtils';