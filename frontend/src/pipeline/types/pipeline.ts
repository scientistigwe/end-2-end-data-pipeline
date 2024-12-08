// src/types/pipeline.ts

export type PipelineStatus = 
  | 'idle' 
  | 'running' 
  | 'stopped' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export type PipelineTrigger = 'manual' | 'scheduled' | 'event';
export type PipelineMode = 'development' | 'staging' | 'production';

export interface PipelineConfig {
  id?: string;
  name: string;
  description?: string;
  mode: PipelineMode;
  source: {
    type: string;
    config: Record<string, unknown>;
  };
  steps: PipelineStep[];
  triggers: PipelineTrigger[];
  schedule?: string; // cron expression
  timeout?: number;
  retryPolicy?: {
    attempts: number;
    backoff: number;
  };
  notifications?: {
    onFailure?: boolean;
    onSuccess?: boolean;
    channels?: string[];
  };
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface PipelineStep {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  dependencies?: string[];
  enabled: boolean;
  timeout?: number;
  retryAttempts?: number;
  condition?: string;
  onFailure?: 'stop' | 'continue' | 'retry';
  metadata?: Record<string, unknown>;
}

export interface Pipeline extends PipelineConfig {
  id: string;
  status: PipelineStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  lastRun?: string;
  nextRun?: string;
  stats: PipelineStats;
}

export interface PipelineStats {
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
  averageDuration: number;
  lastRunDuration?: number;
  uptime: number;
}

export interface PipelineRun {
  id: string;
  pipelineId: string;
  version: number;
  status: PipelineStatus;
  trigger: PipelineTrigger;
  startedAt: string;
  completedAt?: string;
  duration?: number;
  steps: PipelineStepRun[];
  error?: {
    message: string;
    step?: string;
    details?: unknown;
  };
  metrics?: Record<string, number>;
}

export interface PipelineStepRun {
  id: string;
  stepId: string;
  status: PipelineStatus;
  startedAt: string;
  completedAt?: string;
  duration?: number;
  error?: {
    message: string;
    details?: unknown;
  };
  output?: unknown;
  metrics?: Record<string, number>;
}

export interface PipelineLogs {
  logs: Array<{
    timestamp: string;
    level: 'info' | 'warn' | 'error';
    step?: string;
    message: string;
    metadata?: Record<string, unknown>;
  }>;
  pagination: {
    total: number;
    page: number;
    limit: number;
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

export interface PipelineSchedule {
  id: string;
  pipelineId: string;
  cron: string;
  enabled: boolean;
  lastRun?: string;
  nextRun?: string;
  timezone?: string;
  description?: string;
}

export interface PipelineEvent {
  id: string;
  pipelineId: string;
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
  processed: boolean;
  error?: string;
}

export interface PipelineFilters {
  status?: PipelineStatus[];
  mode?: PipelineMode[];
  tags?: string[];
  createdBy?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
}