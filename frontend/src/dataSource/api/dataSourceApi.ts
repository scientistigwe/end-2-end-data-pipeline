// src/services/api/dataSourceApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../common/types/api';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  ValidationResult,
  PreviewData,
  DataSourceFilters,
  SourceConnectionResponse,
  ConnectionTestResponse,
  SourceStatusResponse,
  SchemaInfo,
  S3BucketInfo,
  StreamMetrics,
} from '../dataSource/types/dataSources';

class DataSourceApi extends BaseApiClient {
  /**
   * Core DataSource Operations
   */
  async listDataSources(
    filters?: DataSourceFilters
  ): Promise<ApiResponse<DataSourceMetadata[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.LIST, {
      params: filters
    });
  }

  async getDataSource(id: string): Promise<ApiResponse<{
    config: DataSourceConfig;
    metadata: DataSourceMetadata;
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.GET, {
      routeParams: { id }
    });
  }

  async createDataSource(
    config: DataSourceConfig
  ): Promise<ApiResponse<DataSourceMetadata>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.DATA_SOURCES.CREATE,
      {},
      config
    );
  }

  async updateDataSource(
    id: string,
    updates: Partial<DataSourceConfig>
  ): Promise<ApiResponse<DataSourceMetadata>> {
    return this.request(
      'put',
      API_CONFIG.ENDPOINTS.DATA_SOURCES.UPDATE,
      {
        routeParams: { id }
      },
      updates
    );
  }

  async deleteDataSource(id: string): Promise<ApiResponse<void>> {
    return this.request('delete', API_CONFIG.ENDPOINTS.DATA_SOURCES.DELETE, {
      routeParams: { id }
    });
  }

  /**
   * Validation and Testing
   */
  async validateDataSource(
    id: string
  ): Promise<ApiResponse<ValidationResult>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.VALIDATE, {
      routeParams: { id }
    });
  }

  async testConnection(
    id: string
  ): Promise<ApiResponse<{
    success: boolean;
    error?: string;
  }>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.TEST, {
      routeParams: { id }
    });
  }

  /**
   * Data Preview and Sync
   */
  async previewData(
    id: string,
    options?: {
      limit?: number;
      offset?: number;
    }
  ): Promise<ApiResponse<PreviewData>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.PREVIEW, {
      routeParams: { id },
      params: options
    });
  }

  async syncData(id: string): Promise<ApiResponse<{
    jobId: string;
    status: string;
  }>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.SYNC, {
      routeParams: { id }
    });
  }

  /**
   * Type-specific Operations
   */
  
  // File Operations
  async uploadFile(
    files: File[],
    options?: { onProgress?: (progress: number) => void }
  ): Promise<ApiResponse<{ fileId: string }>> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.UPLOAD, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: options?.onProgress 
        ? (event) => {
            const progress = (event.loaded / (event.total ?? 0)) * 100;
            options?.onProgress?.(progress);
          }
        : undefined
    }, formData);
  }

  // Database Operations
  async executeDatabaseQuery(
    id: string,
    query: string,
    params?: unknown[]
  ): Promise<ApiResponse<{
    rows: unknown[];
    rowCount: number;
    fields: Array<{ name: string; type: string }>;
  }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.QUERY,
      {
        routeParams: { id }
      },
      { query, params }
    );
  }

  // S3 Operations
  async listS3Objects(
    id: string,
    prefix?: string
  ): Promise<ApiResponse<{
    objects: Array<{
      key: string;
      size: number;
      lastModified: string;
      isDirectory: boolean;
    }>;
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.LIST, {
      routeParams: { id },
      params: { prefix }
    });
  }

  // Stream Operations
  async getStreamStatus(
    id: string
  ): Promise<ApiResponse<{
    status: string;
    metrics: {
      messagesPerSecond: number;
      bytesPerSecond: number;
      lastMessage: string;
    };
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.STATUS, {
      routeParams: { id }
    });
  }


  // Connection Operations
  async connectDatabase(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.CONNECT, {}, config);
  }

  async connectApi(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.CONNECT, {}, config);
  }

  async connectS3(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.CONNECT, {}, config);
  }

  async connectStream(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.CONNECT, {}, config);
  }

  async disconnectSource(connectionId: string): Promise<ApiResponse<void>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DISCONNECT, { 
      routeParams: { connectionId } 
    });
  }

  async getSourceStatus(connectionId: string): Promise<ApiResponse<SourceStatusResponse>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.STATUS, {
      routeParams: { connectionId }
    });
  }

  // Database Operations
  async getDatabaseSchema(connectionId: string): Promise<ApiResponse<SchemaInfo>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.SCHEMA, {
      routeParams: { connectionId }
    });
  }

  async testDatabaseConnection(connectionId: string): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.TEST, {
      routeParams: { connectionId }
    });
  }

  // API Operations
  async testApiEndpoint(url: string): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.TEST, {}, { url });
  }

  async executeApiRequest(
    connectionId: string, 
    params: { method: string; url: string; body?: unknown }
  ): Promise<ApiResponse<unknown>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.EXECUTE, {
      routeParams: { connectionId }
    }, params);
  }

  // S3 Operations
  async getBucketInfo(connectionId: string): Promise<ApiResponse<S3BucketInfo>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.INFO, {
      routeParams: { connectionId }
    });
  }

  async downloadS3Object(connectionId: string, key: string): Promise<ApiResponse<Blob>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.DOWNLOAD, {
      routeParams: { connectionId },
      params: { key },
      responseType: 'blob'
    });
  }

  // Stream Operations
  async getStreamMetrics(connectionId: string): Promise<ApiResponse<StreamMetrics>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.METRICS, {
      routeParams: { connectionId }
    });
  }

  // File Operations
  async parseFile(
    fileId: string, 
    config: DataSourceConfig['config']
  ): Promise<ApiResponse<PreviewData>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.PARSE, {
      routeParams: { fileId }
    }, config);
  }
}

export const dataSourceApi = new DataSourceApi();