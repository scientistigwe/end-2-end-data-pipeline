// src/pipeline/types/base.ts
export type PipelineEventType = 'statusChange' | 'runComplete' | 'error';
export type PipelineStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type PipelineMode = 'development' | 'staging' | 'production';
export type LogLevel = 'info' | 'warn' | 'error';

export interface RouteDefinition {
  PIPELINES: {
    [K in PipelineRouteAction]: string;
  };
}

// Define valid route actions
export type PipelineRouteAction =
  | 'LIST'
  | 'CREATE'
  | 'GET'
  | 'UPDATE'
  | 'DELETE'
  | 'START'
  | 'STOP'
  | 'PAUSE'
  | 'RESUME'
  | 'RETRY'
  | 'LOGS'
  | 'METRICS'
  | 'RUNS'
  | 'VALIDATE';