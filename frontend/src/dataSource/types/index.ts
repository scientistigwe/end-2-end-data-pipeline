// src/dataSource/types/index.ts
// Export everything from base types
export * from './base';

// Export from each source type file
export * from './fileSource';
export * from './apiSource';
export * from './dbSource';
export * from './s3Source';
export * from './streamSource';
export * from './dataSourceFilters';

// Export from other type files
export * from './responses';
export * from './components';

// Define the union types
import type { FileSourceConfig } from './fileSource';
import type { ApiSourceConfig } from './apiSource';
import type { DBSourceConfig } from './dbSource';
import type { S3SourceConfig } from './s3Source';
import type { StreamSourceConfig } from './streamSource';

import type { FileMetadata } from './fileSource';
import type { ApiMetadata } from './apiSource';
import type { DBMetadata } from './dbSource';
import type { S3Metadata } from './s3Source';
import type { StreamMetadata } from './streamSource';

export type DataSourceConfig =
  | FileSourceConfig
  | ApiSourceConfig
  | DBSourceConfig
  | S3SourceConfig
  | StreamSourceConfig;

export type DataSourceMetadata =
  | FileMetadata
  | ApiMetadata
  | DBMetadata
  | S3Metadata
  | StreamMetadata;