// src/services/api/pipelineApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../common/types/api';
import type {
  Pipeline,
  PipelineConfig,
  PipelineRun,
  PipelineLogs,
  PipelineMetrics,
  PipelineSchedule,
  PipelineEvent,
  PipelineFilters
} from '../pipeline/types/pipeline';

class PipelineApi extends BaseApiClient {
  /**
   * Pipeline CRUD Operations
   */
  async listPipelines(filters?: PipelineFilters): Promise<ApiResponse<Pipeline[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.PIPELINES.LIST, {
      params: filters
    });
  }

  async createPipeline(config: PipelineConfig): Promise<ApiResponse<Pipeline>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.PIPELINES.CREATE,
      {},
      config
    );
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.request('get', API_CONFIG.ENDPOINTS.PIPELINES.GET, {
      routeParams: { id }
    });
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<Pipeline>> {
    return this.request(
      'put',
      API_CONFIG.ENDPOINTS.PIPELINES.UPDATE,
      {
        routeParams: { id }
      },
      updates
    );
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    return this.request('delete', API_CONFIG.ENDPOINTS.PIPELINES.DELETE, {
      routeParams: { id }
    });
  }

  /**
   * Pipeline Execution Operations
   */
  async startPipeline(
    id: string,
    options?: {
      mode?: string;
      params?: Record<string, unknown>;
    }
  ): Promise<ApiResponse<PipelineRun>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.PIPELINES.START,
      {
        routeParams: { id }
      },
      options
    );
  }

  async stopPipeline(id: string): Promise<ApiResponse<void>> {
    return this.request('post', API_CONFIG.ENDPOINTS.PIPELINES.STOP, {
      routeParams: { id }
    });
  }

  async getPipelineStatus(id: string): Promise<ApiResponse<{
    status: string;
    currentStep?: string;
    progress?: number;
    error?: string;
  }>> {
    return this.request('get', API_CONFIG.ENDPOINTS.PIPELINES.STATUS, {
      routeParams: { id }
    });
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
    return this.request('get', API_CONFIG.ENDPOINTS.PIPELINES.LOGS, {
      routeParams: { id },
      params: options
    });
  }

  /**
   * Pipeline Runs and History
   */
  async getPipelineRuns(
    id: string,
    options?: {
      limit?: number;
      page?: number;
      status?: string;
    }
  ): Promise<ApiResponse<PipelineRun[]>> {
    return this.request('get', `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/runs`, {
      routeParams: { id },
      params: options
    });
  }

  async getPipelineRun(
    pipelineId: string,
    runId: string
  ): Promise<ApiResponse<PipelineRun>> {
    return this.request(
      'get',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/runs/${runId}`,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async retryPipelineRun(
    pipelineId: string,
    runId: string
  ): Promise<ApiResponse<PipelineRun>> {
    return this.request(
      'post',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/runs/${runId}/retry`,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  /**
   * Pipeline Metrics and Monitoring
   */
  async getPipelineMetrics(
    id: string,
    timeRange?: {
      start: string;
      end: string;
    }
  ): Promise<ApiResponse<PipelineMetrics[]>> {
    return this.request(
      'get',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/metrics`,
      {
        routeParams: { id },
        params: timeRange
      }
    );
  }

  /**
   * Pipeline Schedules
   */
  async getSchedules(
    pipelineId: string
  ): Promise<ApiResponse<PipelineSchedule[]>> {
    return this.request(
      'get',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/schedules`,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async updateSchedule(
    pipelineId: string,
    scheduleId: string,
    updates: Partial<PipelineSchedule>
  ): Promise<ApiResponse<PipelineSchedule>> {
    return this.request(
      'put',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/schedules/${scheduleId}`,
      {
        routeParams: { id: pipelineId }
      },
      updates
    );
  }

  /**
   * Pipeline Events
   */
  async getEvents(
    pipelineId: string,
    options?: {
      type?: string;
      processed?: boolean;
      limit?: number;
      page?: number;
    }
  ): Promise<ApiResponse<PipelineEvent[]>> {
    return this.request(
      'get',
      `${API_CONFIG.ENDPOINTS.PIPELINES.GET}/events`,
      {
        routeParams: { id: pipelineId },
        params: options
      }
    );
  }
}

export const pipelineApi = new PipelineApi();