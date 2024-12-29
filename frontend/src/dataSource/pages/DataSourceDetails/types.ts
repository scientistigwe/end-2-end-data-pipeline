// src/dataSource/pages/DataSourceDetails/types.ts
import type {
    ApiSourceConfig,
    ApiMetadata,
  } from '../../types/apiSource';
  import type {
    DBSourceConfig,
    DBMetadata,
  } from '../../types/dbSource';
  import type {
    FileSourceConfig,
    FileMetadata,
  } from '../../types/fileSource';
  import type {
    S3SourceConfig,
    S3Metadata,
  } from '../../types/s3Source';
  import type {
    StreamSourceConfig,
    StreamMetadata,
  } from '../../types/streamSource';
  
  export type SourceMetadata = 
    | ApiMetadata 
    | DBMetadata 
    | FileMetadata 
    | S3Metadata 
    | StreamMetadata;
  
  export type SourceConfig = 
    | ApiSourceConfig 
    | DBSourceConfig 
    | FileSourceConfig 
    | S3SourceConfig 
    | StreamSourceConfig;
  
  export interface DetailSectionProps {
    metadata: SourceMetadata;
    config: SourceConfig;
    onRefresh?: () => void;
  }
  
  export interface ConnectionStatusProps {
    status: string;
    lastSync?: string;
    error?: {
      message: string;
      code?: string;
      details?: unknown;
    };
    onRefresh?: () => void;
  }
  
  export interface StatsDisplayProps {
    stats: Record<string, any>;
    type: string;
  }
  
  export interface ActionButtonProps {
    onClick: () => void;
    isLoading?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
  }