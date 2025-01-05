// src/dataSource/services/dataSourceService.ts - REFACTORED
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '@/common/utils/api/apiUtils';
import type {
    BaseDataSourceConfig,
    BaseMetadata,
    ValidationResult,
    PreviewData,
    DataSourceFilters,
    SourceConnectionResponse,
    FileUploadMetadata
} from '../types/base';
import { DATASOURCE_MESSAGES } from '../constants';

export class DataSourceService {
    static async listDataSources(filters?: DataSourceFilters): Promise<BaseMetadata[]> {
        try {
            const response = await dataSourceApi.listDataSources(filters);
            const allSources = [
                ...response.data.sources.api,
                ...response.data.sources.databases,
                ...response.data.sources.files,
                ...response.data.sources.s3,
                ...response.data.sources.stream
            ];
            return allSources;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.LOAD_FAILED);
        }
    }

    // File Operations
    static async uploadFile(
        file: File,
        metadata: FileUploadMetadata,
        onProgress?: (progress: number) => void
    ): Promise<{ fileId: string; metadata: BaseMetadata }> {
        try {
            const response = await dataSourceApi.uploadFile([file], metadata, onProgress);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED);
        }
    }

    static async parseFile(
        fileId: string,
        options: Record<string, any>
    ): Promise<PreviewData> {
        try {
            const response = await dataSourceApi.parseFile(fileId, options);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.PARSE_FAILED);
        }
    }

    // Database Operations
    static async connectDatabase(
        config: BaseDataSourceConfig['config']
    ): Promise<SourceConnectionResponse> {
        try {
            const response = await dataSourceApi.connectDatabase(config);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.DB_CONNECTION_FAILED);
        }
    }

    static async getDatabaseSchema(
        connectionId: string
    ): Promise<{ tables: Array<any> }> {
        try {
            const response = await dataSourceApi.getDatabaseSchema(connectionId);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.SCHEMA_FETCH_FAILED);
        }
    }

    static async executeDatabaseQuery(
        connectionId: string,
        query: string,
        params?: unknown[]
    ): Promise<{
        rows: unknown[];
        rowCount: number;
        fields: Array<{ name: string; type: string }>;
    }> {
        try {
            const response = await dataSourceApi.executeDatabaseQuery(connectionId, query, params);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.QUERY_FAILED);
        }
    }

    // API Operations
    static async connectApi(
        config: BaseDataSourceConfig['config']
    ): Promise<SourceConnectionResponse> {
        try {
            const response = await dataSourceApi.connectApi(config);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.API_CONNECTION_FAILED);
        }
    }

    static async testApiEndpoint(
        url: string
    ): Promise<{ status: number; responseTime: number; isValid: boolean }> {
        try {
            const response = await dataSourceApi.testApiEndpoint(url);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.API_TEST_FAILED);
        }
    }

    // S3 Operations
    static async connectS3(
        config: BaseDataSourceConfig['config']
    ): Promise<SourceConnectionResponse> {
        try {
            const response = await dataSourceApi.connectS3(config);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.S3_CONNECTION_FAILED);
        }
    }

    static async listS3Objects(
        connectionId: string,
        prefix?: string
    ): Promise<{ objects: Array<any> }> {
        try {
            const response = await dataSourceApi.listS3Objects(connectionId, prefix);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.S3_LIST_FAILED);
        }
    }

    // Stream Operations
    static async connectStream(
        config: BaseDataSourceConfig['config']
    ): Promise<SourceConnectionResponse> {
        try {
            const response = await dataSourceApi.connectStream(config);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.STREAM_CONNECTION_FAILED);
        }
    }

    static async getStreamMetrics(
        connectionId: string
    ): Promise<{ messagesPerSecond: number; bytesPerSecond: number; totalMessages: number }> {
        try {
            const response = await dataSourceApi.getStreamMetrics(connectionId);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.METRICS_FETCH_FAILED);
        }
    }

    // Common Operations
    static async validateDataSource(id: string): Promise<ValidationResult> {
        try {
            const response = await dataSourceApi.validateDataSource(id);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.VALIDATION_FAILED);
        }
    }

    static async previewData(
        id: string,
        options?: { limit?: number; offset?: number }
    ): Promise<PreviewData> {
        try {
            const response = await dataSourceApi.previewData(id, options);
            return response.data;
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.PREVIEW_FAILED);
        }
    }

    static async disconnectSource(connectionId: string): Promise<void> {
        try {
            await dataSourceApi.disconnectSource(connectionId);
        } catch (err) {
            handleApiError(err);
            throw new Error(DATASOURCE_MESSAGES.ERRORS.DISCONNECT_FAILED);
        }
    }
}