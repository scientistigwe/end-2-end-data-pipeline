// src/pipeline/api/pipelineApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  Pipeline,
  PipelineConfig,
  PipelineRun,
  PipelineLogs,
  PipelineMetrics
} from '../types/pipeline';

class PipelineApi extends BaseClient {
  private readonly PIPELINE_EVENTS = {
    STATUS_CHANGE: 'pipeline:statusChange',
    RUN_COMPLETE: 'pipeline:runComplete',
    ERROR: 'pipeline:error'
  };

  constructor() {
    super({
      baseURL: import.meta.env.VITE_PIPELINE_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'pipeline'
      }
    });

    this.setupPipelineInterceptors();
  }

  // Interceptors and Error Handling
  private setupPipelineInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Pipeline-Timestamp', new Date().toISOString());
        return config;
      }
    );

    this.client.interceptors.response.use(
      response => response,
      error => {
        const enhancedError = this.handlePipelineError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  private handlePipelineError(error: any): Error {
    if (error.response?.status === 409) {
      return new Error('Pipeline is already running');
    }
    if (error.response?.status === 404) {
      return new Error('Pipeline not found');
    }
    if (error.response?.status === 400) {
      return new Error(`Invalid pipeline configuration: ${error.response.data?.message}`);
    }
    return error;
  }

  private notifyError(error: Error): void {
    window.dispatchEvent(
      new CustomEvent(this.PIPELINE_EVENTS.ERROR, {
        detail: { error: error.message }
      })
    );
  }

  // Pipeline CRUD Operations
  async listPipelines(params?: {
    page?: number;
    limit?: number;
    status?: string[];
    mode?: string[];
  }): Promise<ApiResponse<Pipeline[]>> {
    return this.get(API_CONFIG.ENDPOINTS.PIPELINES.LIST, { params });
  }

  async createPipeline(config: PipelineConfig): Promise<ApiResponse<Pipeline>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.CREATE,
      config
    );
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.get(
      API_CONFIG.ENDPOINTS.PIPELINES.GET,
      { routeParams: { id } }
    );
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<Pipeline>> {
    return this.put(
      API_CONFIG.ENDPOINTS.PIPELINES.UPDATE,
      updates,
      { routeParams: { id } }
    );
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    return this.delete(
      API_CONFIG.ENDPOINTS.PIPELINES.DELETE,
      { routeParams: { id } }
    );
  }

  // Pipeline Execution Controls
  async startPipeline(
    id: string,
    options?: { 
      mode?: string; 
      params?: Record<string, unknown>
    }
  ): Promise<ApiResponse<PipelineRun>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.START,
      options,
      { routeParams: { id } }
    );
  }

  async stopPipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.STOP,
      null,
      { routeParams: { id } }
    );
  }

  async pausePipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.PAUSE,
      null,
      { routeParams: { id } }
    );
  }

  async resumePipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.RESUME,
      null,
      { routeParams: { id } }
    );
  }

  async retryPipeline(id: string): Promise<ApiResponse<PipelineRun>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.RETRY,
      null,
      { routeParams: { id } }
    );
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
  ): Promise<ApiResponse<PipelineLogs>> {
    return this.get(
      API_CONFIG.ENDPOINTS.PIPELINES.LOGS,
      {
        routeParams: { id },
        params: options
      }
    );
  }

  async getPipelineMetrics(
    id: string,
    timeRange?: {
      start: string;
      end: string;
    }
  ): Promise<ApiResponse<PipelineMetrics[]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.PIPELINES.METRICS,
      {
        routeParams: { id },
        params: timeRange
      }
    );
  }

  // Pipeline Runs
  async getPipelineRuns(
    id: string,
    options?: {
      limit?: number;
      page?: number;
      status?: string;
    }
  ): Promise<ApiResponse<PipelineRun[]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.PIPELINES.RUNS,
      {
        routeParams: { id },
        params: options
      }
    );
  }

  // Validation
  async validatePipelineConfig(config: PipelineConfig): Promise<ApiResponse<{
    valid: boolean;
    errors?: string[];
  }>> {
    return this.post(
      API_CONFIG.ENDPOINTS.PIPELINES.VALIDATE,
      config
    );
  }

  // Helper Methods
  async waitForPipelineCompletion(
    id: string,
    options?: {
      pollingInterval?: number;
      timeout?: number;
    }
  ): Promise<ApiResponse<PipelineRun>> {
    const interval = options?.pollingInterval || 5000;
    const timeout = options?.timeout || 300000;
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const response = await this.getPipeline(id);
      const status = response.data.status;

      if (status === 'completed' || status === 'failed') {
        window.dispatchEvent(
          new CustomEvent(this.PIPELINE_EVENTS.RUN_COMPLETE, {
            detail: { pipelineId: id, status }
          })
        );
        return this.getPipelineRuns(id, { limit: 1 });
      }

      await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new Error('Pipeline execution timeout');
  }

  async getPipelineDashboard(id: string): Promise<{
    pipeline: Pipeline;
    metrics: PipelineMetrics[];
    runs: PipelineRun[];
    logs: PipelineLogs;
  }> {
    const [pipeline, metrics, runs, logs] = await Promise.all([
      this.getPipeline(id),
      this.getPipelineMetrics(id),
      this.getPipelineRuns(id, { limit: 10 }),
      this.getPipelineLogs(id, { limit: 100 })
    ]);

    return {
      pipeline: pipeline.data,
      metrics: metrics.data,
      runs: runs.data,
      logs: logs.data
    };
  }

  // Event Subscription
  subscribeToEvents(
    event: keyof typeof this.PIPELINE_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.PIPELINE_EVENTS[event], handler);
    return () => window.removeEventListener(this.PIPELINE_EVENTS[event], handler);
  }
}

// Export singleton instance
export const pipelineApi = new PipelineApi();