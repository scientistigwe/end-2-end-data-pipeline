// src/monitoring/api/monitoringApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient } from '@/common/api/client/baseClient';
import { 
  ApiResponse,
  HTTP_STATUS,
  ERROR_CODES 
} from '@/common/types/api';
import type { AxiosResponse, InternalAxiosRequestConfig  } from 'axios';
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
    this.setupMonitoringHeaders();
    this.setupMonitoringInterceptors();
  }

  private setupMonitoringHeaders = (): void => {
    this.client.setDefaultHeaders({
      'X-Service': 'monitoring'
    });
  };

  private setupMonitoringInterceptors = (): void => {
    const instance = this.client.getAxiosInstance();
    if (!instance) return;

    instance.interceptors.request.use(
      this.handleRequestInterceptor,
      this.handleRequestError
    );

    instance.interceptors.response.use(
      this.handleResponseInterceptor,
      this.handleResponseError
    );
  };

  private handleRequestInterceptor = (
    config: InternalAxiosRequestConfig
  ): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig> => {
    return config;
  };

  private handleRequestError = (error: unknown): Promise<never> => {
    return Promise.reject(this.handleMonitoringError(error));
  };

  private handleResponseInterceptor = (
    response: AxiosResponse
  ): AxiosResponse | Promise<AxiosResponse> => {
    return response;
  };

  private handleResponseError = (error: unknown): Promise<never> => {
    const enhancedError = this.handleMonitoringError(error);
    this.notifyError(enhancedError);
    throw enhancedError;
  };
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
      if (errorObj.response?.status === HTTP_STATUS.TOO_MANY_REQUESTS) {
        return {
          ...baseError,
          message: 'Monitoring rate limit exceeded. Please try again later.',
          code: ERROR_CODES.RATE_LIMIT_EXCEEDED
        };
      }
      if (errorObj.response?.status === HTTP_STATUS.SERVICE_UNAVAILABLE) {
        return {
          ...baseError,
          message: 'Monitoring service is temporarily unavailable.',
          code: ERROR_CODES.SERVICE_UNAVAILABLE
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
      new CustomEvent(MonitoringApi.MONITORING_EVENTS.ERROR, {
        detail: { error: error.message }
      })
    );
  }

  // Core Monitoring Operations
  async startMonitoring(pipelineId: string, config: MonitoringConfig): Promise<ApiResponse<void>> {
    return this.client.executePost(
      RouteHelper.getRoute('MONITORING', 'START', { pipeline_id: pipelineId }),
      config
    );
  }

  async getMetrics(pipelineId: string): Promise<ApiResponse<MetricsData>> {
    return this.client.executeGet(
      RouteHelper.getRoute('MONITORING', 'METRICS', { pipeline_id: pipelineId })
    );
  }

  async getHealth(pipelineId: string): Promise<ApiResponse<SystemHealth>> {
    return this.client.executeGet(
      RouteHelper.getRoute('MONITORING', 'HEALTH', { pipeline_id: pipelineId })
    );
  }

  async getPerformance(pipelineId: string): Promise<ApiResponse<PerformanceMetrics>> {
    return this.client.executeGet(
      RouteHelper.getRoute('MONITORING', 'PERFORMANCE', { pipeline_id: pipelineId })
    );
  }

  async getResourceUsage(
    pipelineId: string,
    params?: {
      interval?: string;
      duration?: string;
    }
  ): Promise<ApiResponse<ResourceUsage>> {
    return this.client.executeGet(
      RouteHelper.getRoute('MONITORING', 'RESOURCES', { pipeline_id: pipelineId }),
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
      RouteHelper.getRoute('MONITORING', 'TIME_SERIES', { pipeline_id: pipelineId }),
      { params }
    );
  }

  // Alert Operations
  async configureAlerts(pipelineId: string, config: AlertConfig): Promise<ApiResponse<void>> {
    return this.client.executePost(
      RouteHelper.getRoute('MONITORING', 'ALERTS_CONFIG', { pipeline_id: pipelineId }),
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
      RouteHelper.getRoute('MONITORING', 'ALERTS_HISTORY', { pipeline_id: pipelineId }),
      { params }
    );
  }

  // WebSocket Management
  startRealtimeMonitoring(
    pipelineId: string,
    handlers: WebSocketHandlers
  ): () => void {
    const wsUrl = `${import.meta.env.VITE_WS_URL}/monitoring/${pipelineId}`;
    this.initializeWebSocket(wsUrl, handlers);
    return () => this.stopRealtimeMonitoring();
  }

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
        const parsedError = this.handleMonitoringError(error);
        handlers.onError?.(parsedError);
        this.notifyError(parsedError);
      }
    };

    this.metricsSocket.onerror = (event) => {
      const error = this.handleWebSocketError(event);
      handlers.onError?.(error);
      this.handleWebSocketReconnect(handlers);
    };

    this.metricsSocket.onclose = (event) => {
      const error = this.handleWebSocketError(event);
      handlers.onError?.(error);
      this.handleWebSocketReconnect(handlers);
    };
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
      
      this.notifyError(new Error(`Reconnecting... Attempt ${this.reconnectAttempts}`));
    } else {
      const error = new Error('Max reconnection attempts reached');
      handlers.onError?.(error);
      this.notifyError(error);
    }
  }

  private dispatchMetricsUpdate(data: MetricsData): void {
    window.dispatchEvent(
      new CustomEvent(MonitoringApi.MONITORING_EVENTS.METRICS_UPDATE, {
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
    event: keyof typeof MonitoringApi.MONITORING_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(MonitoringApi.MONITORING_EVENTS[event], handler);
    return () => window.removeEventListener(MonitoringApi.MONITORING_EVENTS[event], handler);
  }
}

export const monitoringApi = new MonitoringApi();