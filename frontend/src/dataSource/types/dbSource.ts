// src/dataSource/types/dbSource.ts
import type { BaseMetadata, BaseDataSourceConfig, DataSourceType } from './base';

export interface DBSourceConfig extends BaseDataSourceConfig {
  type: DataSourceType.DATABASE;
  config: {
    type: 'postgresql' | 'mysql' | 'mongodb' | 'oracle';
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

export interface DBMetadata extends BaseMetadata {
  type: DataSourceType.DATABASE;
  stats?: {
    tableCount: number;
    size: number;
    lastSync: string;
    connectionStatus: string;
  };
}

export interface DBSourceCardProps {
  id: string;
  metadata: DBMetadata;
  config: DBSourceConfig;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}