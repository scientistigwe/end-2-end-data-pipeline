// src/monitoring/types/base.ts
export type MetricStatus = 'healthy' | 'warning' | 'critical';
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';
export type MonitoringEventType = 'metrics' | 'error' | 'status';

export interface MetricDefinition {
  name: string;
  type: 'gauge' | 'counter' | 'histogram';
  unit?: string;
  description?: string;
  labels?: string[];
}