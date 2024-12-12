// src/store/types.ts
import type { AuthState } from '@/auth/types/auth';
import type { AnalysisState } from '@/analysis/types/analysis';
import type { DataSourceState } from '@/dataSource/types/dataSources';
import type { PipelineState } from '@/pipeline/types/pipeline';
import type { MonitoringState } from '@/monitoring/types/monitoring';
import type { RecommendationsState } from '@/recommendations/types/recommendations';
import type { ReportState } from '@/reports/types/report';
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