// src/dataSource/api/dataSourceApi.ts - REFACTORED
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { RouteHelper } from '@/common/api/routes';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { 
    BaseDataSourceConfig,
    BaseMetadata,
    ValidationResult,
    PreviewData,
    DataSourceFilters,
    SourceConnectionResponse
} from '../types/base';

class DataSourceApi {
  private client = baseAxiosClient;

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.DATA_SOURCES,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
  }

    // Modified to match backend response structure
    async listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<{
        sources: {
            api: BaseMetadata[];
            databases: BaseMetadata[];
            files: BaseMetadata[];
            s3: BaseMetadata[];
            stream: BaseMetadata[];
        }
    }>> {
        return this.client.executeGet(
            RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
            { params: filters }
        );
    }

    async createDataSource(
      config: BaseDataSourceConfig
      ): Promise<ApiResponse<BaseMetadata>> {
          const endpoint = RouteHelper.getRoute('DATA_SOURCES', 'CREATE');
          return this.client.executePost(endpoint, config);
      }

      async deleteDataSource(
          sourceId: string
      ): Promise<ApiResponse<void>> {
          const endpoint = RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId });
          return this.client.executeDelete(endpoint);
  }
  
    // File Operations
    async uploadFile(
        files: File[], 
        metadata: Record<string, any>,
        onProgress?: (progress: number) => void
    ): Promise<ApiResponse<{ fileId: string; metadata: BaseMetadata }>> {
        const formData = new FormData();
        files.forEach(file => formData.append('file', file));
        formData.append('metadata', JSON.stringify(metadata));

        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
            formData,
            {
                headers: { 'Content-Type': 'multipart/form-data' },
                onUploadProgress: onProgress ? 
                    (event) => {
                        if (event.total) {
                            onProgress((event.loaded / event.total) * 100);
                        }
                    } : undefined
            }
        );
    }

    async getFileMetadata(fileId: string): Promise<ApiResponse<BaseMetadata>> {
        return this.client.executeGet(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'METADATA', { file_id: fileId })
        );
    }

    async parseFile(
        fileId: string, 
        options: Record<string, any>
    ): Promise<ApiResponse<PreviewData>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'PARSE', { file_id: fileId }),
            options
        );
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

    // Common Operations
    async validateDataSource(
        sourceId: string
    ): Promise<ApiResponse<ValidationResult>> {
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

    async disconnectSource(
        connectionId: string
    ): Promise<ApiResponse<void>> {
        return this.client.executePost(
            RouteHelper.getNestedRoute('DATA_SOURCES', 'CONNECTION', 'DISCONNECT', { connection_id: connectionId })
        );
    }
}

export const dataSourceApi = new DataSourceApi();