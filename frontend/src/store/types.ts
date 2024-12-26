// src/store/types.ts
import type { AuthState } from '@/auth/types/auth';
import type { AnalysisState } from '@/analysis/types/analysis';
import type { DataSourceState } from '@/dataSource/types/base';
import type { PipelineState } from '@/pipeline/types/metrics';
import type { MonitoringState } from '@/monitoring/types/metrics';
import type { RecommendationsState } from '@/recommendations/types/events';
import type { ReportState } from '@/reports/types/models';
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