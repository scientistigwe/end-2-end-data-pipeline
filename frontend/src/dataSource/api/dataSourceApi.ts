// src/dataSource/api/dataSourceApi.ts

import axios, { AxiosResponse } from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { RouteHelper } from '@/common/api/routes';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { 
    BaseDataSourceConfig,
    BaseMetadata,
    ValidationResult,
    PreviewData,
    DataSourceFilters,
    SourceConnectionResponse,
    FileUploadResponse,
    FileMetadataResponse,
    FileParseOptions,
    FileParseResponse
} from '../types/base';

class DataSourceApi {
    private client = baseAxiosClient;

    constructor() {
        this.client.setServiceConfig({
            service: ServiceType.DATA_SOURCES,
            headers: {
                'Accept': 'application/json',
            }
        });
    }

    // File Operations with proper typing
    async uploadFile(
        file: File,
        metadata: Record<string, any>,
        onProgress?: (progress: number) => void
    ): Promise<ApiResponse<FileUploadResponse>> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('metadata', JSON.stringify(metadata));

        const config: ApiRequestConfig = {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent: ProgressEvent) => {
                if (onProgress && progressEvent.total) {
                    const progress = Math.round(
                        (progressEvent.loaded * 100) / progressEvent.total
                    );
                    onProgress(progress);
                }
            },
        };

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
                formData,
                config
            );
        } catch (error) {
            console.error('File upload error:', error);
            throw this.handleError(error);
        }
    }

    async getFileMetadata(fileId: string): Promise<ApiResponse<FileMetadataResponse>> {
        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute(
                    'DATA_SOURCES',
                    'FILE',
                    'METADATA',
                    { file_id: fileId }
                )
            );
        } catch (error) {
            console.error('Get file metadata error:', error);
            throw this.handleError(error);
        }
    }

    async parseFile(
        fileId: string, 
        parseOptions: FileParseOptions
    ): Promise<ApiResponse<FileParseResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute(
                    'DATA_SOURCES',
                    'FILE',
                    'PARSE',
                    { file_id: fileId }
                ),
                parseOptions
            );
        } catch (error) {
            console.error('File parsing error:', error);
            throw this.handleError(error);
        }
    }

    // List all data sources with filters
    async listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<{
        sources: {
            files: BaseMetadata[];
            databases: BaseMetadata[];
            api: BaseMetadata[];
            s3: BaseMetadata[];
            stream: BaseMetadata[];
        }
    }>> {
        return this.client.executeGet(
            RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
            { params: filters }
        );
    }

    // Basic CRUD operations
    async createDataSource(
        config: BaseDataSourceConfig
    ): Promise<ApiResponse<BaseMetadata>> {
        return this.client.executePost(
            RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
            config
        );
    }

    async deleteDataSource(sourceId: string): Promise<ApiResponse<void>> {
        return this.client.executeDelete(
            RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId })
        );
    }

    // Validation and Preview
    async validateDataSource(sourceId: string): Promise<ApiResponse<ValidationResult>> {
        return this.client.executePost(
            RouteHelper.getRoute('DATA_SOURCES', 'VALIDATE', { source_id: sourceId })
        );
    }

    async previewData(
        sourceId: string,
        options?: { limit?: number; offset?: number }
    ): Promise<ApiResponse<PreviewData>> {
        return this.client.executeGet(
            RouteHelper.getRoute('DATA_SOURCES', 'PREVIEW', { source_id: sourceId }),
            { params: options }
        );
    }

    // Error handling
    private handleError(error: any): Error {
        if (axios.isAxiosError(error)) {
            const message = error.response?.data?.message || error.message;
            return new Error(`API Error: ${message}`);
        }
        return error instanceof Error ? error : new Error('Unknown error occurred');
    }


    // Database Operations
    async connectDatabase(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
            config
        );
    }

    async executeDatabaseQuery(
        connectionId: string,
        query: string,
        params?: unknown[]
    ): Promise<ApiResponse<{
        rows: unknown[];
        rowCount: number;
        fields: Array<{ name: string; type: string }>;
    }>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { connection_id: connectionId }),
            { query, params }
        );
    }

    async getDatabaseSchema(connectionId: string): Promise<ApiResponse<{
        tables: Array<{
            name: string;
            columns: Array<{
                name: string;
                type: string;
                nullable: boolean;
            }>;
        }>;
    }>> {
        return this.client.executeGet(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connection_id: connectionId })
        );
    }

    // API Operations
    async connectApi(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
            config
        );
    }

    async testApiEndpoint(url: string): Promise<ApiResponse<{
        status: number;
        responseTime: number;
        isValid: boolean;
    }>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
            { url }
        );
    }

    // S3 Operations
    async connectS3(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
            config
        );
    }

    async listS3Objects(
        connectionId: string,
        prefix?: string
    ): Promise<ApiResponse<{
        objects: Array<{
            key: string;
            size: number;
            lastModified: string;
        }>;
    }>> {
        return this.client.executeGet(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
            { params: { prefix } }
        );
    }

    // Stream Operations
    async connectStream(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
            config
        );
    }

    async getStreamMetrics(connectionId: string): Promise<ApiResponse<{
        messagesPerSecond: number;
        bytesPerSecond: number;
        totalMessages: number;
    }>> {
        return this.client.executeGet(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connection_id: connectionId })
        );
    }

    async disconnectSource(
        connectionId: string
    ): Promise<ApiResponse<void>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'CONNECTION', 'DISCONNECT', { connection_id: connectionId })
        );
    }
}


export const dataSourceApi = new DataSourceApi();

// Type definitions (should be in a separate types file)
export interface FileUploadProgressEvent extends ProgressEvent {
    total: number;
    loaded: number;
}