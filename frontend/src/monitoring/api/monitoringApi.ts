// src/services/api/monitoringApi.ts
import { BaseApiClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../common/types/api';
import type {
  MonitoringConfig,
  MetricsData,
  SystemHealth,
  PerformanceMetrics,
  AlertConfig,
  Alert,
  ResourceUsage,
  TimeSeriesData
} from '../monitoring/types/monitoring';

class MonitoringApi extends BaseApiClient {
  async startMonitoring(
    pipelineId: string, 
    config: MonitoringConfig
  ): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.MONITORING.START,
      {
        routeParams: { id: pipelineId }
      },
      config
    );
  }

  async getMetrics(
    pipelineId: string
  ): Promise<ApiResponse<MetricsData>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.METRICS,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async getHealth(
    pipelineId: string
  ): Promise<ApiResponse<SystemHealth>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.HEALTH,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async getPerformance(
    pipelineId: string
  ): Promise<ApiResponse<PerformanceMetrics>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.PERFORMANCE,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async configureAlerts(
    pipelineId: string,
    config: AlertConfig
  ): Promise<ApiResponse<void>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG,
      {
        routeParams: { id: pipelineId }
      },
      config
    );
  }

  async getAlertHistory(
    pipelineId: string
  ): Promise<ApiResponse<Alert[]>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async getResourceUsage(
    pipelineId: string
  ): Promise<ApiResponse<ResourceUsage>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.RESOURCES,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async getTimeSeries(
    pipelineId: string
  ): Promise<ApiResponse<TimeSeriesData>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.TIME_SERIES,
      {
        routeParams: { id: pipelineId }
      }
    );
  }

  async getAggregatedMetrics(
    pipelineId: string
  ): Promise<ApiResponse<MetricsData>> {
    return this.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.AGGREGATED,
      {
        routeParams: { id: pipelineId }
      }
    );
  }
}

export const monitoringApi = new MonitoringApi();

