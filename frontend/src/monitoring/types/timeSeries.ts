// src/monitoring/types/timeSeries.ts
export interface TimeSeriesData {
    series: TimeSeries[];
    interval: string;
    startTime: string;
    endTime: string;
  }
  
  export interface TimeSeries {
    name: string;
    data: TimeSeriesPoint[];
  }
  
  export interface TimeSeriesPoint {
    timestamp: string;
    value: number;
  }