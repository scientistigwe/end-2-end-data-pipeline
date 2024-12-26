// src/dataSource/types/base.ts
export enum DataSourceType {
  FILE = 'file',
  API = 'api',
  DATABASE = 'database',
  S3 = 's3',
  STREAM = 'stream'
}

export type DataSourceStatus = 'connected' | 'disconnected' | 'error' | 'connecting' | 'validating';
export type DataSourceValidationSeverity = 'error' | 'warning' | 'info';

export interface BaseDataSourceConfig {
  id: string;
  type: DataSourceType;
  name: string;
  description?: string;
  tags?: string[];
  validationRules?: ValidationRule[];
  refreshInterval?: number;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'inactive' | 'error';
}

export interface BaseMetadata {
  id: string;
  name: string;
  type: DataSourceType;
  status: DataSourceStatus;
  description?: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
  lastSync?: string;
  error?: {
    message: string;
    code?: string;
    details?: unknown;
  };
}

export interface ValidationRule {
  field: string;
  type: string;
  params?: Record<string, unknown>;
  severity: DataSourceValidationSeverity;
  message: string;
}