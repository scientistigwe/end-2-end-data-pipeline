import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { AxiosProgressEvent } from 'axios';
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
} from '../types/dataSources';

class DataSourceApi {
  private client = baseAxiosClient;

  constructor() {
    this.setupDataSourceHeaders();
  }

  private setupDataSourceHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'datasource'
    });
  }

  // Progress Tracking Methods
  private async requestWithProgress<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    config?: Omit<ApiRequestConfig, 'onUploadProgress'> & {
      onProgress?: (progress: number) => void;
    },
    data?: unknown
  ): Promise<ApiResponse<T>> {
    const { onProgress, ...restConfig } = config ?? {};
    
    const requestConfig: ApiRequestConfig = {
      ...restConfig,
      onUploadProgress: onProgress 
        ? (event: AxiosProgressEvent) => {
            if (event.total) {
              onProgress((event.loaded / event.total) * 100);
            }
          }
        : undefined
    };

    switch (method) {
      case 'GET':
        return this.client.executeGet(endpoint, requestConfig);
      case 'POST':
        return this.client.executePost(endpoint, data, requestConfig);
      case 'PUT':
        return this.client.executePut(endpoint, data, requestConfig);
      case 'DELETE':
        return this.client.executeDelete(endpoint, requestConfig);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }

  // Core Operations
  async listDataSources(filters?: DataSourceFilters) {
    return this.client.executeGet<DataSourceMetadata[]>(
      this.client.createRoute('DATA_SOURCES', 'LIST'),
      { params: filters }
    );
  }

  async getDataSource(id: string) {
    return this.client.executeGet<{ config: DataSourceConfig; metadata: DataSourceMetadata }>(
      this.client.createRoute('DATA_SOURCES', 'DETAIL', { id })
    );
  }

  async createDataSource(config: DataSourceConfig) {
    return this.client.executePost<DataSourceMetadata>(
      this.client.createRoute('DATA_SOURCES', 'CREATE'),
      config
    );
  }

  async updateDataSource(id: string, updates: Partial<DataSourceConfig>) {
    return this.client.executePut<DataSourceMetadata>(
      this.client.createRoute('DATA_SOURCES', 'UPDATE', { id }),
      updates
    );
  }

  async deleteDataSource(id: string) {
    return this.client.executeDelete(
      this.client.createRoute('DATA_SOURCES', 'DELETE', { id })
    );
  }

  // Validation & Testing
  async validateDataSource(id: string) {
    return this.client.executePost<ValidationResult>(
      this.client.createRoute('DATA_SOURCES', 'VALIDATE', { id })
    );
  }

  async testConnection(id: string) {
    return this.client.executePost<{ success: boolean; error?: string }>(
      this.client.createRoute('DATA_SOURCES', 'TEST', { id })
    );
  }

  // Preview & Sync
  async previewData(id: string, options?: { limit?: number; offset?: number }) {
    return this.client.executeGet<PreviewData>(
      this.client.createRoute('DATA_SOURCES', 'PREVIEW', { id }),
      { params: options }
    );
  }

  async syncData(id: string) {
    return this.client.executePost<{ jobId: string; status: string }>(
      this.client.createRoute('DATA_SOURCES', 'SYNC', { id })
    );
  }

  // File Operations
  async uploadFile(files: File[], onProgress?: (progress: number) => void) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.requestWithProgress<{ fileId: string }>(
      'POST',
      this.client.createNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
      { onProgress },
      formData
    );
  }

  async parseFile(fileId: string, config: DataSourceConfig['config']) {
    return this.client.executePost<PreviewData>(
      this.client.createNestedRoute('DATA_SOURCES', 'FILE', 'PARSE', { fileId }),
      config
    );
  }

  // Database Operations
  async executeDatabaseQuery(id: string, query: string, params?: unknown[]) {
    return this.client.executePost<{
      rows: unknown[];
      rowCount: number;
      fields: Array<{ name: string; type: string }>;
    }>(
      this.client.createNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { id }),
      { query, params }
    );
  }

  async getDatabaseSchema(connectionId: string) {
    return this.client.executeGet<SchemaInfo>(
      this.client.createNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connectionId })
    );
  }

  async testDatabaseConnection(connectionId: string) {
    return this.client.executePost<ConnectionTestResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'DATABASE', 'TEST', { connectionId })
    );
  }

  async connectDatabase(config: DataSourceConfig['config']) {
    return this.client.executePost<SourceConnectionResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
      config
    );
  }

  // S3 Operations
  async listS3Objects(id: string, prefix?: string) {
    return this.client.executeGet<{
      objects: Array<{
        key: string;
        size: number;
        lastModified: string;
        isDirectory: boolean;
      }>;
    }>(
      this.client.createNestedRoute('DATA_SOURCES', 'S3', 'LIST', { id }),
      { params: { prefix } }
    );
  }

  async getBucketInfo(connectionId: string) {
    return this.client.executeGet<S3BucketInfo>(
      this.client.createNestedRoute('DATA_SOURCES', 'S3', 'INFO', { connectionId })
    );
  }

  async downloadS3Object(
    connectionId: string, 
    key: string, 
    onProgress?: (progress: number) => void
  ) {
    return this.requestWithProgress<Blob>(
      'GET',
      this.client.createNestedRoute('DATA_SOURCES', 'S3', 'DOWNLOAD', { connectionId }),
      {
        params: { key },
        responseType: 'blob',
        onProgress
      }
    );
  }

  async connectS3(config: DataSourceConfig['config']) {
    return this.client.executePost<SourceConnectionResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
      config
    );
  }

  // Stream Operations
  async getStreamStatus(id: string) {
    return this.client.executeGet<{
      status: string;
      metrics: {
        messagesPerSecond: number;
        bytesPerSecond: number;
        lastMessage: string;
      };
    }>(
      this.client.createNestedRoute('DATA_SOURCES', 'STREAM', 'STATUS', { id })
    );
  }

  async getStreamMetrics(connectionId: string) {
    return this.client.executeGet<StreamMetrics>(
      this.client.createNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connectionId })
    );
  }

  async connectStream(config: DataSourceConfig['config']) {
    return this.client.executePost<SourceConnectionResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
      config
    );
  }

  // API Operations
  async testApiEndpoint(url: string) {
    return this.client.executePost<ConnectionTestResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'API', 'TEST'),
      { url }
    );
  }

  async executeApiRequest(
    connectionId: string,
    params: { method: string; url: string; body?: unknown }
  ) {
    return this.client.executePost<unknown>(
      this.client.createNestedRoute('DATA_SOURCES', 'API', 'EXECUTE', { connectionId }),
      params
    );
  }

  async connectApi(config: DataSourceConfig['config']) {
    return this.client.executePost<SourceConnectionResponse>(
      this.client.createNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
      config
    );
  }

  // Connection Operations
  async disconnectSource(connectionId: string) {
    return this.client.executePost<void>(
      this.client.createRoute('DATA_SOURCES', 'DISCONNECT', { connectionId })
    );
  }

  async getConnectionStatus(connectionId: string) {
    return this.client.executeGet<{ status: string; lastSync?: string; error?: string }>(
      this.client.createRoute('DATA_SOURCES', 'STATUS', { connectionId })
    );
  }
}

// Export singleton instance
export const dataSourceApi = new DataSourceApi();