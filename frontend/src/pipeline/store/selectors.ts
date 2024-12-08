// src/store/pipeline/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../../../store/index';

export const selectPipelines = (state: RootState) => state.pipelines.pipelines;
export const selectPipelineRuns = (state: RootState) => state.pipelines.runs;
export const selectPipelineLogs = (state: RootState) => state.pipelines.logs;
export const selectPipelineMetrics = (state: RootState) => state.pipelines.metrics;
export const selectPipelineSchedules = (state: RootState) => state.pipelines.schedules;
export const selectPipelineEvents = (state: RootState) => state.pipelines.events;
export const selectFilters = (state: RootState) => state.pipelines.filters;
export const selectSelectedPipelineId = (state: RootState) => 
  state.pipelines.selectedPipelineId;

export const selectFilteredPipelines = createSelector(
  [selectPipelines, selectFilters],
  (pipelines, filters) => {
    return Object.values(pipelines).filter(pipeline => {
      if (filters.status && !filters.status.includes(pipeline.status)) {
        return false;
      }
      if (filters.mode && !filters.mode.includes(pipeline.mode)) {
        return false;
      }
      if (filters.tags && filters.tags.length > 0) {
        if (!pipeline.tags?.some(tag => filters.tags?.includes(tag))) {
          return false;
        }
      }
      if (filters.createdBy && !filters.createdBy.includes(pipeline.createdBy)) {
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

export const selectSelectedPipeline = createSelector(
  [selectPipelines, selectSelectedPipelineId],
  (pipelines, selectedId) => selectedId ? pipelines[selectedId] : null
);

