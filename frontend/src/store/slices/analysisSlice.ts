// store/slices/analysisSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Define the correct types for analysis statuses and types
type AnalysisStatus = 'running' | 'completed' | 'error';
type AnalysisType = 'quality' | 'insight';

// Define interfaces for different payloads
interface AnalysisStartedPayload {
  analysisId: string;
  type: AnalysisType;
}

interface UpdateAnalysisProgressPayload {
  analysisId: string;
  progress: number;
}

interface AnalysisCompletedPayload {
  analysisId: string;
  results: any;
}

interface AnalysisErrorPayload {
  analysisId: string;
  error: string;
}

interface Analysis {
  id: string;
  type: AnalysisType;
  status: AnalysisStatus;
  progress: number;
  results: any;
  error?: string;
  startedAt: string;
  completedAt?: string;
}

interface AnalysisState {
  activeAnalyses: Record<string, Analysis>;
  qualityReports: Record<string, {
    id: string;
    timestamp: string;
    metrics: any;
    issues: any[];
    recommendations: any[];
  }>;
  insightReports: Record<string, {
    id: string;
    timestamp: string;
    insights: any[];
    trends: any[];
    anomalies: any[];
  }>;
}

const initialState: AnalysisState = {
  activeAnalyses: {},
  qualityReports: {},
  insightReports: {}
};

export const analysisSlice = createSlice({
  name: 'analysis',
  initialState,
  reducers: {
    analysisStarted(state, action: PayloadAction<AnalysisStartedPayload>) {
      state.activeAnalyses[action.payload.analysisId] = {
        id: action.payload.analysisId,
        type: action.payload.type,
        status: 'running',
        progress: 0,
        results: null,
        startedAt: new Date().toISOString()
      };
    },
    updateAnalysisProgress(state, action: PayloadAction<UpdateAnalysisProgressPayload>) {
      const analysis = state.activeAnalyses[action.payload.analysisId];
      if (analysis) {
        analysis.progress = Math.min(Math.max(action.payload.progress, 0), 100);
      }
    },
    analysisCompleted(state, action: PayloadAction<AnalysisCompletedPayload>) {
      const analysis = state.activeAnalyses[action.payload.analysisId];
      if (analysis) {
        analysis.status = 'completed';
        analysis.progress = 100;
        analysis.results = action.payload.results;
        analysis.completedAt = new Date().toISOString();
        
        // Store results in appropriate report collection
        if (analysis.type === 'quality') {
          state.qualityReports[action.payload.analysisId] = {
            id: action.payload.analysisId,
            timestamp: analysis.completedAt,
            ...action.payload.results
          };
        } else {
          state.insightReports[action.payload.analysisId] = {
            id: action.payload.analysisId,
            timestamp: analysis.completedAt,
            ...action.payload.results
          };
        }
      }
    },
    analysisError(state, action: PayloadAction<AnalysisErrorPayload>) {
      const analysis = state.activeAnalyses[action.payload.analysisId];
      if (analysis) {
        analysis.status = 'error';
        analysis.error = action.payload.error;
      }
    },
    removeAnalysis(state, action: PayloadAction<string>) {
      delete state.activeAnalyses[action.payload];
    }
  }
});

// Export actions
export const {
  analysisStarted,
  updateAnalysisProgress,
  analysisCompleted,
  analysisError,
  removeAnalysis
} = analysisSlice.actions;

// Selectors
export const selectActiveAnalyses = (state: RootState) => state.analysis.activeAnalyses;
export const selectQualityReports = (state: RootState) => state.analysis.qualityReports;
export const selectInsightReports = (state: RootState) => state.analysis.insightReports;
export const selectAnalysisById = (id: string) => (state: RootState) => 
  state.analysis.activeAnalyses[id];

export default analysisSlice.reducer;