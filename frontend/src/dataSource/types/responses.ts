// src/dataSource/types/responses.ts
import type { DataSourceStatus, DataSourceValidationSeverity } from './base';

export interface ValidationResult {
  isValid: boolean;
  issues: Array<{
    field?: string;
    type: string;
    severity: DataSourceValidationSeverity;
    message: string;
  }>;
  warnings: Array<{
    field?: string;
    message: string;
  }>;
}

export interface PreviewData {
  fields: Array<{
    name: string;
    type: string;
  }>;
  data: Array<Record<string, unknown>>;
  totalRows: number;
}

export interface SourceConnectionResponse {
  connectionId: string;
  status: string;
  details?: Record<string, unknown>;
}

export interface ConnectionTestResponse {
  success: boolean;
  responseTime?: number;
  details?: {
    version?: string;
    features?: string[];
    [key: string]: unknown;
  };
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface SourceStatusResponse {
  status: DataSourceStatus;
  lastChecked: string;
  responseTime?: number;
  error?: string;
  metadata?: Record<string, unknown>;
}