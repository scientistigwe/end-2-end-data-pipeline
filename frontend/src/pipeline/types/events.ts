// src/pipeline/types/events.ts
import type { PipelineStatus } from './base';

export const PIPELINE_EVENTS = {
  STATUS_CHANGE: 'pipeline:statusChange',
  RUN_COMPLETE: 'pipeline:runComplete',
  ERROR: 'pipeline:error'
} as const;

export interface PipelineStatusChangeDetail {
  pipelineId: string;
  status: PipelineStatus;
  previousStatus: PipelineStatus;
  timestamp: string;
}

export interface PipelineRunCompleteDetail {
  pipelineId: string;
  status: PipelineStatus;
  timestamp: string;
}

export interface PipelineErrorDetail {
  error: string;
  code?: string;
}

export interface PipelineError extends Error {
  name: 'PipelineError';
  code?: string;
  timestamp: string;
  component: 'pipeline';
  details?: unknown;
}

export type PipelineEventMap = {
  'pipeline:statusChange': CustomEvent<PipelineStatusChangeDetail>;
  'pipeline:runComplete': CustomEvent<PipelineRunCompleteDetail>;
  'pipeline:error': CustomEvent<PipelineErrorDetail>;
};

export type PipelineEventName = keyof PipelineEventMap;