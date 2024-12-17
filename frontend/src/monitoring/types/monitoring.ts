// src/monitoring/types/monitoring.ts
export type MetricStatus = 'healthy' | 'warning' | 'critical';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';

export interface MonitoringConfig {
  metrics: string[];
  interval?: number;
  alertThresholds?: Record<string, number>;
  timeRange?: TimeRange;
  retention?: string;
}

export interface MetricsData {
  type: string;
  timestamp: string;
  values: Record<string, number>;
  status: MetricStatus;
  labels?: Record<string, string>;
  metadata?: Record<string, any>;
  pipelines: Record<string, {
    throughput: number;
    latency: number;
    errorRate: number;
    lastUpdated: string;
  }>;
  dataSources: Record<string, {
    availability: number;
    responseTime: number;
    errorCount: number;
    lastChecked: string;
  }>;
}

export interface SystemHealth {
  status: MetricStatus;
  lastChecked: string;
  components: Array<{
    name: string;
    status: MetricStatus;
    message?: string;
    lastChecked?: string;
  }>;
  error?: string;
  lastUpdated: string;
}

export interface PerformanceMetrics {
  cpu: {
    usage: number;
    load: number;
    threads: number;
  };
  memory: {
    used: number;
    available: number;
    peak: number;
  };
  latency: {
    p50: number;
    p90: number;
    p99: number;
  };
  throughput: {
    current: number;
    average: number;
    peak: number;
  };
}

export interface ResourceUsage {
  cpu: {
    used: number;
    total: number;
    percentage: number;
  };
  network: {
    incoming: number;
    outgoing: number;
  };
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  disk: {
    used: number;
    total: number;
    percentage: number;
  };
  timestamp: string;
}

export interface AlertConfig {
  metric: string;
  threshold: number;
  severity: AlertSeverity;
  condition: 'above' | 'below' | 'equals';
  enabled?: boolean;
  description?: string;
  name: string;
  }

export interface Alert {
  id: string;
  timestamp: string;
  metric: string;
  value: number;
  threshold: number;
  severity: AlertSeverity;
  message: string;
  resolved: boolean;
  resolvedAt?: string;
  acknowledged?: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  type: string;
  source?: string;
}

export interface TimeSeriesData {
  series: Array<{
    name: string;
    data: Array<{
      timestamp: string;
      value: number;
    }>;
  }>;
  interval: string;
  startTime: string;
  endTime: string;
}

export interface MonitoringState {
  metrics: MetricsData[] | null;
  systemHealth: SystemHealth | null;
  alerts: Alert[];
  resources: ResourceUsage | null;
  selectedTimeRange: TimeRange;
  filters: MonitoringFilters;
  isLoading: boolean;
  error: Error | null;
}

export interface MonitoringFilters {
  metricTypes?: string[];
  status?: MetricStatus[];
  timeRange?: TimeRange;
  search?: string;
}

export interface Alert {
  id: string;
  configId: string;
  timestamp: string;
  metric: string;
  value: number;
  threshold: number;
  condition: 'above' | 'below' | 'equals';
  severity: AlertSeverity;
  status: 'active' | 'acknowledged' | 'resolved';
  acknowledgedBy?: string;
  resolvedBy?: string;
  resolution?: {
    timestamp: string;
    comment?: string;
    action?: string;
  };
}

export interface MetricDefinition {
  name: string;
  type: 'gauge' | 'counter' | 'histogram';
  unit?: string;
  description?: string;
  labels?: string[];
}

export type MonitoringEventType = 'metrics' | 'error' | 'status';

export interface MonitoringError extends Error {
  code?: string;
  component?: string;
  timestamp?: string;
}

export interface WebSocketError extends Error {
  type: 'websocket';
  code?: number;
  wasClean?: boolean;
}
