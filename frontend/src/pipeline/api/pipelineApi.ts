  // src/pipeline/api/pipelineApi.ts
  import { ApiClient } from './client';
  import { API_CONFIG } from './config';
  import type {
    Pipeline,
    PipelineConfig,
    PipelineRun,
    PipelineLogs,
    PipelineMetrics
  } from '../types/pipeline';
  
  export class PipelineApi extends ApiClient {
    // Pipeline CRUD Operations
    async listPipelines(params?: {
      page?: number;
      limit?: number;
      status?: string[];
      mode?: string[];
    }): Promise<Pipeline[]> {
      return this.request('GET', API_CONFIG.ENDPOINTS.LIST, { params });
    }
  
    async createPipeline(config: PipelineConfig): Promise<Pipeline> {
      return this.request('POST', API_CONFIG.ENDPOINTS.CREATE, {
        data: config
      });
    }
  
    async getPipeline(id: string): Promise<Pipeline> {
      const url = API_CONFIG.ENDPOINTS.GET.replace(':id', id);
      return this.request('GET', url);
    }
  
    async updatePipeline(
      id: string,
      updates: Partial<PipelineConfig>
    ): Promise<Pipeline> {
      const url = API_CONFIG.ENDPOINTS.UPDATE.replace(':id', id);
      return this.request('PUT', url, { data: updates });
    }
  
    async deletePipeline(id: string): Promise<void> {
      const url = API_CONFIG.ENDPOINTS.DELETE.replace(':id', id);
      return this.request('DELETE', url);
    }
  
    // Pipeline Execution Controls
    async startPipeline(
      id: string,
      options?: { mode?: string; params?: Record<string, unknown> }
    ): Promise<PipelineRun> {
      const url = API_CONFIG.ENDPOINTS.START.replace(':id', id);
      return this.request('POST', url, { data: options });
    }
  
    async stopPipeline(id: string): Promise<void> {
      const url = API_CONFIG.ENDPOINTS.STOP.replace(':id', id);
      return this.request('POST', url);
    }
  
    async pausePipeline(id: string): Promise<void> {
      const url = API_CONFIG.ENDPOINTS.PAUSE.replace(':id', id);
      return this.request('POST', url);
    }
  
    async resumePipeline(id: string): Promise<void> {
      const url = API_CONFIG.ENDPOINTS.RESUME.replace(':id', id);
      return this.request('POST', url);
    }
  
    async retryPipeline(id: string): Promise<PipelineRun> {
      const url = API_CONFIG.ENDPOINTS.RETRY.replace(':id', id);
      return this.request('POST', url);
    }
  
    // Pipeline Monitoring
    async getPipelineLogs(
      id: string,
      options?: {
        startTime?: string;
        endTime?: string;
        level?: string;
        limit?: number;
        page?: number;
      }
    ): Promise<PipelineLogs> {
      const url = API_CONFIG.ENDPOINTS.LOGS.replace(':id', id);
      return this.request('GET', url, { params: options });
    }
  
    async getPipelineMetrics(
      id: string,
      timeRange?: {
        start: string;
        end: string;
      }
    ): Promise<PipelineMetrics[]> {
      const url = API_CONFIG.ENDPOINTS.METRICS.replace(':id', id);
      return this.request('GET', url, { params: timeRange });
    }
  
    // Pipeline Runs
    async getPipelineRuns(
      id: string,
      options?: {
        limit?: number;
        page?: number;
        status?: string;
      }
    ): Promise<PipelineRun[]> {
      const url = API_CONFIG.ENDPOINTS.RUNS.replace(':id', id);
      return this.request('GET', url, { params: options });
    }
  
    async validatePipelineConfig(config: PipelineConfig): Promise<{
      valid: boolean;
      errors?: string[];
    }> {
      return this.request('POST', API_CONFIG.ENDPOINTS.VALIDATE, {
        data: config
      });
    }
  }
  
