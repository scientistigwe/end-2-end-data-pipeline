// src/pipeline/types/metrics.ts
export interface MetricData {
  timestamp: string;
  metrics: {
    throughput: number;
    latency: number;
    errorRate: number;
    resourceUsage: {
      cpu: number;
      memory: number;
    };
  };
}

export interface PipelineMetrics {
  timestamp: string;
  metrics: {
    throughput: number;
    latency: number;
    errorRate: number;
    resourceUsage: {
      cpu: number;
      memory: number;
      disk: number;
    };
    customMetrics?: Record<string, number>;
  };
}

export interface PipelineStats {
  successfulRuns: number;
  totalRuns: number;
  averageDuration: number;
}