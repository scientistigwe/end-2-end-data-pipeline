// src/dataSource/api/dataSourceApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { AxiosProgressEvent } from 'axios';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  DataSourceFilters,
  ConnectionTestResponse,
} from '../types';

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
      RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
      { params: filters }
    );
  }

  async getDataSource(id: string) {
    return this.client.executeGet<{ config: DataSourceConfig; metadata: DataSourceMetadata }>(
      RouteHelper.getRoute('DATA_SOURCES', 'GET', { source_id: id })
    );
  }

  async createDataSource(config: DataSourceConfig) {
    return this.client.executePost<DataSourceMetadata>(
      RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
      config
    );
  }

  async updateDataSource(id: string, updates: Partial<DataSourceConfig>) {
    return this.client.executePut<DataSourceMetadata>(
      RouteHelper.getRoute('DATA_SOURCES', 'UPDATE', { source_id: id }),
      updates
    );
  }

  // File Operations Example
  async uploadFile(files: File[], onProgress?: (progress: number) => void) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.requestWithProgress<{ fileId: string }>(
      'POST',
      RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
      { onProgress },
      formData
    );
  }

  // Database Operations Example
  async executeDatabaseQuery(connectionId: string, query: string, params?: unknown[]) {
    return this.client.executePost<{
      rows: unknown[];
      rowCount: number;
      fields: Array<{ name: string; type: string }>;
    }>(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { connection_id: connectionId }),
      { query, params }
    );
  }

  // S3 Operations Example
  async listS3Objects(connectionId: string, prefix?: string) {
    return this.client.executeGet<{
      objects: Array<{
        key: string;
        size: number;
        lastModified: string;
        isDirectory: boolean;
      }>;
    }>(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
      { params: { prefix } }
    );
  }

  // Stream Operations Example
  async getStreamStatus(connectionId: string) {
    return this.client.executeGet<{
      status: string;
      metrics: {
        messagesPerSecond: number;
        bytesPerSecond: number;
        lastMessage: string;
      };
    }>(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'STATUS', { connection_id: connectionId })
    );
  }

  // API Operations Example
  async testApiEndpoint(url: string) {
    return this.client.executePost<ConnectionTestResponse>(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
      { url }
    );
  }
}

export const dataSourceApi = new DataSourceApi();