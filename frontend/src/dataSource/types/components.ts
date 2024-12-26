// src/dataSource/types/components.ts
import { DataSourceType } from './base';  // Remove the 'type' keyword

export interface DataSourceOption {
  value: DataSourceType;
  label: string;
}

export interface DataSourceTypeSelectProps {
  value: DataSourceType | '';
  onChange: (value: DataSourceType) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

export const DATA_SOURCE_OPTIONS: readonly DataSourceOption[] = [
  { value: DataSourceType.FILE, label: 'File Upload' },
  { value: DataSourceType.API, label: 'API' },
  { value: DataSourceType.DATABASE, label: 'Database' },
  { value: DataSourceType.S3, label: 'S3 Storage' },
  { value: DataSourceType.STREAM, label: 'Data Stream' },
] as const;