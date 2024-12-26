// src/pipeline/types/config.ts
import type { PipelineMode, PipelineStatus } from './base';

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