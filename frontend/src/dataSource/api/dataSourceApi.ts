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
    config?: ApiRequestConfig & { onProgress?: (progress: number) => void },
    data?: unknown
  ): Promise<ApiResponse<T>> {
    const { onProgress, ...restConfig } = config ?? {};
    
    const requestConfig: ApiRequestConfig = {
      ...restConfig,
      onUploadProgress: onProgress 
        ? (e: AxiosProgressEvent) => {
            if (e.total) {
              const progress = (e.loaded / e.total) * 100;
              onProgress(Math.round(progress));
            }
          }
        : undefined
    };

    return this.request(method, endpoint, requestConfig, data);
  }

  private async uploadWithProgress<T>(
    endpoint: string,
    data: unknown,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<T>> {
    return this.requestWithProgress('post', endpoint, { onProgress }, data);
  }

  private async downloadWithProgress<T>(
    endpoint: string,
    config?: ApiRequestConfig,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<T>> {
    return this.requestWithProgress('get', endpoint, { ...config, onProgress });
  }

  // Core Operations
  async listDataSources(filters?: DataSourceFilters) {
    return this.get<DataSourceMetadata[]>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.LIST,
      { params: filters }
    );
  }

  async getDataSource(id: string) {
    return this.get<{ config: DataSourceConfig; metadata: DataSourceMetadata }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.GET,
      { routeParams: { id } }
    );
  }

  async createDataSource(config: DataSourceConfig) {
    return this.post<DataSourceMetadata>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.CREATE,
      config
    );
  }

  async updateDataSource(id: string, updates: Partial<DataSourceConfig>) {
    return this.put<DataSourceMetadata>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.UPDATE,
      updates,
      { routeParams: { id } }
    );
  }

  async deleteDataSource(id: string) {
    return this.delete(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DELETE,
      { routeParams: { id } }
    );
  }

  // Validation Operations
  async validateDataSource(id: string) {
    return this.post<ValidationResult>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.VALIDATE,
      null,
      { routeParams: { id } }
    );
  }

  async testConnection(id: string) {
    return this.post<{ success: boolean; error?: string }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.TEST,
      null,
      { routeParams: { id } }
    );
  }

  // Data Sync Operations
  async previewData(id: string, options?: { limit?: number; offset?: number }) {
    return this.get<PreviewData>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.PREVIEW,
      {
        routeParams: { id },
        params: options
      }
    );
  }

  async syncData(id: string) {
    return this.post<{ jobId: string; status: string }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.SYNC,
      null,
      { routeParams: { id } }
    );
  }

  // File Operations
  async uploadFile(files: File[], onProgress?: (progress: number) => void) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.uploadWithProgress<{ fileId: string }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.UPLOAD,
      formData,
      onProgress
    );
  }

  async parseFile(fileId: string, config: DataSourceConfig['config']) {
    return this.post<PreviewData>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.PARSE,
      config,
      { routeParams: { fileId } }
    );
  }

  // Database Operations
  async executeDatabaseQuery(id: string, query: string, params?: unknown[]) {
    return this.post<{
      rows: unknown[];
      rowCount: number;
      fields: Array<{ name: string; type: string }>;
    }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.QUERY,
      { query, params },
      { routeParams: { id } }
    );
  }

  async getDatabaseSchema(connectionId: string) {
    return this.get<SchemaInfo>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.SCHEMA,
      { routeParams: { connectionId } }
    );
  }

  async testDatabaseConnection(connectionId: string) {
    return this.post<ConnectionTestResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.TEST,
      null,
      { routeParams: { connectionId } }
    );
  }

  async connectDatabase(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.CONNECT,
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
      API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.LIST,
      {
        routeParams: { id },
        params: { prefix }
      }
    );
  }

  async getBucketInfo(connectionId: string) {
    return this.get<S3BucketInfo>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.INFO,
      { routeParams: { connectionId } }
    );
  }

  async downloadS3Object(
    connectionId: string, 
    key: string, 
    onProgress?: (progress: number) => void
  ) {
    return this.downloadWithProgress<Blob>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.DOWNLOAD,
      {
        routeParams: { connectionId },
        params: { key },
        responseType: 'blob'
      },
      onProgress
    );
  }

  async connectS3(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.CONNECT,
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
      API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.STATUS,
      { routeParams: { id } }
    );
  }

  async getStreamMetrics(connectionId: string) {
    return this.get<StreamMetrics>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.METRICS,
      { routeParams: { connectionId } }
    );
  }

  async connectStream(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.CONNECT,
      config
    );
  }

  // API Operations
  async testApiEndpoint(url: string) {
    return this.post<ConnectionTestResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.API.TEST,
      { url }
    );
  }

  async executeApiRequest(
    connectionId: string,
    params: { method: string; url: string; body?: unknown }
  ) {
    return this.post<unknown>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.API.EXECUTE,
      params,
      { routeParams: { connectionId } }
    );
  }

  async connectApi(config: DataSourceConfig['config']) {
    return this.post<SourceConnectionResponse>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.API.CONNECT,
      config
    );
  }

  // Connection Operations
  async disconnectSource(connectionId: string) {
    return this.post<void>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.DISCONNECT,
      null,
      { routeParams: { connectionId } }
    );
  }

  async getConnectionStatus(connectionId: string) {
    return this.get<{ status: string; lastSync?: string; error?: string }>(
      API_CONFIG.ENDPOINTS.DATA_SOURCES.STATUS,
      { routeParams: { connectionId } }
    );
  }
}

// Export singleton instance
export const dataSourceApi = new DataSourceApi();