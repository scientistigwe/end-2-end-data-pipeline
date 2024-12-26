// src/dataSource/types/streamSource.ts
import type { BaseMetadata, BaseDataSourceConfig, DataSourceType } from './base';

export interface StreamSourceConfig extends BaseDataSourceConfig {
  type: DataSourceType.STREAM;
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

export interface StreamMetadata extends BaseMetadata {
  type: DataSourceType.STREAM;
  stats?: {
    messagesPerSecond: number;
    bytesPerSecond: number;
    totalMessages: number;
    connectedTime: string;
  };
}

export interface StreamSourceCardProps {
  id: string;
  metadata: StreamMetadata;
  config: StreamSourceConfig;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}