// src/dataSource/types/fileSource.ts
import type { BaseMetadata, BaseDataSourceConfig, DataSourceType } from './base';

export interface FileSourceConfig extends BaseDataSourceConfig {
  type: DataSourceType.FILE;
  config: {
    type: 'csv' | 'json' | 'parquet' | 'excel';
    delimiter?: string;
    encoding?: string;
    hasHeader?: boolean;
    sheet?: string;
    skipRows?: number;
    parseOptions?: {
      dateFormat?: string;
      nullValues?: string[];
    };
  };
}

export interface FileMetadata extends BaseMetadata {
  type: DataSourceType.FILE;
  stats: {
    filename: string;
    size: number;
    rowCount?: number;
    lastModified: string;
    mimeType?: string;
  };
}

// Component Props
export interface FileSourceCardProps {
  id: string;
  metadata: FileMetadata;
  config: FileSourceConfig;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}