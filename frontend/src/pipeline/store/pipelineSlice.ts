// src/store/pipeline/pipelineSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  PipelineRun,
  PipelineLogs,
  PipelineMetrics,
  PipelineSchedule,
  PipelineEvent,
  PipelineFilters
} from '../types/pipeline';

export type StepStatus = 'pending' | 'running' | 'completed' | 'error';
export type PipelineStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error';
export type PipelineType = 'etl' | 'transformation' | 'validation' | 'custom';

interface PipelineState {
  pipelines: Record<string, Pipeline>;
  runs: Record<string, PipelineRun[]>;
  logs: Record<string, PipelineLogs>;
  metrics: Record<string, PipelineMetrics[]>;
  schedules: Record<string, PipelineSchedule[]>;
  events: Record<string, PipelineEvent[]>;
  selectedPipelineId: string | null;
  filters: PipelineFilters;
  isLoading: boolean;
  error: string | null;
  activePipelines: Record<string, Pipeline>;
  pipelineHistory: PipelineHistoryEntry[];
  configurations: Record<string, PipelineConfig>;
  currentPipeline: string | null;
  loading: boolean;
}

const initialState: PipelineState = {
  pipelines: {},
  runs: {},
  logs: {},
  metrics: {},
  schedules: {},
  events: {},
  selectedPipelineId: null,
  filters: {},
  isLoading: false,
  error: null
};

export interface PipelineStep {
  id: string;
  name: string;
  type: string;
  status: StepStatus;
  startTime?: string;
  endTime?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

interface PipelineConfig {
  name: string;
  type: string;
  description?: string;
  steps: PipelineStep[];
  sourceId: string;
  targetId?: string;
  schedule?: {
    enabled: boolean;
    cron?: string;
    lastRun?: string;
    nextRun?: string;
  };
  retryConfig?: {
    maxAttempts: number;
    backoffMultiplier: number;
  };
}

interface Pipeline {
  id: string;
  name: string;
  status: PipelineStatus;
  progress: number;
  sourceId: string;
  config: PipelineConfig;
  metadata: Record<string, unknown>;
  error?: string;
  startTime: string;
  endTime?: string;
  currentStep?: string;
  attempts: number;
}

interface PipelineHistoryEntry {
  id: string;
  pipelineId: string;
  startTime: string;
  endTime?: string;
  status: PipelineStatus;
  error?: string;
  metrics?: {
    duration: number;
    processedRecords: number;
    failedRecords: number;
  };
}

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
    setPipelineSchedules(
      state,
      action: PayloadAction<{ pipelineId: string; schedules: PipelineSchedule[] }>
    ) {
      state.schedules[action.payload.pipelineId] = action.payload.schedules;
    },
    setPipelineEvents(
      state,
      action: PayloadAction<{ pipelineId: string; events: PipelineEvent[] }>
    ) {
      state.events[action.payload.pipelineId] = action.payload.events;
    },
    setFilters(state, action: PayloadAction<PipelineFilters>) {
      state.filters = action.payload;
    },
    setSelectedPipeline(state, action: PayloadAction<string | null>) {
      state.selectedPipelineId = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    }
  }
});

export const {
  setPipelines,
  updatePipeline,
  updatePipelineStatus,
  setPipelineRuns,
  addPipelineRun,
  setPipelineLogs,
  setPipelineMetrics,
  setPipelineSchedules,
  setPipelineEvents,
  setFilters,
  setSelectedPipeline,
  setLoading,
  setError
} = pipelineSlice.actions;

export default pipelineSlice.reducer;

