// src/types/dataSources.ts
export type SourceType = 'file' | 'api' | 'database' | 's3' | 'stream';
export type SourceConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error' | 'validating';
export type ValidationSeverity = 'error' | 'warning' | 'info';

export interface SourceTypeConfig {
  id: SourceType;
  label: string;
}

export interface BaseSourceConfig {
  id: string;
  type: SourceType;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  status: 'active' | 'inactive' | 'error';
}

export interface FileSourceConfig extends BaseSourceConfig {
  type: 'file';
  metadata: {
    fileName: string;
    fileSize: number;
    fileType: string;
    uploadedAt: string;
  };
}

export interface ApiSourceConfig extends BaseSourceConfig {
  type: 'api';
  config: {
    url: string;
    method: string;
    headers: Record<string, string>;
    authentication?: {
      type: string;
      credentials: Record<string, string>;
    };
  };
}

export interface DBSourceConfig extends BaseSourceConfig {
  type: 'database';
  config: {
    type: string;
    host: string;
    port: number;
    database: string;
    username: string;
    ssl?: boolean;
  };
}

export interface S3SourceConfig extends BaseSourceConfig {
  type: 's3';
  config: {
    bucket: string;
    region: string;
    path: string;
    credentials: {
      accessKeyId: string;
      secretAccessKey: string;
    };
  };
}

export interface StreamSourceConfig extends BaseSourceConfig {
  type: 'stream';
  config: {
    type: string;
    topic: string;
    broker: string;
    options: Record<string, unknown>;
  };
}

export type DataSourceConfig = 
  | FileSourceConfig 
  | ApiSourceConfig 
  | DBSourceConfig 
  | S3SourceConfig 
  | StreamSourceConfig



export interface SourceMetadata {
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadedAt: string;
  metadata: Record<string, unknown>;
}

export interface ConnectionResponse {
  connectionId: string;
  status: SourceConnectionStatus;
}

export interface ValidationIssue {
  type: string;
  message: string;
  severity: ValidationSeverity;
}

export interface StreamMetrics {
  messagesPerSecond: number;
  bytesPerSecond: number;
  lastMessage: string;
}

export interface S3Object {
  key: string;
  size: number;
  lastModified: string;
  isDirectory: boolean;
}

