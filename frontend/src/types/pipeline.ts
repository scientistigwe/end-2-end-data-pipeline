// src/types/pipeline.ts
import { AnalysisType } from './analysis';

export type PipelineStatus = 
  | 'idle' 
  | 'running' 
  | 'stopped' 
  | 'completed' 
  | 'failed' 
  | 'cancelled';

export interface Pipeline {
  id: string;
  name: string;
  status: string;
}

export interface PipelineConfig {
  id?: string;
  name: string;
  description?: string;
  type: AnalysisType;
  source: {
    type: string;
    config: Record<string, unknown>;
  };
  options?: {
    timeout?: number;
    retryAttempts?: number;
    priority?: 'high' | 'medium' | 'low';
  };
}

export interface PipelineResponse {
  id: string;
  name: string;
  type: AnalysisType;
  status: PipelineStatus;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface PipelineLogs {
  logs: Array<{
    timestamp: string;
    level: 'info' | 'warn' | 'error';
    message: string;
    metadata?: Record<string, unknown>;
  }>;
  metadata?: {
    startTime: string;
    endTime?: string;
    totalEntries: number;
  };
}

