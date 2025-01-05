// src/dataSource/types/apiSource.ts

import type { BaseDataSourceConfig, BaseMetadata, DataSourceType } from './base';

export interface ApiSourceConfig extends BaseDataSourceConfig {
    type: DataSourceType.API;
    config: {
        url: string;
        method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
        headers?: Record<string, string>;
        queryParams?: Record<string, string>;
        body?: unknown;
        auth?: {
            type: 'none' | 'basic' | 'bearer' | 'oauth2';
            credentials?: {
                username?: string;
                password?: string;
                token?: string;
                clientId?: string;
                clientSecret?: string;
            };
            oauth2Config?: {
                tokenUrl: string;
                authUrl?: string;
                scope?: string[];
                grantType: 'client_credentials' | 'authorization_code' | 'password';
            };
        };
        options?: {
            timeout?: number;
            retries?: number;
            rateLimit?: {
                requests: number;
                period: number;  // in seconds
            };
            validation?: {
                validateStatus?: (status: number) => boolean;
                validateResponse?: (data: unknown) => boolean;
            };
            transformation?: {
                responsePath?: string;  // JSONPath for response extraction
                dateFields?: string[];
                numberFields?: string[];
            };
        };
    };
}

export interface ApiMetadata extends BaseMetadata {
    type: DataSourceType.API;
    stats: {
        lastResponse?: {
            status: number;
            timestamp: string;
            duration: number;
        };
        metrics: {
            totalRequests: number;
            successRate: number;
            averageResponseTime: number;
            errorRate: number;
            lastError?: {
                timestamp: string;
                status: number;
                message: string;
            };
        };
        rateLimit?: {
            remaining: number;
            reset: string;
            limit: number;
        };
    };
}

export interface ApiTestResult {
    success: boolean;
    responseTime: number;
    statusCode: number;
    headers?: Record<string, string>;
    responsePreview?: unknown;
    error?: {
        code: string;
        message: string;
        details?: unknown;
    };
}

export interface ApiRequestConfig {
    headers?: Record<string, string>;
    queryParams?: Record<string, string>;
    body?: unknown;
    timeout?: number;
}

export interface ApiRequestResult {
    status: number;
    headers: Record<string, string>;
    data: unknown;
    duration: number;
    size: number;
}

// Component Props Types
export interface ApiSourceFormProps {
    onSubmit: (config: ApiSourceConfig) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<ApiSourceConfig>;
    isLoading?: boolean;
    onTest?: (url: string) => Promise<ApiTestResult>;
}

export interface ApiSourceCardProps {
    id: string;
    metadata: ApiMetadata;
    config: ApiSourceConfig;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onTest?: (id: string) => void;
}

export interface ApiRequestEditorProps {
    connectionId: string;
    config: ApiSourceConfig;
    onExecute: (request: ApiRequestConfig) => Promise<ApiRequestResult>;
    onSave?: (config: Partial<ApiSourceConfig>) => Promise<void>;
}

export interface ApiMonitorProps {
    connectionId: string;
    metadata: ApiMetadata;
    onRefresh?: () => void;
    refreshInterval?: number;
}