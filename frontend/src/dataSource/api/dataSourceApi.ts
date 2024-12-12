// src/services/api/dataSourceApi.ts
import { DataSourceApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  ValidationResult,
  PreviewData,
  DataSourceFilters,
  SourceConnectionResponse,
  ConnectionTestResponse,
  SchemaInfo,
  S3BucketInfo,
  StreamMetrics,
} from '../../dataSource/types/dataSources';

// Interface segregation - breaking down by domain
interface CoreDataSourceOperations {
  listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<DataSourceMetadata[]>>;
  getDataSource(id: string): Promise<ApiResponse<{config: DataSourceConfig; metadata: DataSourceMetadata}>>;
  createDataSource(config: DataSourceConfig): Promise<ApiResponse<DataSourceMetadata>>;
  updateDataSource(id: string, updates: Partial<DataSourceConfig>): Promise<ApiResponse<DataSourceMetadata>>;
  deleteDataSource(id: string): Promise<ApiResponse<void>>;
}

interface ValidationOperations {
  validateDataSource(id: string): Promise<ApiResponse<ValidationResult>>;
  testConnection(id: string): Promise<ApiResponse<{success: boolean; error?: string}>>;
}

interface DataSyncOperations {
  previewData(id: string, options?: {limit?: number; offset?: number}): Promise<ApiResponse<PreviewData>>;
  syncData(id: string): Promise<ApiResponse<{jobId: string; status: string}>>;
}

interface FileOperations {
  uploadFile(files: File[], options?: { onProgress?: (progress: number) => void }): Promise<ApiResponse<{ fileId: string }>>;
  parseFile(fileId: string, config: DataSourceConfig['config']): Promise<ApiResponse<PreviewData>>;
}

interface DatabaseOperations {
  executeDatabaseQuery(
    id: string, 
    query: string, 
    params?: unknown[]
  ): Promise<ApiResponse<{
    rows: unknown[];
    rowCount: number;
    fields: Array<{ name: string; type: string }>;
  }>>;
  getDatabaseSchema(connectionId: string): Promise<ApiResponse<SchemaInfo>>;
  testDatabaseConnection(connectionId: string): Promise<ApiResponse<ConnectionTestResponse>>;
  connectDatabase(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>>;
}

interface S3Operations {
  listS3Objects(id: string, prefix?: string): Promise<ApiResponse<{
    objects: Array<{
      key: string;
      size: number;
      lastModified: string;
      isDirectory: boolean;
    }>;
  }>>;
  getBucketInfo(connectionId: string): Promise<ApiResponse<S3BucketInfo>>;
  downloadS3Object(connectionId: string, key: string): Promise<ApiResponse<Blob>>;
  connectS3(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>>;
}

interface StreamOperations {
  getStreamStatus(id: string): Promise<ApiResponse<{
    status: string;
    metrics: {
      messagesPerSecond: number;
      bytesPerSecond: number;
      lastMessage: string;
    };
  }>>;
  getStreamMetrics(connectionId: string): Promise<ApiResponse<StreamMetrics>>;
  connectStream(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>>;
}

interface ApiOperations {
  testApiEndpoint(url: string): Promise<ApiResponse<ConnectionTestResponse>>;
  executeApiRequest(
    connectionId: string,
    params: { method: string; url: string; body?: unknown }
  ): Promise<ApiResponse<unknown>>;
  connectApi(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>>;
}

interface ConnectionOperations {
  disconnectSource(connectionId: string): Promise<ApiResponse<void>>;
}

class DataSourceApi implements 
  CoreDataSourceOperations,
  ValidationOperations,
  DataSyncOperations,
  FileOperations,
  DatabaseOperations,
  S3Operations,
  StreamOperations,
  ApiOperations,
  ConnectionOperations {

  private client: DataSourceApiClient;

  constructor() {
    this.client = new DataSourceApiClient();
  }

  private buildEndpoint(endpoint: string, params: Record<string, string> = {}): string {
    let result = endpoint;
    Object.entries(params).forEach(([key, value]) => {
      result = result.replace(`:${key}`, value);
    });
    return result;
  }

  // CoreDataSourceOperations
  async listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<DataSourceMetadata[]>> {
    return this.client.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.LIST, { params: filters });
  }

  async getDataSource(id: string): Promise<ApiResponse<{
    config: DataSourceConfig;
    metadata: DataSourceMetadata;
  }>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.GET, { id }));
  }

  async createDataSource(config: DataSourceConfig): Promise<ApiResponse<DataSourceMetadata>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.CREATE, {}, config);
  }

  async updateDataSource(
    id: string,
    updates: Partial<DataSourceConfig>
  ): Promise<ApiResponse<DataSourceMetadata>> {
    return this.client.request(
      'put',
      this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.UPDATE, { id }),
      {},
      updates
    );
  }

  async deleteDataSource(id: string): Promise<ApiResponse<void>> {
    return this.client.request('delete', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.DELETE, { id }));
  }

  async disconnectSource(connectionId: string): Promise<ApiResponse<void>> {
    return this.client.request(
      'post',
      this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.DISCONNECT, { connectionId })
    );
  }

  // Validation Operations
  async validateDataSource(id: string): Promise<ApiResponse<ValidationResult>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.VALIDATE, { id }));
  }

  async testConnection(id: string): Promise<ApiResponse<{ success: boolean; error?: string }>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.API.TEST, { id }));
  }

  // Data Sync Operations
  async previewData(
    id: string,
    options?: { limit?: number; offset?: number }
  ): Promise<ApiResponse<PreviewData>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.PREVIEW, { id }), {
      params: options
    });
  }

  async syncData(id: string): Promise<ApiResponse<{ jobId: string; status: string }>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.SYNC, { id }));
  }

  // For file uploads with progress
  async uploadFile(
    files: File[],
    options?: { onProgress?: (progress: number) => void }
  ): Promise<ApiResponse<{ fileId: string }>> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
  
    const config: ApiRequestConfig = {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: options?.onProgress
    };
  
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.UPLOAD, config, formData);
  }

  async parseFile(
    fileId: string,
    config: DataSourceConfig['config']
  ): Promise<ApiResponse<PreviewData>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.PARSE, { fileId }), {}, config);
  }

  // Database Operations Implementation
  async executeDatabaseQuery(
    id: string,
    query: string,
    params?: unknown[]
  ): Promise<ApiResponse<{
    rows: unknown[];
    rowCount: number;
    fields: Array<{ name: string; type: string }>;
  }>> {
    return this.client.request(
      'post',
      this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.QUERY, { id }),
      {},
      { query, params }
    );
  }

  async getDatabaseSchema(connectionId: string): Promise<ApiResponse<SchemaInfo>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.SCHEMA, { connectionId }));
  }

  async testDatabaseConnection(connectionId: string): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.TEST, { connectionId }));
  }

  async connectDatabase(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.CONNECT, {}, config);
  }

  // S3 Operations Implementation
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
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.LIST, { id }), {
      params: { prefix }
    });
  }

  async getBucketInfo(connectionId: string): Promise<ApiResponse<S3BucketInfo>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.INFO, { connectionId }));
  }

  async downloadS3Object(connectionId: string, key: string): Promise<ApiResponse<Blob>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.DOWNLOAD, { connectionId }), {
      params: { key },
      responseType: 'blob'
    });
  }

  async connectS3(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.CONNECT, {}, config);
  }

  // Stream Operations Implementation
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
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.STATUS, { id }));
  }

  async getStreamMetrics(connectionId: string): Promise<ApiResponse<StreamMetrics>> {
    return this.client.request('get', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.METRICS, { connectionId }));
  }

  async connectStream(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.CONNECT, {}, config);
  }

  // API Operations Implementation
  async testApiEndpoint(url: string): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.TEST, {}, { url });
  }

  async executeApiRequest(
    connectionId: string,
    params: { method: string; url: string; body?: unknown }
  ): Promise<ApiResponse<unknown>> {
    return this.client.request('post', this.buildEndpoint(API_CONFIG.ENDPOINTS.DATA_SOURCES.API.EXECUTE, { connectionId }), {}, params);
  }

  async connectApi(config: DataSourceConfig['config']): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.client.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.CONNECT, {}, config);
  }
}

// Export a singleton instance
export const dataSourceApi = new DataSourceApi();


