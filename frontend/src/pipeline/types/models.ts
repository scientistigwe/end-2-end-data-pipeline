// src/pipeline/types/types.ts
import type { LogLevel, PipelineStatus } from './base';
import type { PipelineConfig } from './config';
import type { MetricData, PipelineStats } from './metrics';

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