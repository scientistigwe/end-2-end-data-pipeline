import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store/rootReducer';
import type { 
  Pipeline, 
  PipelineStatus, 
  PipelineRun, 
  PipelineLogs, 
  PipelineMetrics 
} from '../types/metrics';
import type { PipelineState } from './pipelineSlice';

// Base selectors
export const selectPipelineState = (state: RootState): PipelineState => 
  state.pipelines;

export const selectPipelines = (state: RootState): Record<string, Pipeline> => 
  state.pipelines?.pipelines || {};

export const selectSelectedPipelineId = (state: RootState): string | null => 
  state.pipelines?.selectedPipelineId || null;

export const selectPipelineFilters = (state: RootState): PipelineState['filters'] => 
  state.pipelines?.filters || {};

export const selectPipelineRuns = (state: RootState): Record<string, PipelineRun[]> => 
  state.pipelines?.runs || {};

export const selectPipelineLogs = (state: RootState): Record<string, PipelineLogs> => 
  state.pipelines?.logs || {};

export const selectPipelineMetrics = (state: RootState): Record<string, PipelineMetrics[]> => 
  state.pipelines?.metrics || {};

export const selectIsLoading = (state: RootState): boolean => 
  state.pipelines?.isLoading || false;

export const selectError = (state: RootState): string | null => 
  state.pipelines?.error || null;

// Derived selectors
export const selectSelectedPipeline = createSelector(
  [selectPipelines, selectSelectedPipelineId],
  (pipelines, selectedId): Pipeline | null => 
    selectedId ? pipelines[selectedId] || null : null
);

export const selectFilteredPipelines = createSelector(
  [selectPipelines, selectPipelineFilters],
  (pipelines, filters): Pipeline[] => {
    return Object.values(pipelines).filter(pipeline => {
      if (filters.status?.length && !filters.status.includes(pipeline.status)) {
        return false;
      }
      if (filters.mode?.length && !filters.mode.includes(pipeline.mode)) {
        return false;
      }
      if (filters.dateRange) {
        const pipelineDate = new Date(pipeline.createdAt);
        const start = new Date(filters.dateRange.start);
        const end = new Date(filters.dateRange.end);
        if (pipelineDate < start || pipelineDate > end) {
          return false;
        }
      }
      return true;
    });
  }
);

export const selectPipelinesByStatus = createSelector(
  [selectPipelines],
  (pipelines): Record<PipelineStatus, Pipeline[]> => {
    return Object.values(pipelines).reduce((acc, pipeline) => {
      if (!acc[pipeline.status]) {
        acc[pipeline.status] = [];
      }
      acc[pipeline.status].push(pipeline);
      return acc;
    }, {} as Record<PipelineStatus, Pipeline[]>);
  }
);

export const selectPipelineStats = createSelector(
  [selectPipelines],
  (pipelines) => {
    const pipelineArray = Object.values(pipelines);
    return {
      total: pipelineArray.length,
      running: pipelineArray.filter(p => p.status === 'running').length,
      completed: pipelineArray.filter(p => p.status === 'completed').length,
      failed: pipelineArray.filter(p => p.status === 'failed').length,
      success_rate: pipelineArray.length > 0
        ? (pipelineArray.filter(p => p.status === 'completed').length / pipelineArray.length) * 100
        : 0
    };
  }
);

export const selectPipelineRunsByPipelineId = createSelector(
  [selectPipelineRuns, (_state: RootState, pipelineId: string) => pipelineId],
  (runs, pipelineId): PipelineRun[] => 
    runs[pipelineId] || []
);

export const selectPipelineLogsByPipelineId = createSelector(
  [selectPipelineLogs, (_state: RootState, pipelineId: string) => pipelineId],
  (logs, pipelineId): PipelineLogs | null => 
    logs[pipelineId] || null
);

export const selectPipelineMetricsByPipelineId = createSelector(
  [selectPipelineMetrics, (_state: RootState, pipelineId: string) => pipelineId],
  (metrics, pipelineId): PipelineMetrics[] => 
    metrics[pipelineId] || []
);

export const selectPipelineStatusHistory = (state: RootState): Record<string, Array<{
  status: PipelineStatus;
  previousStatus: PipelineStatus;
  timestamp: string;
}>> => state.pipelines?.statusHistory || {};

export const selectPipelineStatusHistoryById = createSelector(
  [selectPipelineStatusHistory, (_state: RootState, pipelineId: string) => pipelineId],
  (statusHistory, pipelineId) => statusHistory[pipelineId] || []
);