import { dateUtils, formatBytes } from '@/common';
import type { 
  DataSourceMetadata, 
  DataSourceType,
  DataSourceStatus 
} from '../types/base';

export const formatSourceType = (type: DataSourceType): string => {
  const typeMap: Record<DataSourceType, string> = {
    file: 'File',
    api: 'API',
    database: 'Database',
    s3: 'S3',
    stream: 'Stream'
  };
  return typeMap[type] || type;
};

export const formatSourceStatus = (status: DataSourceStatus): string => {
  const statusMap: Record<DataSourceStatus, string> = {
    connected: 'Connected',
    disconnected: 'Disconnected',
    error: 'Error',
    connecting: 'Connecting',
    validating: 'Validating'
  };
  return statusMap[status] || status;
};

interface FormattedMetadata extends Omit<DataSourceMetadata, 'stats'> {
  formattedStats?: {
    rowCount?: number;
    formattedSize?: string;
    lastUpdated?: string;
  };
  stats?: DataSourceMetadata['stats'];
}

export const formatSourceMetadata = (metadata: DataSourceMetadata): FormattedMetadata => {
  const formattedMetadata: FormattedMetadata = {
    ...metadata,
    createdAt: dateUtils.formatDate(metadata.createdAt),
    updatedAt: dateUtils.formatDate(metadata.updatedAt),
    lastSync: metadata.lastSync ? dateUtils.formatDate(metadata.lastSync) : undefined,
    nextSync: metadata.nextSync ? dateUtils.formatDate(metadata.nextSync) : undefined,
  };

  if (metadata.stats) {
    formattedMetadata.stats = metadata.stats; // Preserve original stats
    formattedMetadata.formattedStats = {
      rowCount: metadata.stats.rowCount,
      formattedSize: metadata.stats.size ? formatBytes(metadata.stats.size) : undefined,
      lastUpdated: metadata.stats.lastUpdated ? dateUtils.formatDate(metadata.stats.lastUpdated) : undefined
    };
  }

  return formattedMetadata;
};