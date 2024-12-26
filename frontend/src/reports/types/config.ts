// src/report/types/config.ts
import type { ReportType, ReportFormat, ReportScheduleFrequency } from './base';

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