// src/report/types/base.ts
export type ReportType = 'quality' | 'insight' | 'performance' | 'summary';
export type ReportFormat = 'pdf' | 'csv' | 'json';
export type ReportScheduleFrequency = 'daily' | 'weekly' | 'monthly';
export type MetricStatus = 'healthy' | 'warning' | 'critical';

export const ReportStatus = {
  PENDING: 'pending',
  GENERATING: 'generating',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
} as const;

export type ReportStatus = typeof ReportStatus[keyof typeof ReportStatus];

export const REPORT_EVENTS = {
  GENERATION_COMPLETE: 'report:generationComplete',
  EXPORT_READY: 'report:exportReady',
  STATUS_CHANGE: 'report:statusChange',
  ERROR: 'report:error'
} as const;