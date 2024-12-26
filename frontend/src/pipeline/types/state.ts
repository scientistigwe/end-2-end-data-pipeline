// src/pipeline/types/state.ts
import type { PipelineStatus } from './base';
import type { Pipeline, PipelineRun, PipelineLogs } from './models';
import type { PipelineMetrics } from './metrics';

export interface PipelineState {
  pipelines: Record<string, Pipeline>;
  selectedPipelineId: string | null;
  runs: Record<string, PipelineRun[]>;
  logs: Record<string, PipelineLogs>;
  metrics: Record<string, PipelineMetrics[]>;
  filters: PipelineStateFilters;
  isLoading: boolean;
  error: string | null;
}

export interface PipelineStateFilters {
  status?: PipelineStatus[];
  startDate?: string;
  endDate?: string;
  search?: string;
  mode?: string[];
  tags?: string[];
}

export interface PipelineDashboardState {
  metrics: {
    totalPipelines: number;
    activePipelines: number;
    failedPipelines: number;
    averageRuntime: number;
    successRate: number;
  };
  recentRuns: PipelineRun[];
  statusBreakdown: Record<PipelineStatus, number>;
  resourceUsage: {
    cpu: number;
    memory: number;
    storage: number;
  };
  alerts: Array<{
    id: string;
    type: string;
    message: string;
    timestamp: string;
    severity: 'low' | 'medium' | 'high';
  }>;
}

export interface PipelineUIState {
  selectedPipeline: string | null;
  selectedTab: 'overview' | 'runs' | 'logs' | 'metrics' | 'settings';
  isEditing: boolean;
  isConfiguring: boolean;
  expandedSections: Set<string>;
  viewMode: 'list' | 'grid' | 'table';
  timeRange: {
    start: string;
    end: string;
  };
}

export interface PipelineCache {
  data: Record<string, Pipeline>;
  metrics: Record<string, PipelineMetrics[]>;
  timestamp: number;
  expiresAt: number;
}

export interface PipelineStateUpdate {
  type: 'add' | 'update' | 'remove';
  pipelineId: string;
  data?: Partial<Pipeline>;
  timestamp: string;
}

export interface PipelineBatchState {
  operations: PipelineStateUpdate[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
  errors: Array<{
    pipelineId: string;
    error: string;
  }>;
  timestamp: string;
}