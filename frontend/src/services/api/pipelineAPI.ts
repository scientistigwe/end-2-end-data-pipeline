// src/services/pipelineApi.ts
import { api } from './../../services/api/client';
import { API_CONFIG } from './../../services/api/config';
import type { 
  PipelineConfig, 
  ApiResponse, 
  PipelineResponse,
  PipelineLogs 
} from './types';

/**
 * Pipeline API client for managing pipeline operations
 */
export const pipelineApi = {
  /**
   * Start a new pipeline with the given configuration
   */
  start: async (config: PipelineConfig): Promise<ApiResponse<PipelineResponse>> => {
    const endpoint = formatEndpoint(API_CONFIG.ENDPOINTS.PIPELINES.START, {});
    return api.post(endpoint, config);
  },

  /**
   * Get the current status of a pipeline
   */
  getStatus: async (pipelineId: string): Promise<ApiResponse<PipelineResponse>> => {
    const endpoint = formatEndpoint(API_CONFIG.ENDPOINTS.PIPELINES.STATUS, { id: pipelineId });
    return api.get(endpoint);
  },

  /**
   * Stop a running pipeline
   */
  stop: async (pipelineId: string): Promise<ApiResponse<void>> => {
    const endpoint = formatEndpoint(API_CONFIG.ENDPOINTS.PIPELINES.STOP, { id: pipelineId });
    return api.post(endpoint, { id: pipelineId });
  },

  /**
   * Get logs for a pipeline
   */
  getLogs: async (pipelineId: string): Promise<ApiResponse<PipelineLogs>> => {
    const endpoint = formatEndpoint(API_CONFIG.ENDPOINTS.PIPELINES.LOGS, { id: pipelineId });
    return api.get(endpoint);
  }
};

/**
 * Helper function to format endpoints with parameters
 */
const formatEndpoint = (endpoint: string, params: Record<string, string>): string => {
  let formattedEndpoint = endpoint;
  Object.entries(params).forEach(([key, value]) => {
    formattedEndpoint = formattedEndpoint.replace(`:${key}`, value);
  });
  return formattedEndpoint;
};