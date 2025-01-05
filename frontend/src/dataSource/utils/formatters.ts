// src/dataSource/utils/formatters.ts

import { dateUtils } from '@/common';
import type { 
    BaseMetadata,
    DataSourceStatus,
    DataSourceError
} from '../types';

import { DataSourceType } from '../types/base';

export const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

export const formatSourceType = (type: DataSourceType): string => {
    const typeMap: Record<DataSourceType, string> = {
        [DataSourceType.FILE]: 'File',
        [DataSourceType.API]: 'API',
        [DataSourceType.DATABASE]: 'Database',
        [DataSourceType.S3]: 'S3',
        [DataSourceType.STREAM]: 'Stream'
    };
    return typeMap[type] || type;
};

export const formatSourceStatus = (status: DataSourceStatus): string => {
    const statusMap: Record<DataSourceStatus, string> = {
        active: 'Active',
        inactive: 'Inactive',
        error: 'Error',
        connecting: 'Connecting',
        processing: 'Processing',
        validating: 'Validating'
    };
    return statusMap[status] || status;
};

export const formatError = (error: DataSourceError): string => {
    return error.code ? 
        `${error.message} (${error.code})` : 
        error.message;
};

interface FormattedMetadata extends Omit<BaseMetadata, 'config'> {
    formattedType: string;
    formattedStatus: string;
    formattedDates: {
        created: string;
        updated: string;
        lastSync?: string;
    };
    configSummary?: string;
}

export const formatSourceMetadata = (
    metadata: BaseMetadata
): FormattedMetadata => {
    return {
        id: metadata.id,
        name: metadata.name,
        type: metadata.type,
        status: metadata.status,
        description: metadata.description,
        tags: metadata.tags,
        error: metadata.error,
        formattedType: formatSourceType(metadata.type),
        formattedStatus: formatSourceStatus(metadata.status),
        formattedDates: {
            created: dateUtils.formatDate(metadata.createdAt),
            updated: dateUtils.formatDate(metadata.updatedAt),
            lastSync: metadata.lastSync ? 
                dateUtils.formatDate(metadata.lastSync) : 
                undefined
        },
        configSummary: metadata.config ? 
            formatConfigSummary(metadata.type, metadata.config) : 
            undefined,
        createdAt: metadata.createdAt,
        updatedAt: metadata.updatedAt,
        lastSync: metadata.lastSync
    };
};

const formatConfigSummary = (
    type: DataSourceType, 
    config: Record<string, unknown>
): string => {
    switch (type) {
        case DataSourceType.FILE:
            return `${config['type'] || 'Unknown'} file`;
        case DataSourceType.DATABASE:
            return `${config['type'] || 'Unknown'} database @ ${config['host']}`;
        case DataSourceType.API:
            return `${config['method'] || 'GET'} ${config['url'] || ''}`;
        case DataSourceType.S3:
            return `${config['bucket'] || ''} (${config['region'] || 'Unknown region'})`;
        case DataSourceType.STREAM:
            return `${config['protocol'] || 'Unknown'} stream`;
        default:
            return 'Unknown configuration';
    }
};