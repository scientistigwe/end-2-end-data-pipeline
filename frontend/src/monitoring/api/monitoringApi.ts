import { baseAxiosClient } from '@/common/api/client/baseClient';
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
} from '../types/monitoring';

class MonitoringApi {
  private client = baseAxiosClient;
  private metricsSocket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly MAX_RECONNECT_ATTEMPTS = 5;
  private readonly RECONNECT_DELAY = 1000;
  private readonly MONITORING_EVENTS = {
    METRICS_UPDATE: 'monitoring:metricsUpdate',
    ERROR: 'monitoring:error',
    STATUS_CHANGE: 'monitoring:statusChange'
  } as const;

  constructor() {
    this.setupMonitoringHeaders();
    this.setupMonitoringInterceptors();
  }

  private setupMonitoringHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'monitoring'
    });
  }

  // Interceptors
  private setupMonitoringInterceptors() {
    // Add custom interceptor on the axios instance
    const instance = (this.client as any).client;
    if (!instance) return;

    instance.interceptors.request.use(
      (config) => {
        return config;
      }
    );

    instance.interceptors.response.use(
      response => response,
      error => {
        const enhancedError = this.handleMonitoringError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  // Error Handling
  private handleMonitoringError(error: unknown): MonitoringError {
    const baseError: MonitoringError = {
      name: 'MonitoringError',
      message: 'Unknown monitoring error',
      timestamp: new Date().toISOString(),
      component: 'monitoring'
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
      if (errorObj.response?.status === 429) {
        return {
          ...baseError,
          message: 'Monitoring rate limit exceeded. Please try again later.',
          code: 'RATE_LIMIT_EXCEEDED'
        };
      }
      if (errorObj.response?.status === 503) {
        return {
          ...baseError,
          message: 'Monitoring service is temporarily unavailable.',
          code: 'SERVICE_UNAVAILABLE'
        };
      }
    }

    return baseError;
  }

  private handleWebSocketError(event: Event): WebSocketError {
    const baseError: WebSocketError = {
      name: 'WebSocketError',
      message: 'Unknown WebSocket error',
      type: 'websocket'
    };

    if (event instanceof ErrorEvent) {
      return {
        ...baseError,
        message: event.message
      };
    }

    if (event instanceof CloseEvent) {
      return {
        ...baseError,
        message: 'WebSocket connection closed',
        code: event.code,
        wasClean: event.wasClean
      };
    }

    return baseError;
  }

  private notifyError(error: Error): void {
    window.dispatchEvent(
      new CustomEvent(this.MONITORING_EVENTS.ERROR, {
        detail: { error: error.message }
      })
    );
  }

  // Core Monitoring Operations
  async startMonitoring(pipelineId: string, config: MonitoringConfig): Promise<ApiResponse<void>> {
    return this.client.executePost<void>(
      this.client.createRoute('MONITORING', 'START', { id: pipelineId }),
      config
    );
  }

  async getMetrics(pipelineId: string): Promise<ApiResponse<MetricsData>> {
    return this.client.executeGet<MetricsData>(
      this.client.createRoute('MONITORING', 'METRICS', { id: pipelineId })
    );
  }

  async getHealth(pipelineId: string): Promise<ApiResponse<SystemHealth>> {
    return this.client.executeGet<SystemHealth>(
      this.client.createRoute('MONITORING', 'HEALTH', { id: pipelineId })
    );
  }

  async getPerformance(pipelineId: string): Promise<ApiResponse<PerformanceMetrics>> {
    return this.client.executeGet<PerformanceMetrics>(
      this.client.createRoute('MONITORING', 'PERFORMANCE', { id: pipelineId })
    );
  }

  async getResourceUsage(
    pipelineId: string,
    params?: {
      interval?: string;
      duration?: string;
    }
  ): Promise<ApiResponse<ResourceUsage>> {
    return this.client.executeGet<ResourceUsage>(
      this.client.createRoute('MONITORING', 'RESOURCES', { id: pipelineId }),
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
    return this.client.executeGet<TimeSeriesData>(
      this.client.createRoute('MONITORING', 'TIME_SERIES', { id: pipelineId }),
      { params }
    );
  }

  // Alert Operations
  async configureAlerts(pipelineId: string, config: AlertConfig): Promise<ApiResponse<void>> {
    return this.client.executePost<void>(
      this.client.createRoute('MONITORING', 'ALERTS_CONFIG', { id: pipelineId }),
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
    return this.client.executeGet<Alert[]>(
      this.client.createRoute('MONITORING', 'ALERTS_HISTORY', { id: pipelineId }),
      { params }
    );
  }

  // WebSocket Management
  startRealtimeMonitoring(
    pipelineId: string,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): () => void {
    const wsUrl = `${import.meta.env.VITE_WS_URL}/monitoring/${pipelineId}`;
    
    const connect = () => {
      this.metricsSocket = new WebSocket(wsUrl);
      this.setupWebSocketHandlers(pipelineId, onMetrics, onError);
    };

    connect();
    return () => this.stopRealtimeMonitoring();
  }

  private setupWebSocketHandlers(
    pipelineId: string,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): void {
    if (!this.metricsSocket) return;

    this.metricsSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as MetricsData;
        onMetrics(data);
        this.dispatchMetricsUpdate(data);
      } catch (error) {
        const parsedError = this.handleMonitoringError(error);
        onError?.(parsedError);
        this.notifyError(parsedError);
      }
    };

    this.metricsSocket.onerror = (event) => {
      const error = this.handleWebSocketError(event);
      onError?.(error);
      this.handleWebSocketReconnect(pipelineId, onMetrics, onError);
    };

    this.metricsSocket.onclose = (event) => {
      const error = this.handleWebSocketError(event);
      onError?.(error);
      this.handleWebSocketReconnect(pipelineId, onMetrics, onError);
    };
  }

  private handleWebSocketReconnect(
    pipelineId: string,
    onMetrics: (data: MetricsData) => void,
    onError?: (error: Error) => void
  ): void {
    if (this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      const delay = this.RECONNECT_DELAY * this.reconnectAttempts;

      setTimeout(() => {
        this.startRealtimeMonitoring(pipelineId, onMetrics, onError);
      }, delay);
      
      this.notifyError(new Error(`Reconnecting... Attempt ${this.reconnectAttempts}`));
    } else {
      const error = new Error('Max reconnection attempts reached');
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

  // Event Subscription
  subscribeToMonitoringEvents(
    event: keyof typeof this.MONITORING_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.MONITORING_EVENTS[event], handler);
    return () => window.removeEventListener(this.MONITORING_EVENTS[event], handler);
  }
}

export const monitoringApi = new MonitoringApi();