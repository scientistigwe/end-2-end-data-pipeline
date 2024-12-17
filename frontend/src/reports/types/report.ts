// src/report/types/report.ts
export type ReportType = 'quality' | 'insight' | 'performance' | 'summary';
export type ReportFormat = 'pdf' | 'csv' | 'json';
export type ReportScheduleFrequency = 'daily' | 'weekly' | 'monthly';
export type MetricStatus = 'healthy' | 'warning' | 'critical';

// Event Constants
export const REPORT_EVENTS = {
  GENERATION_COMPLETE: 'report:generationComplete',
  EXPORT_READY: 'report:exportReady',
  STATUS_CHANGE: 'report:statusChange',
  ERROR: 'report:error'
} as const;

// Error Type
export interface ReportError extends Error {
  name: 'ReportError';
  code?: string;
  timestamp: string;
  component: 'report';
  details: {
    reportId?: string;
    [key: string]: unknown;
  };
}

// Event Detail Types
export interface ReportGenerationCompleteDetail {
  reportId: string;
  status: string;
  metadata: ReportMetadata;
}

export interface ReportExportReadyDetail {
  exports: Array<{
    id: string;
    downloadUrl: string;
  }>;
}

export interface ReportStatusChangeDetail {
  reportId: string;
  status: string;
  previousStatus?: string;
  progress?: number;
}

export interface ReportErrorDetail {
  error: string;
  code?: string;
  reportId?: string;
}

// Event Map Type
export type ReportEventMap = {
  'report:generationComplete': CustomEvent<ReportGenerationCompleteDetail>;
  'report:exportReady': CustomEvent<ReportExportReadyDetail>;
  'report:statusChange': CustomEvent<ReportStatusChangeDetail>;
  'report:error': CustomEvent<ReportErrorDetail>;
};

export type ReportEventName = keyof ReportEventMap;

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

