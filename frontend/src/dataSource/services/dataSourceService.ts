// src/dataSource/services/dataSourceService.ts
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { dateUtils } from '@/common';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  ValidationResult,
  PreviewData,
  DataSourceFilters,
  SourceConnectionResponse,
} from '../types/dataSources';
import { DATASOURCE_MESSAGES } from '../constants';

export class DataSourceService {
  static async listDataSources(filters?: DataSourceFilters): Promise<DataSourceMetadata[]> {
    try {
      const response = await dataSourceApi.listDataSources(filters);
      return response.data.map(this.transformMetadata);
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.LOAD_FAILED);
    }
  }

  static async getDataSource(id: string): Promise<{
    config: DataSourceConfig;
    metadata: DataSourceMetadata;
  }> {
    try {
      const response = await dataSourceApi.getDataSource(id);
      return {
        config: response.data.config,
        metadata: this.transformMetadata(response.data.metadata)
      };
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.FETCH_FAILED);
    }
  }

  static async createDataSource(config: DataSourceConfig): Promise<DataSourceMetadata> {
    try {
      const response = await dataSourceApi.createDataSource(config);
      return this.transformMetadata(response.data);
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.CREATE_FAILED);
    }
  }

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

  // File Operations
  static async uploadFile(
    files: File[],
    onProgress?: (progress: number) => void
  ): Promise<{ fileId: string }> {
    try {
      const response = await dataSourceApi.uploadFile(files, {
        onProgress
      });
      return response.data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED);
    }
  }

  // Connection Operations
  static async connectDatabase(
    config: DataSourceConfig['config']
  ): Promise<SourceConnectionResponse> {
    try {
      const response = await dataSourceApi.connectDatabase(config);
      return response.data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.DB_CONNECTION_FAILED);
    }
  }

  static async connectApi(
    config: DataSourceConfig['config']
  ): Promise<SourceConnectionResponse> {
    try {
      const response = await dataSourceApi.connectApi(config);
      return response.data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.API_CONNECTION_FAILED);
    }
  }

  static async connectS3(
    config: DataSourceConfig['config']
  ): Promise<SourceConnectionResponse> {
    try {
      const response = await dataSourceApi.connectS3(config);
      return response.data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.S3_CONNECTION_FAILED);
    }
  }

  static async connectStream(
    config: DataSourceConfig['config']
  ): Promise<SourceConnectionResponse> {
    try {
      const response = await dataSourceApi.connectStream(config);
      return response.data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.STREAM_CONNECTION_FAILED);
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

  private static transformMetadata(metadata: DataSourceMetadata): DataSourceMetadata {
    return {
      ...metadata,
      createdAt: dateUtils.formatDate(metadata.createdAt),
      updatedAt: dateUtils.formatDate(metadata.updatedAt),
      lastSync: metadata.lastSync ? dateUtils.formatDate(metadata.lastSync) : undefined,
      nextSync: metadata.nextSync ? dateUtils.formatDate(metadata.nextSync) : undefined
    };
  }
}

export default DataSourceService;