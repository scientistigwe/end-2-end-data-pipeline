// src/pipeline/store/pipelineSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Pipeline,
  PipelineRun,
  PipelineLogs,
  PipelineMetrics,
  PipelineStatus
} from '../types/pipeline';

interface PipelineState {
  pipelines: Record<string, Pipeline>;
  runs: Record<string, PipelineRun[]>;
  logs: Record<string, PipelineLogs>;
  metrics: Record<string, PipelineMetrics[]>;
  selectedPipelineId: string | null;
  isLoading: boolean;
  error: string | null;
  filters: {
    status?: PipelineStatus[];
    mode?: string[];
    dateRange?: {
      start: string;
      end: string;
    };
  };
}

const initialState: PipelineState = {
  pipelines: {},
  runs: {},
  logs: {},
  metrics: {},
  selectedPipelineId: null,
  isLoading: false,
  error: null,
  filters: {}
};

const pipelineSlice = createSlice({
  name: 'pipeline',
  initialState,
  reducers: {
    setPipelines(state, action: PayloadAction<Pipeline[]>) {
      state.pipelines = action.payload.reduce((acc, pipeline) => {
        acc[pipeline.id] = pipeline;
        return acc;
      }, {} as Record<string, Pipeline>);
    },

    updatePipeline(state, action: PayloadAction<Pipeline>) {
      state.pipelines[action.payload.id] = action.payload;
    },

    removePipeline(state, action: PayloadAction<string>) {
      delete state.pipelines[action.payload];
    },

    updatePipelineStatus(
      state,
      action: PayloadAction<{ id: string; status: PipelineStatus }>
    ) {
      if (state.pipelines[action.payload.id]) {
        state.pipelines[action.payload.id].status = action.payload.status;
      }
    },

    setPipelineRuns(
      state,
      action: PayloadAction<{ pipelineId: string; runs: PipelineRun[] }>
    ) {
      state.runs[action.payload.pipelineId] = action.payload.runs;
    },

    addPipelineRun(
      state,
      action: PayloadAction<{ pipelineId: string; run: PipelineRun }>
    ) {
      if (!state.runs[action.payload.pipelineId]) {
        state.runs[action.payload.pipelineId] = [];
      }
      state.runs[action.payload.pipelineId].unshift(action.payload.run);
    },

    setPipelineLogs(
      state,
      action: PayloadAction<{ pipelineId: string; logs: PipelineLogs }>
    ) {
      state.logs[action.payload.pipelineId] = action.payload.logs;
    },

    setPipelineMetrics(
      state,
      action: PayloadAction<{ pipelineId: string; metrics: PipelineMetrics[] }>
    ) {
      state.metrics[action.payload.pipelineId] = action.payload.metrics;
    },

    setSelectedPipelineId(state, action: PayloadAction<string | null>) {
      state.selectedPipelineId = action.payload;
    },

    setFilters(state, action: PayloadAction<PipelineState['filters']>) {
      state.filters = action.payload;
    },

    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },

    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },

    resetPipelineState(state) {
      Object.assign(state, initialState);
    }
  }
});

export const {
  setPipelines,
  updatePipeline,
  removePipeline,
  updatePipelineStatus,
  setPipelineRuns,
  addPipelineRun,
  setPipelineLogs,
  setPipelineMetrics,
  setSelectedPipelineId,
  setFilters,
  setLoading,
  setError,
  resetPipelineState
} = pipelineSlice.actions;

export type pipelineState = typeof initialState;
export default pipelineSlice.reducer;


