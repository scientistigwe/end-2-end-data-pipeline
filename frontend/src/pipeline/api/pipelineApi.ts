// src/pipeline/api/pipelineApi.ts
import { AxiosHeaders } from 'axios';
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import { RouteHelper, RouteKey } from '@/common/api/routes';
import type { ApiResponse } from '@/common/types/api';
import type {
  Pipeline,
  PipelineConfig,
  PipelineRun,
  PipelineLogs,
  PipelineMetrics,
  PipelineError,
  PipelineEventMap,
  PipelineEventName,
  PipelineStatus,
  PipelineStatusChangeDetail,
  PipelineRunCompleteDetail,
  PipelineErrorDetail
} from '../types/pipeline';
import { PIPELINE_EVENTS } from '../constants/events';

class PipelineApi extends BaseClient {
  private readonly PIPELINE_EVENTS = PIPELINE_EVENTS;
  private readonly MODULE: RouteKey = 'PIPELINES';

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
  private setupPipelineInterceptors(): void {
    this.client.interceptors.request.use(
      (config) => {
        const headers = new AxiosHeaders(config.headers || {});
        headers.set('X-Pipeline-Timestamp', new Date().toISOString());
        config.headers = headers;
        return config;
      },
      (error) => Promise.reject(error)
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

  private handlePipelineError(error: unknown): PipelineError {
    const baseError: PipelineError = {
      name: 'PipelineError',
      message: 'Unknown pipeline error',
      timestamp: new Date().toISOString(),
      component: 'pipeline'
    };

    if (error instanceof Error) {
      return {
        ...baseError,
        ...error,
        message: error.message
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      const status = errorObj.response?.status;

      switch (status) {
        case 409:
          return {
            ...baseError,
            message: 'Pipeline is already running',
            code: 'PIPELINE_RUNNING'
          };
        case 404:
          return {
            ...baseError,
            message: 'Pipeline not found',
            code: 'PIPELINE_NOT_FOUND'
          };
        case 400:
          return {
            ...baseError,
            message: `Invalid pipeline configuration: ${errorObj.response.data?.message}`,
            code: 'INVALID_CONFIG'
          };
        default:
          return {
            ...baseError,
            message: errorObj.response?.data?.message || errorObj.message || baseError.message,
            code: errorObj.code || 'UNKNOWN_ERROR'
          };
      }
    }

    return baseError;
  }

  // Event Notification Methods
  private notifyError(error: PipelineError): void {
    window.dispatchEvent(
      new CustomEvent<PipelineErrorDetail>(this.PIPELINE_EVENTS.ERROR, {
        detail: {
          error: error.message,
          code: error.code
        }
      })
    );
  }

  private notifyStatusChange(
    pipelineId: string,
    status: PipelineStatus,
    previousStatus: PipelineStatus
  ): void {
    window.dispatchEvent(
      new CustomEvent<PipelineStatusChangeDetail>(this.PIPELINE_EVENTS.STATUS_CHANGE, {
        detail: {
          pipelineId,
          status,
          previousStatus
        }
      })
    );
  }

  private notifyRunComplete(pipelineId: string, status: PipelineStatus): void {
    window.dispatchEvent(
      new CustomEvent<PipelineRunCompleteDetail>(this.PIPELINE_EVENTS.RUN_COMPLETE, {
        detail: {
          pipelineId,
          status
        }
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
    return this.get(
      RouteHelper.getRoute(this.MODULE, 'LIST'),
      { params }
    );
  }

  async createPipeline(config: PipelineConfig): Promise<ApiResponse<Pipeline>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'CREATE'),
      config
    );
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.get(
      RouteHelper.getRoute(this.MODULE, 'GET', { pipeline_id: id })
    );
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<Pipeline>> {
    return this.put(
      RouteHelper.getRoute(this.MODULE, 'UPDATE', { pipeline_id: id }),
      updates
    );
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    return this.delete(
      RouteHelper.getRoute(this.MODULE, 'DELETE', { pipeline_id: id })
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
      RouteHelper.getRoute(this.MODULE, 'START', { pipeline_id: id }),
      options
    );
  }

  async stopPipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'STOP', { pipeline_id: id })
    );
  }

  async pausePipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'PAUSE', { pipeline_id: id })
    );
  }

  async resumePipeline(id: string): Promise<ApiResponse<void>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'RESUME', { pipeline_id: id })
    );
  }

  async retryPipeline(id: string): Promise<ApiResponse<PipelineRun>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'RETRY', { pipeline_id: id })
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
      RouteHelper.getRoute(this.MODULE, 'LOGS', { pipeline_id: id }),
      { params: options }
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
      RouteHelper.getRoute(this.MODULE, 'METRICS', { pipeline_id: id }),
      { params: timeRange }
    );
  }

  async getPipelineRuns(
    id: string,
    options?: {
      limit?: number;
      page?: number;
      status?: string;
    }
  ): Promise<ApiResponse<PipelineRun[]>> {
    return this.get(
      RouteHelper.getRoute(this.MODULE, 'RUNS'),
      { params: { ...options, pipeline_id: id } }
    );
  }

  // Validation
  async validatePipelineConfig(config: PipelineConfig): Promise<ApiResponse<{
    valid: boolean;
    errors?: string[];
  }>> {
    return this.post(
      RouteHelper.getRoute(this.MODULE, 'VALIDATE'),
      config
    );
  }

  // Helper Methods
  private async checkCompletion(
    id: string,
    startTime: number,
    interval: number,
    timeout: number
  ): Promise<ApiResponse<PipelineRun>> {
    if (Date.now() - startTime >= timeout) {
      throw this.handlePipelineError({
        message: 'Pipeline execution timeout',
        code: 'EXECUTION_TIMEOUT'
      });
    }

    const response = await this.getPipeline(id);
    const status = response.data.status;

    if (status === 'completed' || status === 'failed') {
      this.notifyRunComplete(id, status);
      const runsResponse = await this.getPipelineRuns(id, { limit: 1 });
      return {
        ...runsResponse,
        data: runsResponse.data[0]
      };
    }

    await new Promise(resolve => setTimeout(resolve, interval));
    return this.checkCompletion(id, startTime, interval, timeout);
  }

  async waitForPipelineCompletion(
    id: string,
    options?: {
      pollingInterval?: number;
      timeout?: number;
    }
  ): Promise<ApiResponse<PipelineRun>> {
    const interval = options?.pollingInterval || 5000;
    const timeout = options?.timeout || 300000; // 5 minutes default
    return this.checkCompletion(id, Date.now(), interval, timeout);
  }

  async getPipelineDashboard(id: string) {
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
  subscribeToEvents<E extends PipelineEventName>(
    event: E,
    callback: (event: PipelineEventMap[E]) => void
  ): () => void {
    const handler = (e: Event) => callback(e as PipelineEventMap[E]);
    window.addEventListener(event, handler);
    return () => window.removeEventListener(event, handler);
  }
}

export const pipelineApi = new PipelineApi();