// src/types/reports.ts
import { MetricStatus } from './monitoring';

export type ReportType = 'quality' | 'insight' | 'performance' | 'summary';
export type ReportFormat = 'pdf' | 'csv' | 'json';
export type ReportStatus = 'pending' | 'generating' | 'completed' | 'failed';
export type ReportScheduleFrequency = 'daily' | 'weekly' | 'monthly';

export interface ReportConfig {
  type: ReportType;
  pipelineId: string;
  name: string;
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
}

export interface ScheduleConfig extends ReportConfig {
  frequency: ReportScheduleFrequency;
  recipients: string[];
  nextRunAt?: string;
  lastRunAt?: string;
}

export interface ReportMetadata {
  totalCount: number;
  metrics: {
    name: string;
    value: number;
    status: MetricStatus;
  }[];
  summary: string;
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