// src/dataSource/types/fileSource.ts

import type { BaseDataSourceConfig, BaseMetadata, DataSourceType } from './base';

export interface FileSourceConfig extends BaseDataSourceConfig {
    type: DataSourceType.FILE;
    config: {
        type: 'csv' | 'json' | 'parquet' | 'excel';
        encoding?: string;
        delimiter?: string;
        hasHeader?: boolean;
        sheet?: string;  // For Excel files
        skipRows?: number;
        parseOptions?: {
            dateFormat?: string;
            nullValues?: string[];
            compression?: string;
            schema?: Record<string, string>;  // Column name -> type mapping
        };
        storageOptions?: {
            path?: string;
            retention?: number;  // in days
            compress?: boolean;
        };
    };
}

export interface FileMetadata extends BaseMetadata {
    type: DataSourceType.FILE;
    stats: {
        filename: string;
        originalName: string;
        size: number;
        rowCount?: number;
        lastModified: string;
        mimeType?: string;
        encoding?: string;
        delimiter?: string;
        columnCount?: number;
        compressionType?: string;
        hash?: string;
    };
}

export interface FileUploadResponse {
    fileId: string;
    sourceId: string;
    metadata: FileMetadata;
}

export interface FileParseOptions {
    encoding?: string;
    delimiter?: string;
    hasHeader?: boolean;
    sheet?: string;
    skipRows?: number;
    limit?: number;
    parseOptions?: {
        dateFormat?: string;
        nullValues?: string[];
    };
}

export interface FileParseResponse {
    columns: Array<{
        name: string;
        type: string;
        nullable: boolean;
        index: number;
        sampleValues?: unknown[];
    }>;
    data: unknown[][];
    totalRows: number;
    parseErrors?: Array<{
        row: number;
        column?: string;
        message: string;
    }>;
}

// Component Props Types
export interface FileSourceFormProps {
    onSubmit: (config: FileSourceConfig) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<FileSourceConfig>;
    isLoading?: boolean;
}

export interface FileSourceCardProps {
    id: string;
    metadata: FileMetadata;
    config: FileSourceConfig;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onPreview?: (id: string) => void;
}

export interface FilePreviewProps {
    sourceId: string;
    metadata: FileMetadata;
    onClose: () => void;
    maxRows?: number;
}