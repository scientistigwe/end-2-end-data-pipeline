// src/services/monitoringApi.ts
import { api } from './api/client';
import { MonitoringMetrics } from '../types/monitoring';

export const monitoringApi = {
  getPipelineMetrics: async (pipelineId: string): Promise<MonitoringMetrics> => {
    return api.get(`/monitoring/${pipelineId}/metrics`);
  },

  getSystemHealth: async () => {
    return api.get('/monitoring/health');
  },

  getResourceUsage: async (pipelineId: string) => {
    return api.get(`/monitoring/${pipelineId}/resources`);
  }
};
