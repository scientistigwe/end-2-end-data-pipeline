// src/store/types.ts
import type { AuthState } from '@/auth/store/authSlice';
import type { AnalysisState } from '@/analysis/store/analysisSlice';
import type { DataSourceState } from '@/dataSource/store/dataSourceSlice';
import type { PipelineState } from '@/pipeline/store/pipelineSlice';
import type { MonitoringState } from '@/monitoring/store/monitoringSlice';
import type { RecommendationsState } from '@/recommendations/store/recommendationsSlice';
import type { ReportState } from '@/reports/store/reportSlice';
import type { UIState } from '@/common/store/ui/uiSlice';

export interface RootState {
  auth: AuthState;
  analysis: AnalysisState;
  dataSources: DataSourceState;
  pipelines: PipelineState;
  monitoring: MonitoringState;
  recommendations: RecommendationsState;
  reports: ReportState;
  ui: UIState;
}

