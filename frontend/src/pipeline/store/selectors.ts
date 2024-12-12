// src/pipeline/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store';
import { PipelineState } from './pipelineSlice';
import { PipelineStatus } from '../types/pipeline';

// Base selectors
export const selectPipelineState = (state: RootState) => state.pipeline;
export const selectPipelines = (state: RootState) => state.pipeline.pipelines;
export const selectSelectedPipelineId = (state: RootState) => 
  state.pipeline.selectedPipelineId;
export const selectPipelineFilters = (state: RootState) => state.pipeline.filters;

// Derived selectors
export const selectSelectedPipeline = createSelector(
  [selectPipelines, selectSelectedPipelineId],
  (pipelines, selectedId) => selectedId ? pipelines[selectedId] : null
);

export const selectFilteredPipelines = createSelector(
  [selectPipelines, selectPipelineFilters],
  (pipelines, filters) => {
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
  (pipelines) => {
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
