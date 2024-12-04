// src/services/dataSourceApi.ts
import { api } from './api/client';
import { API_CONFIG } from './api/config';
import { SourceType, SourceConfig } from '../types/dataSources';

export const dataSourceApi = {
  // File operations
  uploadFile: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return api.post(API_CONFIG.ENDPOINTS.DATA_SOURCES.FILE.UPLOAD, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  // API source operations
  connectApi: async (config: SourceConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.DATA_SOURCES.API.CONNECT, config);
  },

  // Database operations
  connectDatabase: async (config: SourceConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.DATA_SOURCES.DATABASE.CONNECT, config);
  },

  // S3 operations
  connectS3: async (config: SourceConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.DATA_SOURCES.S3.CONNECT, config);
  },

  // Stream operations
  connectStream: async (config: SourceConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.DATA_SOURCES.STREAM.CONNECT, config);
  },

  // Generic source operations
  getStatus: async (connectionId: string) => {
    return api.get(`/data-sources/${connectionId}/status`);
  },

  disconnect: async (connectionId: string) => {
    return api.post(`/data-sources/${connectionId}/disconnect`);
  }
};
