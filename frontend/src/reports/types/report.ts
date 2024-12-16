// src/report/types/report.ts
export type ReportType = 'quality' | 'insight' | 'performance' | 'summary';
export type ReportFormat = 'pdf' | 'csv' | 'json';
export type ReportScheduleFrequency = 'daily' | 'weekly' | 'monthly';
export type MetricStatus = 'healthy' | 'warning' | 'critical';

export interface ReportConfig {
  name: string;
  type: ReportType;
  pipelineId: string;
  description?: string;
  timeRange?: {
    start: string;
    end: string;
  };
  filters?: Record<string, unknown>;
  format: ReportFormat;
}

export interface Report {
  id: string;
  config: ReportConfig;
  status: ReportStatus;
  createdAt: string;
  completedAt?: string;
  downloadUrl?: string;
  error?: string;
  metadata?: ReportMetadata;
}

export interface ReportMetadata {
  totalCount: number;
  metrics: ReportMetric[];
  summary: string;
}

export interface ReportMetric {
  name: string;
  value: number;
  status: MetricStatus;
}

export interface ScheduleConfig extends ReportConfig {
  frequency: ReportScheduleFrequency;
  recipients: string[];
  nextRunAt?: string;
  lastRunAt?: string;
}

export interface ExportOptions {
  format: ReportFormat;
  sections?: string[];
  includeMetadata?: boolean;
}

export interface ReportGenerationOptions {
  priority?: 'high' | 'normal' | 'low';
  notify?: boolean;
  dryRun?: boolean;
}

export interface ReportState {
  reports: Record<string, {
    id: string;
    name: string;
    type: string;
    schedule?: {
      enabled: boolean;
      frequency: 'daily' | 'weekly' | 'monthly';
      lastGenerated?: string;
      nextGeneration?: string;
    };
    parameters: Record<string, unknown>;
    data: Record<string, unknown>;
    metadata: {
      createdAt: string;
      updatedAt: string;
      generatedAt: string;
    };
  }>;
  activeReportId: string | null;
  isLoading: boolean;
  error: string | null;
}

export const ReportStatus = {
  PENDING: 'pending',
  GENERATING: 'generating',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
} as const;

export type ReportStatus = typeof ReportStatus[keyof typeof ReportStatus];

