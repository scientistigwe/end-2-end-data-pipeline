// src/monitoring/api/monitoringApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  MonitoringConfig,
  MetricsData,
  SystemHealth,
  PerformanceMetrics,
  AlertConfig,
  Alert,
  ResourceUsage,
  TimeSeriesData,
  MetricDefinition
} from '../types/monitoring';

class MonitoringApi extends BaseClient {
  private metricsSocket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly MAX_RECONNECT_ATTEMPTS = 5;
  private readonly RECONNECT_DELAY = 1000;
  private readonly MONITORING_EVENTS = {
    METRICS_UPDATE: 'monitoring:metricsUpdate',
    ERROR: 'monitoring:error',
    STATUS_CHANGE: 'monitoring:statusChange'
  };

  constructor() {
    super({
      baseURL: import.meta.env.VITE_MONITORING_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'monitoring'
      }
    });

    this.setupMonitoringInterceptors();
  }

  // Interceptors and Error Handling
  private setupMonitoringInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Monitoring-Timestamp', new Date().toISOString());
        return config;
      }
    );

    this.client.interceptors.response.use(
      response => response,
      error => {
        const enhancedError = this.handleMonitoringError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  private handleMonitoringError(error: any): Error {
    if (error.response?.status === 429) {
      return new Error('Monitoring rate limit exceeded. Please try again later.');
    }
    if (error.response?.status === 503) {
      return new Error('Monitoring service is temporarily unavailable.');
    }
    if (error.response?.status === 404) {
      return new Error('Requested monitoring resource not found.');
    }
    if (error.response?.status === 400) {
      return new Error(`Invalid monitoring request: ${error.response.data?.message}`);
    }
    return error;
  }

  // Event Handling
  private notifyError(error: Error): void {
    window.dispatchEvent(
      new CustomEvent(this.MONITORING_EVENTS.ERROR, {
        detail: { error: error.message }
      })
    );
  }

  // Core Monitoring Operations
  async startMonitoring(pipelineId: string, config: MonitoringConfig): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.MONITORING.START,
      config,
      { routeParams: { id: pipelineId } }
    );
  }

  async pauseMonitoring(pipelineId: string): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.MONITORING.START}/pause`,
      null,
      { routeParams: { id: pipelineId } }
    );
  }

  async resumeMonitoring(pipelineId: string): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.MONITORING.START}/resume`,
      null,
      { routeParams: { id: pipelineId } }
    );
  }

  async stopMonitoring(pipelineId: string): Promise<ApiResponse<void>> {
    this.stopRealtimeMonitoring();
    return this.post(
      `${API_CONFIG.ENDPOINTS.MONITORING.START}/stop`,
      null,
      { routeParams: { id: pipelineId } }
    );
  }

  // Metrics Operations
  async getMetrics(pipelineId: string): Promise<ApiResponse<MetricsData>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.METRICS,
      { routeParams: { id: pipelineId } }
    );
  }

  async getMetricDefinitions(pipelineId: string): Promise<ApiResponse<MetricDefinition[]>> {
    return this.get(
      `${API_CONFIG.ENDPOINTS.MONITORING.METRICS}/definitions`,
      { routeParams: { id: pipelineId } }
    );
  }

  async getAggregatedMetrics(
    pipelineId: string,
    params?: {
      metrics?: string[];
      aggregation?: 'avg' | 'sum' | 'min' | 'max';
      period?: string;
    }
  ): Promise<ApiResponse<MetricsData>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.AGGREGATED,
      {
        routeParams: { id: pipelineId },
        params
      }
    );
  }

  // Health & Performance Operations
  async getHealth(pipelineId: string): Promise<ApiResponse<SystemHealth>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.HEALTH,
      { routeParams: { id: pipelineId } }
    );
  }

  async getPerformance(pipelineId: string): Promise<ApiResponse<PerformanceMetrics>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.PERFORMANCE,
      { routeParams: { id: pipelineId } }
    );
  }

  async getResourceUsage(
    pipelineId: string,
    params?: {
      interval?: string;
      duration?: string;
    }
  ): Promise<ApiResponse<ResourceUsage>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.RESOURCES,
      {
        routeParams: { id: pipelineId },
        params
      }
    );
  }

  // Time Series Operations
  async getTimeSeries(
    pipelineId: string,
    params: {
      metrics: string[];
      startTime: string;
      endTime: string;
      interval?: string;
    }
  ): Promise<ApiResponse<TimeSeriesData>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.TIME_SERIES,
      {
        routeParams: { id: pipelineId },
        params
      }
    );
  }

  // Alert Operations
  async configureAlerts(pipelineId: string, config: AlertConfig): Promise<ApiResponse<void>> {
    return this.post(
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG,
      config,
      { routeParams: { id: pipelineId } }
    );
  }

  async getAlertHistory(
    pipelineId: string,
    params?: {
      startDate?: string;
      endDate?: string;
      severity?: string[];
      limit?: number;
    }
  ): Promise<ApiResponse<Alert[]>> {
    return this.get(
      API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY,
      {
        routeParams: { id: pipelineId },
        params
      }
    );
  }

  async acknowledgeAlert(pipelineId: string, alertId: string): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY}/acknowledge`,
      null,
      { routeParams: { id: pipelineId, alertId } }
    );
  }

  async resolveAlert(
    pipelineId: string,
    alertId: string,
    resolution?: {
      comment?: string;
      action?: string;
    }
  ): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_HISTORY}/resolve`,
      resolution,
      { routeParams: { id: pipelineId, alertId } }
    );
  }

  async updateAlertConfig(
    pipelineId: string,
    alertId: string,
    updates: Partial<AlertConfig>
  ): Promise<ApiResponse<void>> {
    return this.put(
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG}/${alertId}`,
      updates,
      { routeParams: { id: pipelineId } }
    );
  }

  async deleteAlertConfig(pipelineId: string, alertId: string): Promise<ApiResponse<void>> {
    return this.delete(
      `${API_CONFIG.ENDPOINTS.MONITORING.ALERTS_CONFIG}/${alertId}`,
      { routeParams: { id: pipelineId } }
    );
  }

  // Real-time Monitoring
  startRealtimeMonitoring(
    pipelineId: string,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): () => void {
    const wsUrl = `${import.meta.env.VITE_WS_URL}/monitoring/${pipelineId}`;
    
    const connect = () => {
      this.metricsSocket = new WebSocket(wsUrl);

      this.metricsSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMetrics(data);
          this.dispatchMetricsUpdate(data);
        } catch (error) {
          const parsedError = new Error('Invalid metrics data received');
          onError?.(parsedError);
          this.notifyError(parsedError);
        }
      };

      this.metricsSocket.onerror = (error) => {
        onError?.(error as Error);
        this.handleWebSocketReconnect(pipelineId, onMetrics, onError);
      };

      this.metricsSocket.onclose = () => {
        this.handleWebSocketReconnect(pipelineId, onMetrics, onError);
      };
    };

    connect();
    return () => this.stopRealtimeMonitoring();
  }

  private handleWebSocketReconnect(
    pipelineId: string,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): void {
    if (this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.startRealtimeMonitoring(pipelineId, onMetrics, onError);
      }, this.RECONNECT_DELAY * this.reconnectAttempts);
    } else {
      const error = new Error('Failed to establish real-time monitoring connection');
      onError?.(error);
      this.notifyError(error);
    }
  }

  private dispatchMetricsUpdate(data: MetricsData): void {
    window.dispatchEvent(
      new CustomEvent(this.MONITORING_EVENTS.METRICS_UPDATE, {
        detail: { metrics: data }
      })
    );
  }

  stopRealtimeMonitoring(): void {
    if (this.metricsSocket) {
      this.metricsSocket.close();
      this.metricsSocket = null;
    }
    this.reconnectAttempts = 0;
  }

  // Helper Methods
  async pollMetrics(
    pipelineId: string,
    interval: number = 5000,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): Promise<() => void> {
    let isPolling = true;

    const poll = async () => {
      while (isPolling) {
        try {
          const response = await this.getMetrics(pipelineId);
          onMetrics(response.data);
          this.dispatchMetricsUpdate(response.data);
          await new Promise(resolve => setTimeout(resolve, interval));
        } catch (error) {
          const enhancedError = this.handleMonitoringError(error);
          onError?.(enhancedError);
          this.notifyError(enhancedError);
          await new Promise(resolve => setTimeout(resolve, interval));
        }
      }
    };

    poll();
    return () => { isPolling = false; };
  }

  async getMonitoringDashboard(pipelineId: string) {
    const [metrics, health, performance, resources, alerts] = await Promise.all([
      this.getMetrics(pipelineId),
      this.getHealth(pipelineId),
      this.getPerformance(pipelineId),
      this.getResourceUsage(pipelineId),
      this.getAlertHistory(pipelineId)
    ]);

    return {
      metrics: metrics.data,
      health: health.data,
      performance: performance.data,
      resources: resources.data,
      alerts: alerts.data
    };
  }

  async batchUpdateAlertConfigs(
    pipelineId: string,
    updates: Array<{ id: string; config: Partial<AlertConfig> }>
  ): Promise<Array<ApiResponse<void>>> {
    const promises = updates.map(update =>
      this.updateAlertConfig(pipelineId, update.id, update.config)
    );
    return Promise.all(promises);
  }

  subscribeToMonitoringEvents(
    event: keyof typeof this.MONITORING_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.MONITORING_EVENTS[event], handler);
    return () => window.removeEventListener(this.MONITORING_EVENTS[event], handler);
  }
}

// Export singleton instance
export const monitoringApi = new MonitoringApi();