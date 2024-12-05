import { AxiosProgressEvent } from 'axios';
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import {
  ApiResponse
} from '../../types/api';
import {
  SourceConnectionStatus,
  SourceMetadata,
  SourceValidationResponse,
  SourceConnectionResponse,
  ConnectionTestResponse,
  S3Object,
  StreamMetrics
} from './../../types/source';
import {
  FileSourceConfig,
  ApiSourceConfig,
  DBSourceConfig,
  S3SourceConfig,
  StreamSourceConfig,

} from '../../hooks/dataSource/types';


export class DataSourceApi extends BaseApiClient {
  /**
   * File Source Operations
   */
  async uploadFile(
    files: File[],
    options?: { onProgress?: (progress: number) => void }
  ): Promise<ApiResponse<FileSourceConfig>> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.UPLOAD, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: options?.onProgress 
        ? (event: AxiosProgressEvent) => {
            const progress = (event.loaded / (event.total ?? 0)) * 100;
            options.onProgress!(progress);
          }
        : undefined
    }, formData);
  }


  async getFileMetadata(fileId: string): Promise<ApiResponse<SourceMetadata>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.METADATA, {
      routeParams: { id: fileId }
    });
  }

  /**
   * API Source Operations
   */
  async connectApi(
    config: ApiSourceConfig['config']
  ): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.CONNECT, {}, config);
  }

  async testApiConnection(
    connectionId: string
  ): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.API.TEST, {
      routeParams: { id: connectionId }
    });
  }

  /**
   * Database Source Operations
   */
  async connectDatabase(
    config: DBSourceConfig['config']
  ): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.CONNECT, {}, config);
  }

  async testDatabaseConnection(
    connectionId: string
  ): Promise<ApiResponse<ConnectionTestResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.TEST, {
      routeParams: { id: connectionId }
    });
  }

  /**
   * S3 Source Operations
   */
  async connectS3(
    config: S3SourceConfig['config']
  ): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.CONNECT, {}, config);
  }

  async listS3Objects(
    connectionId: string,
    path?: string
  ): Promise<ApiResponse<{ objects: S3Object[] }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.LIST, {
      routeParams: { id: connectionId },
      params: path ? { path } : undefined
    });
  }

  /**
   * Stream Source Operations
   */
  async connectStream(
    config: StreamSourceConfig['config']
  ): Promise<ApiResponse<SourceConnectionResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.CONNECT, {}, config);
  }

  async getStreamStatus(
    connectionId: string
  ): Promise<ApiResponse<{
    status: SourceConnectionStatus;
    metrics: StreamMetrics;
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.STATUS, {
      routeParams: { id: connectionId }
    });
  }

  /**
   * Generic Source Operations
   */
  async getSourceStatus(
    connectionId: string
  ): Promise<ApiResponse<{
    status: SourceConnectionStatus;
    lastChecked: string;
    error?: string;
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.DATA_SOURCES.STATUS, {
      routeParams: { id: connectionId }
    });
  }

  async disconnectSource(connectionId: string): Promise<ApiResponse<void>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.DISCONNECT, {
      routeParams: { id: connectionId }
    });
  }

  async validateSource(
    connectionId: string
  ): Promise<ApiResponse<SourceValidationResponse>> {
    return this.request('post', API_CONFIG.ENDPOINTS.DATA_SOURCES.VALIDATE, {
      routeParams: { id: connectionId }
    });
  }

  /**
   * Error handling helper method
   */
  private handleError(error: unknown): never {
    if (error instanceof Error) {
      throw new Error(`DataSource API Error: ${error.message}`);
    }
    throw new Error('An unknown error occurred in DataSource API');
  }
}

// Export a singleton instance
export const dataSourceApi = new DataSourceApi();