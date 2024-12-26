// src/monitoring/types/state.ts
import type { MetricStatus, TimeRange } from './base';
import type { MetricsData, SystemHealth, ResourceUsage } from './metrics';
import type { Alert } from './alerts';

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