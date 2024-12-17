import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Pipeline,
  PipelineRun,
  PipelineLogs,
  PipelineMetrics,
  PipelineStatus
} from '../types/pipeline';

// Define the state interface
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
      if (!Array.isArray(action.payload)) {
        state.error = 'Invalid pipeline data received';
        return;
      }

      try {
        const pipelinesMap: Record<string, Pipeline> = {};
        
        action.payload.forEach((pipeline) => {
          if (pipeline && typeof pipeline.id !== 'undefined') {
            pipelinesMap[pipeline.id] = pipeline;
          }
        });

        state.pipelines = pipelinesMap;
        state.error = null;
      } catch (error) {
        state.error = 'Error processing pipeline data';
        console.error('Error in setPipelines reducer:', error);
      }
    },

    updatePipeline(state, action: PayloadAction<Pipeline>) {
      if (!action.payload?.id) {
        state.error = 'Invalid pipeline update data';
        return;
      }

      try {
        state.pipelines[action.payload.id] = action.payload;
        state.error = null;
      } catch (error) {
        state.error = 'Error updating pipeline';
        console.error('Error in updatePipeline reducer:', error);
      }
    },

    removePipeline(state, action: PayloadAction<string>) {
      if (typeof action.payload !== 'string') {
        state.error = 'Invalid pipeline ID for removal';
        return;
      }

      try {
        delete state.pipelines[action.payload];
        // Clean up related data
        delete state.runs[action.payload];
        delete state.logs[action.payload];
        delete state.metrics[action.payload];
        
        if (state.selectedPipelineId === action.payload) {
          state.selectedPipelineId = null;
        }
        
        state.error = null;
      } catch (error) {
        state.error = 'Error removing pipeline';
        console.error('Error in removePipeline reducer:', error);
      }
    },

    updatePipelineStatus(
      state,
      action: PayloadAction<{ id: string; status: PipelineStatus }>
    ) {
      const { id, status } = action.payload;
      if (!id || !status) {
        state.error = 'Invalid pipeline status update data';
        return;
      }

      try {
        if (state.pipelines[id]) {
          state.pipelines[id].status = status;
          state.error = null;
        } else {
          state.error = 'Pipeline not found';
        }
      } catch (error) {
        state.error = 'Error updating pipeline status';
        console.error('Error in updatePipelineStatus reducer:', error);
      }
    },

    setPipelineRuns(
      state,
      action: PayloadAction<{ pipelineId: string; runs: PipelineRun[] }>
    ) {
      const { pipelineId, runs } = action.payload;
      if (!pipelineId || !Array.isArray(runs)) {
        state.error = 'Invalid pipeline runs data';
        return;
      }

      try {
        state.runs[pipelineId] = runs;
        state.error = null;
      } catch (error) {
        state.error = 'Error setting pipeline runs';
        console.error('Error in setPipelineRuns reducer:', error);
      }
    },

    addPipelineRun(
      state,
      action: PayloadAction<{ pipelineId: string; run: PipelineRun }>
    ) {
      const { pipelineId, run } = action.payload;
      if (!pipelineId || !run) {
        state.error = 'Invalid pipeline run data';
        return;
      }

      try {
        if (!state.runs[pipelineId]) {
          state.runs[pipelineId] = [];
        }
        state.runs[pipelineId].unshift(run);
        state.error = null;
      } catch (error) {
        state.error = 'Error adding pipeline run';
        console.error('Error in addPipelineRun reducer:', error);
      }
    },

    setPipelineLogs(
      state,
      action: PayloadAction<{ pipelineId: string; logs: PipelineLogs }>
    ) {
      const { pipelineId, logs } = action.payload;
      if (!pipelineId || !logs) {
        state.error = 'Invalid pipeline logs data';
        return;
      }

      try {
        state.logs[pipelineId] = logs;
        state.error = null;
      } catch (error) {
        state.error = 'Error setting pipeline logs';
        console.error('Error in setPipelineLogs reducer:', error);
      }
    },

    setPipelineMetrics(
      state,
      action: PayloadAction<{ pipelineId: string; metrics: PipelineMetrics[] }>
    ) {
      const { pipelineId, metrics } = action.payload;
      if (!pipelineId || !Array.isArray(metrics)) {
        state.error = 'Invalid pipeline metrics data';
        return;
      }

      try {
        state.metrics[pipelineId] = metrics;
        state.error = null;
      } catch (error) {
        state.error = 'Error setting pipeline metrics';
        console.error('Error in setPipelineMetrics reducer:', error);
      }
    },

    setSelectedPipelineId(state, action: PayloadAction<string | null>) {
      if (action.payload !== null && typeof action.payload !== 'string') {
        state.error = 'Invalid selected pipeline ID';
        return;
      }

      try {
        state.selectedPipelineId = action.payload;
        state.error = null;
      } catch (error) {
        state.error = 'Error setting selected pipeline';
        console.error('Error in setSelectedPipelineId reducer:', error);
      }
    },

    setFilters(state, action: PayloadAction<PipelineState['filters']>) {
      if (!action.payload || typeof action.payload !== 'object') {
        state.error = 'Invalid filters data';
        return;
      }

      try {
        state.filters = action.payload;
        state.error = null;
      } catch (error) {
        state.error = 'Error setting filters';
        console.error('Error in setFilters reducer:', error);
      }
    },

    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = Boolean(action.payload);
    },

    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },

    resetPipelineState(state) {
      try {
        Object.assign(state, initialState);
      } catch (error) {
        console.error('Error in resetPipelineState reducer:', error);
        state.error = 'Error resetting state';
      }
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

// Export the RootState type
export type RootState = {
  pipeline: PipelineState;
};

export default pipelineSlice.reducer;