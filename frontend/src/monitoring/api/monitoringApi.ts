// src/monitoring/api/monitoringApi.ts
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
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
  WebSocketError,
  MonitoringError
} from '../types';

interface WebSocketHandlers {
  onMetrics: (data: MetricsData) => void;
  onError?: (error: Error) => void;
}

class MonitoringApi {
  private client = baseAxiosClient;
  private metricsSocket: WebSocket | null = null;
  private reconnectAttempts = 0;

  private static readonly MAX_RECONNECT_ATTEMPTS = 5;
  private static readonly RECONNECT_DELAY = 1000;
  private static readonly MONITORING_EVENTS = {
    METRICS_UPDATE: 'monitoring:metricsUpdate',
    ERROR: 'monitoring:error',
    STATUS_CHANGE: 'monitoring:statusChange'
  } as const;

  constructor() {
    this.client.setServiceConfig({
      service: ServiceType.MONITORING
    });
  }

  // Core Monitoring Operations
  async startMonitoring(pipelineId: string, config: MonitoringConfig): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createRoute('MONITORING', 'START', { pipeline_id: pipelineId }),
      config
    );
  }

  async getMetrics(pipelineId: string): Promise<ApiResponse<MetricsData>> {
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'METRICS', { pipeline_id: pipelineId })
    );
  }

  async getAggregatedMetrics(pipelineId: string): Promise<ApiResponse<MetricsData>> {
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'AGGREGATED', { pipeline_id: pipelineId })
    );
  }

  async getHealth(pipelineId: string): Promise<ApiResponse<SystemHealth>> {
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'HEALTH', { pipeline_id: pipelineId })
    );
  }

  async getPerformance(pipelineId: string): Promise<ApiResponse<PerformanceMetrics>> {
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'PERFORMANCE', { pipeline_id: pipelineId })
    );
  }

  // Resource Operations
  async getResourceUsage(
    pipelineId: string,
    params?: {
      interval?: string;
      duration?: string;
    }
  ): Promise<ApiResponse<ResourceUsage>> {
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'RESOURCES', { pipeline_id: pipelineId }),
      { params }
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
    return this.client.executeGet(
      this.client.createRoute('MONITORING', 'TIME_SERIES', { pipeline_id: pipelineId }),
      { params }
    );
  }

  // Alert Operations
  async configureAlerts(pipelineId: string, config: AlertConfig): Promise<ApiResponse<void>> {
    return this.client.executePost(
      this.client.createNestedRoute('MONITORING', 'ALERTS', 'CONFIG', { pipeline_id: pipelineId }),
      config
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
    return this.client.executeGet(
      this.client.createNestedRoute('MONITORING', 'ALERTS', 'HISTORY', { pipeline_id: pipelineId }),
      { params }
    );
  }

  // WebSocket Management
  startRealtimeMonitoring(pipelineId: string, handlers: WebSocketHandlers): () => void {
    const wsUrl = `${import.meta.env.VITE_WS_URL}/monitoring/${pipelineId}`;
    this.initializeWebSocket(wsUrl, handlers);
    return () => this.stopRealtimeMonitoring();
  }

  stopRealtimeMonitoring(): void {
    if (this.metricsSocket) {
      this.metricsSocket.close();
      this.metricsSocket = null;
    }
    this.reconnectAttempts = 0;
  }

  // Event Subscription
  subscribeToMonitoringEvents(
    event: keyof typeof MonitoringApi.MONITORING_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(MonitoringApi.MONITORING_EVENTS[event], handler);
    return () => window.removeEventListener(MonitoringApi.MONITORING_EVENTS[event], handler);
  }

  // Dashboard Operations
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

  // Private WebSocket Methods
  private initializeWebSocket(wsUrl: string, handlers: WebSocketHandlers): void {
    this.metricsSocket = new WebSocket(wsUrl);
    this.setupWebSocketHandlers(handlers);
  }

  private setupWebSocketHandlers(handlers: WebSocketHandlers): void {
    if (!this.metricsSocket) return;

    this.metricsSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as MetricsData;
        handlers.onMetrics(data);
        this.dispatchMetricsUpdate(data);
      } catch (error) {
        handlers.onError?.(new Error('Failed to parse metrics data'));
      }
    };

    this.metricsSocket.onerror = () => {
      this.handleWebSocketError(handlers);
    };

    this.metricsSocket.onclose = () => {
      this.handleWebSocketReconnect(handlers);
    };
  }

  private handleWebSocketError(handlers: WebSocketHandlers): void {
    const error = new Error('WebSocket connection error');
    handlers.onError?.(error);
    window.dispatchEvent(
      new CustomEvent(MonitoringApi.MONITORING_EVENTS.ERROR, {
        detail: { error: error.message }
      })
    );
  }

  private handleWebSocketReconnect(handlers: WebSocketHandlers): void {
    if (this.reconnectAttempts < MonitoringApi.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      const delay = MonitoringApi.RECONNECT_DELAY * this.reconnectAttempts;

      setTimeout(() => {
        if (this.metricsSocket) {
          this.setupWebSocketHandlers(handlers);
        }
      }, delay);
    } else {
      const error = new Error('Max reconnection attempts reached');
      handlers.onError?.(error);
      window.dispatchEvent(
        new CustomEvent(MonitoringApi.MONITORING_EVENTS.ERROR, {
          detail: { error: error.message }
        })
      );
    }
  }

  private dispatchMetricsUpdate(data: MetricsData): void {
    window.dispatchEvent(
      new CustomEvent(MonitoringApi.MONITORING_EVENTS.METRICS_UPDATE, {
        detail: { metrics: data }
      })
    );
  }
}

export const monitoringApi = new MonitoringApi();