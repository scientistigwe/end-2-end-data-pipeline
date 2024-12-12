// src/monitoring/utils/metrics.ts
import { 
    MetricsData, 
    ResourceUsage, 
    TimeSeriesData,
    MetricStatus 
  } from '../types/monitoring';
  import { MONITORING_CONFIG } from '../constants';
  
  export const calculateAverageMetric = (metrics: MetricsData[], key: string): number => {
    if (!metrics.length) return 0;
    const sum = metrics.reduce((acc, metric) => acc + (metric.values[key] || 0), 0);
    return sum / metrics.length;
  };
  
  export const calculateResourceTrend = (
    current: number,
    previous: number
  ): { trend: 'up' | 'down' | 'stable'; percentage: number } => {
    if (current === previous) return { trend: 'stable', percentage: 0 };
    const percentage = ((current - previous) / previous) * 100;
    return {
      trend: percentage > 0 ? 'up' : 'down',
      percentage: Math.abs(percentage)
    };
  };
  
  export const getMetricStatus = (value: number, thresholds: {
    warning: number;
    critical: number;
  }): MetricStatus => {
    if (value >= thresholds.critical) return 'critical';
    if (value >= thresholds.warning) return 'warning';
    return 'healthy';
  };
  
  export const formatMetricValue = (value: number, unit?: string): string => {
    if (unit === '%') return `${value.toFixed(1)}%`;
    if (unit === 'ms') return `${value.toFixed(0)}ms`;
    if (unit === 'MB') return `${(value / 1024 / 1024).toFixed(2)} MB`;
    return value.toFixed(2);
  };
  