// src/dataSource/types/s3Source.ts
import type { BaseMetadata, BaseDataSourceConfig, DataSourceType } from './base';

export interface S3SourceConfig extends BaseDataSourceConfig {
  type: DataSourceType.S3;
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

export interface S3Metadata extends BaseMetadata {
  type: DataSourceType.S3;
  stats?: {
    totalSize: number;
    objectCount: number;
    lastSync: string;
  };
}

export interface S3SourceCardProps {
  id: string;
  metadata: S3Metadata;
  config: S3SourceConfig;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}