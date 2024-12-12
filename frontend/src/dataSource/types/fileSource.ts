// src/dataSource/types/fileSource.ts
import type { DataSourceMetadata, DataSourceConfig } from './dataSources';

export interface FileMetadata extends DataSourceMetadata {
  stats: {
    filename: string;
    size: number;
    rowCount?: number;
    lastModified: string;
  };
}

export interface FileSourceCardProps {
  id: string;
  metadata: FileMetadata;
  config: DataSourceConfig;
}

