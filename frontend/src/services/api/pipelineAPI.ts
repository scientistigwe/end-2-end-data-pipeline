// src/services/pipelineApi.ts
import { api } from './../../services/api/client';
import { API_CONFIG } from './../../services/api/config';
import { PipelineConfig } from './types';

export const pipelineApi = {
  start: async (config: PipelineConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.PIPELINE.START, config);
  },

  getStatus: async (pipelineId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.PIPELINE.STATUS, { id: pipelineId });
  },

  stop: async (pipelineId: string) => {
    return api.post(API_CONFIG.ENDPOINTS.PIPELINE.STOP, { id: pipelineId });
  },

  getLogs: async (pipelineId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.PIPELINE.LOGS, { id: pipelineId });
  }
};
