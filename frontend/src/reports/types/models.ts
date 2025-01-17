// src/report/types/types.ts
import type { ReportConfig } from './config';
import type { ReportStatus, MetricStatus } from './base';

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