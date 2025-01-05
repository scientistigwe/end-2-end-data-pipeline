// src/dataSource/types/s3Source.ts

import type { BaseDataSourceConfig, BaseMetadata, DataSourceType } from './base';

export interface S3SourceConfig extends BaseDataSourceConfig {
    type: DataSourceType.S3;
    config: {
        bucket: string;
        region: string;
        accessKeyId: string;
        secretAccessKey: string;
        prefix?: string;
        endpoint?: string;  // For custom endpoints
        credentials?: {
            sessionToken?: string;
            roleArn?: string;
            externalId?: string;
        };
        options?: {
            sslEnabled?: boolean;
            forcePathStyle?: boolean;
            accelerateEnabled?: boolean;
            retries?: number;
            timeout?: number;
            multipartUploadSize?: number;  // in bytes
            maxKeys?: number;  // for listing
        };
        filters?: {
            prefix?: string;
            delimiter?: string;
            extensions?: string[];
            maxSize?: number;
            minSize?: number;
            afterDate?: string;
            beforeDate?: string;
        };
    };
}

export interface S3Metadata extends BaseMetadata {
    type: DataSourceType.S3;
    stats: {
        bucketName: string;
        region: string;
        totalObjects: number;
        totalSize: number;
        lastSync: string;
        versioning?: boolean;
        encryption?: boolean;
        publicAccess?: boolean;
        metrics?: {
            requestCount: number;
            downloadBytes: number;
            uploadBytes: number;
            errors: number;
        };
    };
}

export interface S3Object {
    key: string;
    size: number;
    lastModified: string;
    etag: string;
    storageClass: string;
    isDirectory: boolean;
    contentType?: string;
    metadata?: Record<string, string>;
    versionId?: string;
}

export interface S3BucketInfo {
    name: string;
    region: string;
    createdAt: string;
    versioning: boolean;
    encryption?: {
        enabled: boolean;
        type: string;
    };
    metrics: {
        objectCount: number;
        totalSize: number;
        lastModified: string;
    };
    cors?: Array<{
        allowedMethods: string[];
        allowedOrigins: string[];
        allowedHeaders: string[];
    }>;
    lifecycle?: Array<{
        id: string;
        prefix: string;
        enabled: boolean;
        expiration?: number;
        transition?: {
            days: number;
            storageClass: string;
        };
    }>;
}

export interface S3UploadConfig {
    key: string;
    contentType?: string;
    metadata?: Record<string, string>;
    tags?: Record<string, string>;
    acl?: string;
    storageClass?: string;
    encryption?: {
        algorithm: string;
        keyId?: string;
    };
}

// Component Props Types
export interface S3SourceFormProps {
    onSubmit: (config: S3SourceConfig) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<S3SourceConfig>;
    isLoading?: boolean;
    onTest?: (config: Partial<S3SourceConfig>) => Promise<void>;
}

export interface S3SourceCardProps {
    id: string;
    metadata: S3Metadata;
    config: S3SourceConfig;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onExplore?: (id: string) => void;
}

export interface S3BrowserProps {
    connectionId: string;
    bucket: string;
    prefix?: string;
    onNavigate?: (prefix: string) => void;
    onSelect?: (object: S3Object) => void;
    onUpload?: (files: File[], config: S3UploadConfig) => Promise<void>;
    onDelete?: (keys: string[]) => Promise<void>;
}

export interface S3StatsProps {
    bucketInfo: S3BucketInfo;
    refreshInterval?: number;
    onRefresh?: () => void;
}