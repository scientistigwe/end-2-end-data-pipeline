// src/monitoring/types/metrics.ts
import type { MetricStatus } from './base';

export interface MetricsData {
  type: string;
  timestamp: string;
  values: Record<string, number>;
  status: MetricStatus;
  labels?: Record<string, string>;
  metadata?: Record<string, unknown>;
  pipelines: Record<string, PipelineMetrics>;
  dataSources: Record<string, DataSourceMetrics>;
}

export interface PipelineMetrics {
  throughput: number;
  latency: number;
  errorRate: number;
  lastUpdated: string;
}

export interface DataSourceMetrics {
  availability: number;
  responseTime: number;
  errorCount: number;
  lastChecked: string;
}

export interface SystemHealth {
  status: MetricStatus;
  lastChecked: string;
  components: HealthComponent[];
  error?: string;
  lastUpdated: string;
}

export interface HealthComponent {
  name: string;
  status: MetricStatus;
  message?: string;
  lastChecked?: string;
}

export interface PerformanceMetrics {
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  latency: LatencyMetrics;
  throughput: ThroughputMetrics;
}

export interface CpuMetrics {
  usage: number;
  load: number;
  threads: number;
}

export interface MemoryMetrics {
  used: number;
  available: number;
  peak: number;
}

export interface LatencyMetrics {
  p50: number;
  p90: number;
  p99: number;
}

export interface ThroughputMetrics {
  current: number;
  average: number;
  peak: number;
}

export interface ResourceUsage {
  cpu: ResourceMetric;
  memory: ResourceMetric;
  network: NetworkUsage;
  disk: ResourceMetric;
  timestamp: string;
}

export interface ResourceMetric {
  used: number;
  total: number;
  percentage: number;
}

export interface NetworkUsage {
  incoming: number;
  outgoing: number;
}