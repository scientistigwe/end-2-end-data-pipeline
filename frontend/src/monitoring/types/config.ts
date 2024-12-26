// src/monitoring/types/config.ts
import type { TimeRange } from './base';

export interface MonitoringConfig {
  metrics: string[];
  interval?: number;
  alertThresholds?: Record<string, number>;
  timeRange?: TimeRange;
  retention?: string;
}