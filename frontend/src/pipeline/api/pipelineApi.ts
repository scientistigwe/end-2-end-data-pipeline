import type {
  AxiosResponse,
  InternalAxiosRequestConfig 
} from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
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
} from '../types';

export const PIPELINE_EVENTS = {
  STATUS_CHANGE: 'pipeline:statusChange',
  RUN_COMPLETE: 'pipeline:runComplete',
  ERROR: 'pipeline:error'
} as const;

class PipelineApi {
  private client = baseAxiosClient;

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.PIPELINE,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    });
  }

  // Pipeline CRUD Operations
  async listPipelines(params?: {
    page?: number;
    limit?: number;
    status?: PipelineStatus[];
    mode?: string[];
  }): Promise<ApiResponse<Pipeline[]>> {
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'LIST'),
      { params }
    );
  }

  async createPipeline(config: PipelineConfig): Promise<ApiResponse<Pipeline>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'CREATE'),
      config
    );
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'GET', { pipeline_id: id })
    );
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<Pipeline>> {
    return this.client.executePut(
      this.client.createRoute('PIPELINES', 'UPDATE', { pipeline_id: id }),
      updates
    );
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      this.client.createRoute('PIPELINES', 'DELETE', { pipeline_id: id })
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
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'START', { pipeline_id: id }),
      options
    );
  }

  async stopPipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'STOP', { pipeline_id: id })
    );
  }

  async pausePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'PAUSE', { pipeline_id: id })
    );
  }

  async resumePipeline(id: string): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'RESUME', { pipeline_id: id })
    );
  }

  async retryPipeline(id: string): Promise<ApiResponse<PipelineRun>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'RETRY', { pipeline_id: id })
    );
  }

  // Pipeline Status and Monitoring
  async getPipelineStatus(id: string): Promise<ApiResponse<{
    status: PipelineStatus;
    progress: number;
    currentStep?: string;
  }>> {
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'STATUS', { pipeline_id: id })
    );
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
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'LOGS', { pipeline_id: id }),
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
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'METRICS', { pipeline_id: id }),
      { params: timeRange }
    );
  }

  async getPipelineRuns(
    id: string,
    options?: {
      limit?: number;
      page?: number;
      status?: PipelineStatus;
    }
  ): Promise<ApiResponse<PipelineRun[]>> {
    return this.client.executeGet(
      this.client.createRoute('PIPELINES', 'RUNS', { pipeline_id: id }),
      { params: options }
    );
  }

  // Validation
  async validatePipelineConfig(config: PipelineConfig): Promise<ApiResponse<{
    valid: boolean;
    errors?: string[];
  }>> {
    return this.client.executePost(
      this.client.createRoute('PIPELINES', 'VALIDATE'),
      config
    );
  }

  // Event Methods
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

export const pipelineApi = new PipelineApi();