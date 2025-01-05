// src/dataSource/types/base.ts

export enum DataSourceType {
  FILE = 'file',
  API = 'api',
  DATABASE = 'database',
  S3 = 's3',
  STREAM = 'stream'
}

export type DataSourceStatus = 
  | 'active'
  | 'inactive'
  | 'error'
  | 'connecting'
  | 'processing'
  | 'validating';

export type DataSourceValidationSeverity = 'error' | 'warning' | 'info';

export interface ValidationRule {
  field: string;
  type: string;
  params?: Record<string, unknown>;
  severity: DataSourceValidationSeverity;
  message: string;
}

export interface DataSourceError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

export interface BaseDataSourceConfig {
  id: string;
  type: DataSourceType;
  name: string;
  description?: string;
  tags?: string[];
  status: DataSourceStatus;
  validationRules?: ValidationRule[];
  refreshInterval?: number;
  config: Record<string, unknown>;  // Source-specific configuration
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  lastSync?: string;
  error?: DataSourceError;
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
  error?: DataSourceError;
  config?: Record<string, unknown>;  // Basic configuration for display
}

export interface PreviewData {
  columns: Array<{
      name: string;
      type: string;
      nullable?: boolean;
  }>;
  data: unknown[][];
  total: number;
  hasMore?: boolean;
}

export interface ValidationResult {
  isValid: boolean;
  errors: Array<{
      field?: string;
      message: string;
      severity: DataSourceValidationSeverity;
      code?: string;
      details?: unknown;
  }>;
  warnings: Array<{
      field?: string;
      message: string;
      details?: unknown;
  }>;
}

export interface SourceConnectionResponse {
  connectionId: string;
  status: DataSourceStatus;
  details?: Record<string, unknown>;
}

export interface SourceConnectionConfig {
  type: DataSourceType;
  config: Record<string, unknown>;  // Source-specific connection parameters
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

// Request/Response Types
export interface FileUploadMetadata {
  name?: string;
  description?: string;
  tags?: string[];
  encoding?: string;
  delimiter?: string;
  hasHeader?: boolean;
  sheet?: string;  // For Excel files
  skipRows?: number;
  parseOptions?: {
      dateFormat?: string;
      nullValues?: string[];
      [key: string]: unknown;
  };
}

export interface DataSourceListResponse {
  sources: {
      api: BaseMetadata[];
      databases: BaseMetadata[];
      files: BaseMetadata[];
      s3: BaseMetadata[];
      stream: BaseMetadata[];
  };
  total: number;
  page?: number;
  pageSize?: number;
}

export interface SourceStatusResponse {
  status: DataSourceStatus;
  lastChecked: string;
  responseTime?: number;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface DataSourceFilters {
  types?: DataSourceType[];
  status?: DataSourceStatus[];
  tags?: string[];
  search?: string;
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}