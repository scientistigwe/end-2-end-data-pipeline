// src/monitoring/api/monitoringApi.ts
import { monitoringClient } from './client';
import { API_CONFIG } from './config';
import type { ApiResponse } from '../../common/types/api';
import type {
  MonitoringConfig,
  MetricsData,
  SystemHealth,
  PerformanceMetrics,
  AlertConfig,
  Alert,
  ResourceUsage,
  TimeSeriesData
} from '../types/monitoring';

export class MonitoringApi {
  static async startMonitoring(
    pipelineId: string, 
    config: MonitoringConfig
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      API_CONFIG.ENDPOINTS.MONITORING.START.replace(':id', pipelineId),
      {},
      config
    );
  }

  static async getMetrics(
    pipelineId: string
  ): Promise<ApiResponse<MetricsData>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.METRICS.replace(':id', pipelineId)
    );
  }

  static async getHealth(
    pipelineId: string
  ): Promise<ApiResponse<SystemHealth>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.HEALTH.replace(':id', pipelineId)
    );
  }

  static async getPerformance(
    pipelineId: string
  ): Promise<ApiResponse<PerformanceMetrics>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.PERFORMANCE.replace(':id', pipelineId)
    );
  }

  static async configureAlerts(
    pipelineId: string,
    config: AlertConfig
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG.replace(':id', pipelineId),
      {},
      config
    );
  }

  static async getAlertHistory(
    pipelineId: string,
    params?: {
      startDate?: string;
      endDate?: string;
      severity?: string[];
      limit?: number;
    }
  ): Promise<ApiResponse<Alert[]>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY.replace(':id', pipelineId),
      { params }
    );
  }

  static async getResourceUsage(
    pipelineId: string,
    params?: {
      interval?: string;
      duration?: string;
    }
  ): Promise<ApiResponse<ResourceUsage>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.RESOURCES.replace(':id', pipelineId),
      { params }
    );
  }

  static async getTimeSeries(
    pipelineId: string,
    params: {
      metrics: string[];
      startTime: string;
      endTime: string;
      interval?: string;
    }
  ): Promise<ApiResponse<TimeSeriesData>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.TIME_SERIES.replace(':id', pipelineId),
      { params }
    );
  }

  static async getAggregatedMetrics(
    pipelineId: string,
    params?: {
      metrics?: string[];
      aggregation?: 'avg' | 'sum' | 'min' | 'max';
      period?: string;
    }
  ): Promise<ApiResponse<MetricsData>> {
    return monitoringClient.request(
      'get',
      API_CONFIG.ENDPOINTS.MONITORING.AGGREGATED.replace(':id', pipelineId),
      { params }
    );
  }

  static async acknowledgeAlert(
    pipelineId: string,
    alertId: string
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY.replace(':id', pipelineId)}/${alertId}/acknowledge`
    );
  }

  static async resolveAlert(
    pipelineId: string,
    alertId: string,
    resolution?: {
      comment?: string;
      action?: string;
    }
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY.replace(':id', pipelineId)}/${alertId}/resolve`,
      {},
      resolution
    );
  }

  static async updateAlertConfig(
    pipelineId: string,
    alertId: string,
    updates: Partial<AlertConfig>
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'put',
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG.replace(':id', pipelineId)}/${alertId}`,
      {},
      updates
    );
  }

  static async deleteAlertConfig(
    pipelineId: string,
    alertId: string
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'delete',
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG.replace(':id', pipelineId)}/${alertId}`
    );
  }

  static async getMetricDefinitions(
    pipelineId: string
  ): Promise<ApiResponse<Array<{
    name: string;
    type: string;
    description: string;
    unit?: string;
    availableAggregations?: string[];
  }>>> {
    return monitoringClient.request(
      'get',
      `${API_CONFIG.ENDPOINTS.MONITORING.METRICS.replace(':id', pipelineId)}/definitions`
    );
  }

  static async pauseMonitoring(
    pipelineId: string
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      `${API_CONFIG.ENDPOINTS.MONITORING.START.replace(':id', pipelineId)}/pause`
    );
  }

  static async resumeMonitoring(
    pipelineId: string
  ): Promise<ApiResponse<void>> {
    return monitoringClient.request(
      'post',
      `${API_CONFIG.ENDPOINTS.MONITORING.START.replace(':id', pipelineId)}/resume`
    );
  }
}

export default MonitoringApi;