// src/types/source.ts
export type SourceConnectionStatus = 
  | 'connected' 
  | 'connecting' 
  | 'disconnected' 
  | 'error' 
  | 'validating';

export interface SourceConnectionResponse {
  connectionId: string;
  status: SourceConnectionStatus;
  metadata?: Record<string, unknown>;
}

export interface ConnectionTestResponse {
  success: boolean;
  error?: string;
}

export interface SourceValidationIssue {
  type: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface SourceValidationResponse {
  isValid: boolean;
  issues?: SourceValidationIssue[];
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

// Export source configuration types
export interface FileSourceConfig {
  type: 'file';
  config: {
    filename: string;
    size: number;
    mimeType: string;
  };
}

export interface ApiSourceConfig {
  type: 'api';
  config: {
    url: string;
    method: string;
    headers?: Record<string, string>;
    body?: unknown;
  };
}

export interface DBSourceConfig {
  type: 'database';
  config: {
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    ssl?: boolean;
  };
}

export interface S3SourceConfig {
  type: 's3';
  config: {
    bucket: string;
    region: string;
    accessKey: string;
    secretKey: string;
    prefix?: string;
  };
}

export interface StreamSourceConfig {
  type: 'stream';
  config: {
    url: string;
    protocol: 'ws' | 'mqtt' | 'kafka';
    options?: Record<string, unknown>;
  };
}

export interface SourceMetadata {
  id: string;
  name: string;
  type: string;
  createdAt: string;
  updatedAt: string;
  properties: Record<string, unknown>;
}