// src/dataSource/api/dataSourceApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { AxiosProgressEvent } from 'axios';
import type { BaseDataSourceConfig, BaseMetadata } from '../types/base';

import type { DataSourceFilters } from '../types/dataSourceFilters';

import type { ConnectionTestResponse } from '../types/responses';

interface SourcesResponse {
  sources: {
    api: BaseMetadata[];
    databases: BaseMetadata[];
    files: BaseMetadata[];
    s3: BaseMetadata[];
    stream: BaseMetadata[];
  }
}

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
  async listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<SourcesResponse>> {
    const response = await this.client.executeGet<SourcesResponse>(
      RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
      { params: filters }
    );
    
    return response;  // BaseClient already handles the ApiResponse structure
  }

  async getDataSource(id: string): Promise<ApiResponse<{ 
    config: BaseDataSourceConfig; 
    metadata: BaseMetadata 
  }>> {
    return this.client.executeGet(
      RouteHelper.getRoute('DATA_SOURCES', 'GET', { source_id: id })
    );
  }

  async createDataSource(config: BaseDataSourceConfig): Promise<ApiResponse<BaseMetadata>> {
    return this.client.executePost(
      RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
      config
    );
  }

  async updateDataSource(id: string, updates: Partial<BaseDataSourceConfig>): Promise<ApiResponse<BaseMetadata>> {
    return this.client.executePut(
      RouteHelper.getRoute('DATA_SOURCES', 'UPDATE', { source_id: id }),
      updates
    );
  }

  async deleteDataSource(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: id })
    );
  }

  // File Operations
  async uploadFile(
    files: File[], 
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<{ fileId: string }>> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.requestWithProgress(
      'POST',
      RouteHelper.getNestedRoute('DATA_SOURCES', 'FILE', 'UPLOAD'),
      { onProgress },
      formData
    );
  }

  // Database Operations
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

  // S3 Operations
  async listS3Objects(
    connectionId: string, 
    prefix?: string
  ): Promise<ApiResponse<{
    objects: Array<{
      key: string;
      size: number;
      lastModified: string;
      isDirectory: boolean;
    }>;
  }>> {
    return this.client.executeGet(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
      { params: { prefix } }
    );
  }

  // Stream Operations
  async getStreamStatus(
    connectionId: string
  ): Promise<ApiResponse<{
    status: string;
    metrics: {
      messagesPerSecond: number;
      bytesPerSecond: number;
      lastMessage: string;
    };
  }>> {
    return this.client.executeGet(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'STATUS', { connection_id: connectionId })
    );
  }

  // API Operations
  async testApiEndpoint(url: string): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.client.executePost(
      RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
      { url }
    );
  }
}

export const dataSourceApi = new DataSourceApi();