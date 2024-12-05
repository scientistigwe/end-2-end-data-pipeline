// src/types/visualization.ts
import { TimeRange } from './common';

export interface TimeSeriesDataPoint {
    timestamp: string;
    value: number;
    metric: string;
  }
  
  export interface TimeSeriesData {
    series: {
      name: string;
      data: TimeSeriesDataPoint[];
    }[];
    metadata: {
      startTime: string;
      endTime: string;
      interval: string;
    };
  }
  
  export interface AggregatedMetric {
    name: string;
    value: number;
    change: number;
    trend: 'up' | 'down' | 'stable';
    period: TimeRange;
  }
  
  export interface ChartData {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
      color?: string;
    }[];
  }
  
  export interface HeatmapData {
    data: Array<{
      x: string;
      y: string;
      value: number;
    }>;
    xLabels: string[];
    yLabels: string[];
  }
  