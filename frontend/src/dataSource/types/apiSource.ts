// src/dataSource/types/apiSource.ts
import type { BaseMetadata, BaseDataSourceConfig, DataSourceType } from './base';

export interface ApiSourceConfig extends BaseDataSourceConfig {
  type: DataSourceType.API;
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

export interface ApiMetadata extends BaseMetadata {
  type: DataSourceType.API;
  stats?: {
    lastResponse?: {
      status: number;
      timestamp: string;
    };
    averageResponseTime?: number;
    successRate?: number;
  };
}

export interface ApiSourceCardProps {
  id: string;
  metadata: ApiMetadata;
  config: ApiSourceConfig;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}