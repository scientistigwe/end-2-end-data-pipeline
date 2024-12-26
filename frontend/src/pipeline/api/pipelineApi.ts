import {   AxiosHeaders } from 'axios';
import type {
  AxiosResponse,
  InternalAxiosRequestConfig 
} from 'axios';
import { baseAxiosClient } from '@/common/api/client/baseClient';
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
  PipelineErrorDetail,
  RouteDefinition
} from '../types';

export const PIPELINE_EVENTS = {
  STATUS_CHANGE: 'pipeline:statusChange',
  RUN_COMPLETE: 'pipeline:runComplete',
  ERROR: 'pipeline:error'
} as const;

class PipelineApi {
  private client = baseAxiosClient;
  private readonly MODULE: keyof RouteDefinition = 'PIPELINES';
  private readonly API_VERSION = 'v1';
  private readonly BASE_PATH = `/api/${this.API_VERSION}/pipelines`;

  constructor() {
    this.setupPipelineHeaders();
    this.setupPipelineInterceptors();
  }

  private setupPipelineHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'pipeline'
    });
  }

  // Interceptors and Error Handling
// src/pipeline/api/pipelineApi.ts
private setupPipelineInterceptors(): void {
  const instance = this.client.getAxiosInstance();
  if (!instance) return;

  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const headers = new AxiosHeaders(config.headers || {});
      config.headers = headers;
      return config;
    },
    (error: unknown) => Promise.reject(this.handlePipelineError(error))
  );

  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: unknown) => {
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
        message: error.message,
        stack: error.stack,
        name: 'PipelineError'
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

  // Pipeline CRUD Operations aligned with backend routes
  async listPipelines(params?: {
    page?: number;
    limit?: number;
    status?: PipelineStatus[];
    mode?: string[];
  }): Promise<ApiResponse<Pipeline[]>> {
    return this.client.executeGet(this.BASE_PATH, { params });
  }

  async createPipeline(config: PipelineConfig): Promise<ApiResponse<Pipeline>> {
    return this.client.executePost(this.BASE_PATH, config);
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.client.executeGet(`${this.BASE_PATH}/${id}`);
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<Pipeline>> {
    return this.client.executePut(`${this.BASE_PATH}/${id}`, updates);
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(`${this.BASE_PATH}/${id}`);
  }

  // Pipeline Execution Controls
  async startPipeline(
    id: string,
    options?: { 
      mode?: string; 
      params?: Record<string, unknown>
    }
  ): Promise<ApiResponse<PipelineRun>> {
    return this.client.executePost(`${this.BASE_PATH}/${id}/start`, options);
  }

  async stopPipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(`${this.BASE_PATH}/${id}/stop`);
  }

  async pausePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(`${this.BASE_PATH}/${id}/pause`);
  }

  async resumePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(`${this.BASE_PATH}/${id}/resume`);
  }

  async retryPipeline(id: string): Promise<ApiResponse<PipelineRun>> {
    return this.client.executePost(`${this.BASE_PATH}/${id}/retry`);
  }

  // Pipeline Status and Monitoring
  async getPipelineStatus(id: string): Promise<ApiResponse<{
    status: PipelineStatus;
    progress: number;
    currentStep?: string;
  }>> {
    return this.client.executeGet(`${this.BASE_PATH}/${id}/status`);
  }

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
    return this.client.executeGet(`${this.BASE_PATH}/${id}/logs`, { params: options });
  }

  async getPipelineMetrics(
    id: string,
    timeRange?: {
      start: string;
      end: string;
    }
  ): Promise<ApiResponse<PipelineMetrics[]>> {
    return this.client.executeGet(`${this.BASE_PATH}/${id}/metrics`, { params: timeRange });
  }

  async getPipelineRuns(
    id: string,
    options?: {
      limit?: number;
      page?: number;
      status?: PipelineStatus;
    }
  ): Promise<ApiResponse<PipelineRun[]>> {
    return this.client.executeGet(`${this.BASE_PATH}/${id}/runs`, { params: options });
  }

  // Validation
  async validatePipelineConfig(config: PipelineConfig): Promise<ApiResponse<{
    valid: boolean;
    errors?: string[];
  }>> {
    return this.client.executePost(`${this.BASE_PATH}/validate`, config);
  }

  // Event Notification Methods
  private notifyError(error: PipelineError): void {
    window.dispatchEvent(
      new CustomEvent<PipelineErrorDetail>(PIPELINE_EVENTS.ERROR, {
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
      new CustomEvent<PipelineStatusChangeDetail>(PIPELINE_EVENTS.STATUS_CHANGE, {
        detail: {
          pipelineId,
          status,
          previousStatus,
          timestamp: new Date().toISOString()
        }
      })
    );
  }

  private notifyRunComplete(pipelineId: string, status: PipelineStatus): void {
    window.dispatchEvent(
      new CustomEvent<PipelineRunCompleteDetail>(PIPELINE_EVENTS.RUN_COMPLETE, {
        detail: {
          pipelineId,
          status,
          timestamp: new Date().toISOString()
        }
      })
    );
  }

  // Event Subscription with type safety
  subscribeToEvents<E extends PipelineEventName>(
    event: E,
    callback: (event: PipelineEventMap[E]) => void
  ): () => void {
    const handler = (e: Event) => callback(e as PipelineEventMap[E]);
    window.addEventListener(event, handler);
    return () => window.removeEventListener(event, handler);
  }

  // Helper Methods
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
}

// Export singleton instance
export const pipelineApi = new PipelineApi();