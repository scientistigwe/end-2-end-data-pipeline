// src/types/dataSource.ts

// Basic Types & Enums
export type DataSourceType = 'file' | 'api' | 'database' | 's3' | 'stream';
export type DataSourceStatus = 'connected' | 'disconnected' | 'error' | 'connecting' | 'validating';
export type DataSourceValidationSeverity = 'error' | 'warning' | 'info';


// Base Interfaces
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

export interface SourceConnectionResponse {
  connectionId: string;
  status: string;
  details?: Record<string, unknown>;
}

export interface ValidationRule {
  field: string;
  type: string;
  params?: Record<string, unknown>;
  severity: DataSourceValidationSeverity;
  message: string;
}

export interface BaseMetadata {
  id: string;
  name: string;
  type: DataSourceType;
  status: DataSourceStatus;
  description?: string;
  tags?: string[];
}

// Source-Specific Configurations
export interface FileSourceConfig extends BaseDataSourceConfig {
  type: 'file';
  config: {
    type: 'csv' | 'json' | 'parquet' | 'excel';
    delimiter?: string;
    encoding?: string;
    hasHeader?: boolean;
    sheet?: string;
    skipRows?: number;
  };
}

export interface ApiSourceConfig extends BaseDataSourceConfig {
  type: 'api';
  config: {
    url: string;
    method: 'GET' | 'POST' | 'PUT' | 'DELETE';
    headers?: Record<string, string>;
    params?: Record<string, string>;
    body?: unknown;
    auth?: {
      type: 'basic' | 'bearer' | 'oauth2';
      credentials: Record<string, string>;
    };
    rateLimit?: {
      requests: number;
      period: number;
    };
  };
}


export interface DBSourceConfig extends BaseDataSourceConfig {
  type: 'database';
  config: {
    type: 'postgresql' | 'mysql' | 'mongodb' | 'oracle';
    protocol: 'kafka' | 'rabbitmq' | 'mqtt' | 'redis';
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    ssl?: boolean;
    schema?: string;
    options?: Record<string, unknown>;
    pool?: {
      min: number;
      max: number;
      idleTimeout: number;
    };
  };
}

export interface S3SourceConfig extends BaseDataSourceConfig {
  type: 's3';
  config: {
    bucket: string;
    region: string;
    accessKeyId: string;
    secretAccessKey: string;
    prefix?: string;
    endpoint?: string;
    sslEnabled?: boolean;
    forcePathStyle?: boolean;
  };
}

export interface StreamSourceConfig extends BaseDataSourceConfig {
  type: 'stream';
  config: {
    protocol: 'kafka' | 'rabbitmq' | 'mqtt' | 'redis';
    connection: {
      hosts: string[];
      options?: Record<string, unknown>;
    };
    auth?: {
      username?: string;
      password?: string;
      ssl?: boolean;
    };
    topics?: string[];
    consumer?: {
      groupId?: string;
      autoCommit?: boolean;
      maxBatchSize?: number;
      maxWaitTime?: number;
    };
  };
}

// Metadata Interfaces
export interface DataSourceMetadata extends BaseMetadata {
  createdAt: string;
  updatedAt: string;
  lastSync?: string;
  nextSync?: string;
  fields?: Array<{
    name: string;
    type: string;
    nullable: boolean;
    description?: string;
  }>;
  stats?: {
    rowCount?: number;
    size?: number;
    lastUpdated?: string;
  };
  error?: {
    message: string;
    code?: string;
    details?: unknown;
  };
}

export interface DataSourceFilters {
  types?: DataSourceType[];
  status?: DataSourceStatus[];
  tags?: string[];
  search?: string;
}

// Response & Result Interfaces
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

// Utility & Feature-Specific Interfaces
export interface StreamMetrics {
  messagesPerSecond: number;
  bytesPerSecond: number;
  totalMessages: number;
  lastMessage?: string;
  errors?: {
    count: number;
    lastError?: string;
  };
}

export interface S3BucketInfo {
  name: string;
  region: string;
  createdAt: string;
  objects: number;
  totalSize: number;
  lastModified: string;
  versioning?: boolean;
  encryption?: {
    enabled: boolean;
    type: string;
  };
}

export interface S3Object {
  key: string;
  size: number;
  lastModified: string;
  etag?: string;
  isDirectory: boolean;
  contentType?: string;
  metadata?: Record<string, unknown>;
}

export interface SchemaInfo {
  tables: Array<{
    name: string;
    schema?: string;
    columns: Array<{
      name: string;
      type: string;
      nullable: boolean;
      isPrimary?: boolean;
      isForeign?: boolean;
      references?: {
        table: string;
        column: string;
      };
    }>;
    indexes?: Array<{
      name: string;
      columns: string[];
      isUnique: boolean;
    }>;
    constraints?: Array<{
      name: string;
      type: string;
      definition?: string;
    }>;
  }>;
}

// State & Filter Interfaces
export interface DataSourceState {
  sources: Record<string, DataSourceMetadata>;
  configs: Record<string, DataSourceConfig>;
  selectedSourceId: string | null;
  validation: Record<string, ValidationResult>;
  preview: Record<string, PreviewData>;
  filters: DataSourceFilters;
  isLoading: boolean;
  error: string | null;
}

export interface DataSourceFilters {
  types?: DataSourceType[];
  status?: DataSourceStatus[];
  tags?: string[];
  search?: string;
}

// Response Types
export interface SourceStatusResponse {
  status: DataSourceStatus;
  lastChecked: string;
  responseTime?: number;
  error?: string;
  metadata?: Record<string, unknown>;
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

// Union Types
export type DataSourceConfig =
  | FileSourceConfig
  | ApiSourceConfig
  | DBSourceConfig
  | S3SourceConfig
  | StreamSourceConfig;