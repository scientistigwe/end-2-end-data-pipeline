// store/slices/pipelineSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';
import type {
  PipelineState,
  Pipeline,
  PipelineConfig,
  PipelineStatus,
  StepStatus
} from '../types';

// Define payload interfaces
interface StartPipelinePayload {
  pipelineId: string;
  config: PipelineConfig;
  sourceId: string;
}

interface UpdatePipelineStatusPayload {
  pipelineId: string;
  status: PipelineStatus;
  progress?: number;
  error?: string;
  currentStep?: string;
}

interface UpdateStepStatusPayload {
  pipelineId: string;
  stepId: string;
  status: StepStatus;
  error?: string;
}

// Define payload interfaces
interface StartPipelinePayload {
  pipelineId: string;
  config: PipelineConfig;
  sourceId: string;
}

interface UpdatePipelineStatusPayload {
  pipelineId: string;
  status: PipelineStatus;
  progress?: number;
  error?: string;
  currentStep?: string;
}

interface UpdateStepStatusPayload {
  pipelineId: string;
  stepId: string;
  status: StepStatus;
  error?: string;
}

const initialState: PipelineState = {
  activePipelines: {},
  pipelineHistory: [],
  configurations: {},
  currentPipeline: null,
  loading: false,
  error: null
};

export const pipelineSlice = createSlice({
  name: 'pipelines',
  initialState,
  reducers: {
    pipelineStarted(state, action: PayloadAction<StartPipelinePayload>) {
      const { pipelineId, config, sourceId } = action.payload;
      const startTime = new Date().toISOString();
      
      state.activePipelines[pipelineId] = {
        id: pipelineId,
        name: config.name, // Add name from config
        status: 'running',
        progress: 0,
        sourceId,
        config,
        metadata: {},
        startTime,
        attempts: 1
      };

      state.pipelineHistory.push({
        id: Date.now().toString(),
        pipelineId,
        startTime,
        status: 'running'
      });
    },

    updatePipelineStatus(state, action: PayloadAction<UpdatePipelineStatusPayload>) {
      const { pipelineId, status, progress, error, currentStep } = action.payload;
      const pipeline = state.activePipelines[pipelineId];
      
      if (pipeline) {
        pipeline.status = status;
        if (progress !== undefined) {
          pipeline.progress = Math.min(Math.max(progress, 0), 100);
        }
        if (error) {
          pipeline.error = error;
        }
        if (currentStep) {
          pipeline.currentStep = currentStep;
        }

        // Update history if pipeline completes or errors
        if (status === 'completed' || status === 'error') {
          const endTime = new Date().toISOString();
          pipeline.endTime = endTime;
          
          const historyEntry = state.pipelineHistory.find(h => 
            h.pipelineId === pipelineId && !h.endTime);
          
          if (historyEntry) {
            historyEntry.endTime = endTime;
            historyEntry.status = status;
            historyEntry.error = error;
          }
        }
      }
    },

    updateStepStatus(state, action: PayloadAction<UpdateStepStatusPayload>) {
      const { pipelineId, stepId, status, error } = action.payload;
      const pipeline = state.activePipelines[pipelineId];
      
      if (pipeline) {
        const step = pipeline.config.steps.find(s => s.id === stepId);
        if (step) {
          step.status = status;
          step.error = error;
          
          if (status === 'running') {
            step.startTime = new Date().toISOString();
          } else if (status === 'completed' || status === 'error') {
            step.endTime = new Date().toISOString();
          }
        }
      }
    },

    savePipelineConfig(state, action: PayloadAction<{ id: string; config: PipelineConfig }>) {
      state.configurations[action.payload.id] = action.payload.config;
    },

    clearPipelineError(state, action: PayloadAction<string>) {
      const pipeline = state.activePipelines[action.payload];
      if (pipeline) {
        delete pipeline.error;
      }
    },

    removePipeline(state, action: PayloadAction<string>) {
      delete state.activePipelines[action.payload];
    }
  }
});

// Export actions
export const {
  pipelineStarted,
  updatePipelineStatus,
  updateStepStatus,
  savePipelineConfig,
  clearPipelineError,
  removePipeline
} = pipelineSlice.actions;

// Selectors
export const selectActivePipelines = (state: RootState) => state.pipelines.activePipelines;
export const selectPipelineById = (id: string) => 
  (state: RootState) => state.pipelines.activePipelines[id];
export const selectPipelineHistory = (state: RootState) => state.pipelines.pipelineHistory;
export const selectPipelineConfigs = (state: RootState) => state.pipelines.configurations;
export const selectPipelinesBySource = (sourceId: string) => (state: RootState) => 
  Object.values(state.pipelines.activePipelines).filter(p => p.sourceId === sourceId);

export default pipelineSlice.reducer;