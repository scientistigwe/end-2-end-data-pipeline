// src/types/monitoring.ts
export type MetricStatus = 'healthy' | 'warning' | 'critical';
export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface MonitoringConfig {
  metrics: string[];
  interval?: number;
  alertThresholds?: Record<string, number>;
}

export interface MetricsData {
  timestamp: string;
  values: Record<string, number>;
  status: MetricStatus;
}

export interface SystemHealth {
  status: MetricStatus;
  lastChecked: string;
  components: Array<{
    name: string;
    status: MetricStatus;
    message?: string;
  }>;
  error?: string;
}

export interface PerformanceMetrics {
  cpu: number;
  memory: number;
  latency: number;
  throughput: number;
  timestamp: string;
}

export interface AlertConfig {
  metric: string;
  threshold: number;
  severity: AlertSeverity;
  condition: 'above' | 'below';
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
}

export interface ResourceUsage {
  cpu: {
    used: number;
    total: number;
    percentage: number;
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
