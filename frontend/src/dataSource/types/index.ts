// src/dataSource/types/index.ts

// First import all necessary types
import type {
  BaseDataSourceConfig,
  BaseMetadata,
  DataSourceStatus,
  ValidationResult,
  PreviewData
} from './base';

import { DataSourceType } from './base';

import type {
  FileSourceConfig,
  FileMetadata
} from './fileSource';

import type {
  DBSourceConfig,
  DBMetadata
} from './dbSource';

import type {
  ApiSourceConfig,
  ApiMetadata
} from './apiSource';

import type {
  S3SourceConfig,
  S3Metadata
} from './s3Source';

import type {
  StreamSourceConfig,
  StreamMetadata
} from './streamSource';

// Re-export everything from base and specific types
export * from './base';
export * from './fileSource';
export * from './dbSource';
export * from './apiSource';
export * from './s3Source';
export * from './streamSource';

// Type guards for discriminating unions
export const isFileSource = (
  config: DataSourceConfig
): config is FileSourceConfig => config.type === DataSourceType.FILE;

export const isDBSource = (
  config: DataSourceConfig
): config is DBSourceConfig => config.type === DataSourceType.DATABASE;

export const isApiSource = (
  config: DataSourceConfig
): config is ApiSourceConfig => config.type === DataSourceType.API;

export const isS3Source = (
  config: DataSourceConfig
): config is S3SourceConfig => config.type === DataSourceType.S3;

export const isStreamSource = (
  config: DataSourceConfig
): config is StreamSourceConfig => config.type === DataSourceType.STREAM;

// Union types for component props
export type DataSourceConfig =
  | FileSourceConfig
  | DBSourceConfig
  | ApiSourceConfig
  | S3SourceConfig
  | StreamSourceConfig;

export type DataSourceMetadata =
  | FileMetadata
  | DBMetadata
  | ApiMetadata
  | S3Metadata
  | StreamMetadata;

// Export everything we imported
export type {
  BaseDataSourceConfig,
  BaseMetadata,
  DataSourceType,
  DataSourceStatus,
  ValidationResult,
  PreviewData,
  FileSourceConfig,
  FileMetadata,
  DBSourceConfig,
  DBMetadata,
  ApiSourceConfig,
  ApiMetadata,
  S3SourceConfig,
  S3Metadata,
  StreamSourceConfig,
  StreamMetadata
};