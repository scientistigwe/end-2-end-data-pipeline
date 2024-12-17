// src/pipeline/types/pipeline.ts
export type PipelineEventType = 'statusChange' | 'runComplete' | 'error';
export type PipelineStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type PipelineMode = 'development' | 'staging' | 'production';
export type LogLevel = 'info' | 'warn' | 'error';

export interface PipelineStep {
  id: string;
  name: string;
  type: string;
  status: PipelineStatus;
  config: Record<string, unknown>;
  dependencies?: string[];
  enabled: boolean;
  timeout?: number;
  retryAttempts?: number;
  condition?: string;
  onFailure?: 'stop' | 'continue' | 'retry';
  metadata?: Record<string, unknown>;
}

export interface PipelineConfig {
  name: string;
  description?: string;
  mode: PipelineMode;
  steps: PipelineStep[];
  sourceId: string;
  targetId?: string;
  schedule?: {
    enabled: boolean;
    cron?: string;
    timezone?: string;
  };
  retryConfig?: {
    maxAttempts: number;
    backoffMultiplier: number;
  };
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface PipelineStats {
  successfulRuns: number;
  totalRuns: number;
  averageDuration: number;
}

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

export interface Pipeline extends PipelineConfig {
  id: string;
  status: PipelineStatus;
  progress: number;
  error?: string;
  startTime: string;
  endTime?: string;
  currentStep?: string;
  attempts: number;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  lastRun?: string;
  nextRun?: string;
  stats: PipelineStats;
  metrics?: MetricData[];
}

export interface PipelineRun {
  id: string;
  pipelineId: string;
  version: number;
  status: PipelineStatus;
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
    level: LogLevel;
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

export interface PipelineState {
  pipelines: Record<string, {
    id: string;
    name: string;
    description?: string;
    status: 'active' | 'paused' | 'failed';
    steps: Array<{
      id: string;
      type: string;
      config: Record<string, unknown>;
      dependencies: string[];
      status: 'pending' | 'running' | 'completed' | 'failed';
    }>;
    schedule?: {
      enabled: boolean;
      cron: string;
      lastRun?: string;
      nextRun?: string;
    };
    metadata: {
      createdAt: string;
      updatedAt: string;
      lastRun?: string;
      successCount: number;
      failureCount: number;
    };
  }>;
  activePipelineId: string | null;
  isLoading: boolean;
  error: string | null;
}

export interface PipelineError extends Error {
  name: 'PipelineError';
  code?: string;
  timestamp: string;
  component: 'pipeline';
  details?: unknown;
}

// Event constants
export const PIPELINE_EVENTS = {
  STATUS_CHANGE: 'pipeline:statusChange',
  RUN_COMPLETE: 'pipeline:runComplete',
  ERROR: 'pipeline:error'
} as const;

export interface PipelineError extends Error {
  name: 'PipelineError';
  code?: string;
  timestamp: string;
  component: 'pipeline';
  details?: unknown;
}

// Event detail types
export interface PipelineStatusChangeDetail {
  pipelineId: string;
  status: PipelineStatus;
  previousStatus: PipelineStatus;
}

export interface PipelineRunCompleteDetail {
  pipelineId: string;
  status: PipelineStatus;
}

export interface PipelineErrorDetail {
  error: string;
  code?: string;
}

// Error type
export interface PipelineError extends Error {
  name: 'PipelineError';
  code?: string;
  timestamp: string;
  component: 'pipeline';
  details?: unknown;
}

// Event map type
export type PipelineEventMap = {
  'pipeline:statusChange': CustomEvent<PipelineStatusChangeDetail>;
  'pipeline:runComplete': CustomEvent<PipelineRunCompleteDetail>;
  'pipeline:error': CustomEvent<PipelineErrorDetail>;
};

export type PipelineEventName = keyof PipelineEventMap;



