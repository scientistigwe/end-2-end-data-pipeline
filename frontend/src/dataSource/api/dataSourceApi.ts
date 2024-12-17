// src/dataSource/api/dataSourceApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
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

class DataSourceApi extends BaseClient {
  constructor() {
    super({
      baseURL: import.meta.env.VITE_DATASOURCE_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'datasource'
      }
    });
  }

  // Progress Tracking Methods
  private async requestWithProgress<T>(
    method: 'get' | 'post' | 'put' | 'delete',
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

    return this.request(method, endpoint, requestConfig, data);
  }

  // Core Operations
  async listDataSources(filters?: DataSourceFilters) {
    return this.get<DataSourceMetadata[]>(
      this.getRoute('DATA_SOURCES', 'LIST'),
      { params: filters }
    );
  }

  async getDataSource(id: string) {
    return this.get<{ config: DataSourceConfig; metadata: DataSourceMetadata }>(
      this.getRoute('DATA_SOURCES', 'DETAIL', { id })
    );
  }

  async createDataSource(config: DataSourceConfig) {
    return this.post<DataSourceMetadata>(
      this.getRoute('DATA_SOURCES', 'CREATE'),
      config
    );
  }

  async updateDataSource(id: string, updates: Partial<DataSourceConfig>) {
    return this.put<DataSourceMetadata>(
      this.getRoute('DATA_SOURCES', 'UPDATE', { id }),
      updates
    );
  }

  async deleteDataSource(id: string) {
    return this.delete(
      this.getRoute('DATA_SOURCES', 'DELETE', { id })
    );
  }

  // Validation & Testing
  async validateDataSource(id: string) {
    return this.post<ValidationResult>(
      this.getRoute('DATA_SOURCES', 'VALIDATE', { id })
    );
  }

  async testConnection(id: string) {
    return this.post<{ success: boolean; error?: string }>(
      this.getRoute('DATA_SOURCES', 'TEST', { id })
    );
  }

  // Preview & Sync
  async previewData(id: string, options?: { limit?: number; offset?: number }) {
    return this.get<PreviewData>(
      this.getRoute('DATA_SOURCES', 'PREVIEW', { id }),
      { params: options }
    );
  }

  async syncData(id: string) {
    return this.post<{ jobId: string; status: string }>(
      this.getRoute('DATA_SOURCES', 'SYNC', { id })
    );
  }

  // File Operations
  async uploadFile(files: File[], onProgress?: (progress: number) => void) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.requestWithProgress<{ fileId: string }>(
      'post',
      this.getNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
      { onProgress },
      formData
    );
  }

  async parseFile(fileId: string, config: DataSourceConfig['config']) {
    return this.post<PreviewData>(
      this.getNestedRoute('DATA_SOURCES', 'FILE', 'PARSE', { fileId }),
      config
    );
  }

  // Database Operations
  async executeDatabaseQuery(id: string, query: string, params?: unknown[]) {
    return this.post<{
      rows: unknown[];
      rowCount: number;
      fields: Array<{ name: string; type: string }>;
    }>(
      this.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { id }),
      { query, params }
    );
  }

  async getDatabaseSchema(connectionId: string) {
    return this.get<SchemaInfo>(
      this.getNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connectionId })
    );
  }

  async testDatabaseConnection(connectionId: string) {
    return this.post<ConnectionTestResponse>(
      this.getNestedRoute('DATA_SOURCES', 'DATABASE', 'TEST', { connectionId })
    );
  }

  async connectDatabase(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      this.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
      config
    );
  }

  // S3 Operations
  async listS3Objects(id: string, prefix?: string) {
    return this.get<{
      objects: Array<{
        key: string;
        size: number;
        lastModified: string;
        isDirectory: boolean;
      }>;
    }>(
      this.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { id }),
      { params: { prefix } }
    );
  }

  async getBucketInfo(connectionId: string) {
    return this.get<S3BucketInfo>(
      this.getNestedRoute('DATA_SOURCES', 'S3', 'INFO', { connectionId })
    );
  }

  async downloadS3Object(
    connectionId: string, 
    key: string, 
    onProgress?: (progress: number) => void
  ) {
    return this.requestWithProgress<Blob>(
      'get',
      this.getNestedRoute('DATA_SOURCES', 'S3', 'DOWNLOAD', { connectionId }),
      {
        params: { key },
        responseType: 'blob',
        onProgress
      }
    );
  }

  async connectS3(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      this.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
      config
    );
  }

  // Stream Operations
  async getStreamStatus(id: string) {
    return this.get<{
      status: string;
      metrics: {
        messagesPerSecond: number;
        bytesPerSecond: number;
        lastMessage: string;
      };
    }>(
      this.getNestedRoute('DATA_SOURCES', 'STREAM', 'STATUS', { id })
    );
  }

  async getStreamMetrics(connectionId: string) {
    return this.get<StreamMetrics>(
      this.getNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connectionId })
    );
  }

  async connectStream(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      this.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
      config
    );
  }

  // API Operations
  async testApiEndpoint(url: string) {
    return this.post<ConnectionTestResponse>(
      this.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
      { url }
    );
  }

  async executeApiRequest(
    connectionId: string,
    params: { method: string; url: string; body?: unknown }
  ) {
    return this.post<unknown>(
      this.getNestedRoute('DATA_SOURCES', 'API', 'EXECUTE', { connectionId }),
      params
    );
  }

  async connectApi(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      this.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
      config
    );
  }

  // Connection Operations
  async disconnectSource(connectionId: string) {
    return this.post<void>(
      this.getRoute('DATA_SOURCES', 'DISCONNECT', { connectionId })
    );
  }

  async getConnectionStatus(connectionId: string) {
    return this.get<{ status: string; lastSync?: string; error?: string }>(
      this.getRoute('DATA_SOURCES', 'STATUS', { connectionId })
    );
  }
}

// Export singleton instance
export const dataSourceApi = new DataSourceApi();