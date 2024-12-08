// src/analysis/store/analysisSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  AnalysisResult,
  QualityReport,
  InsightReport
} from '../types/analysis';

interface AnalysisState {
  analyses: Record<string, {
    id: string;
    type: string;
    status: 'running' | 'completed' | 'error';
    results: unknown;
  }>;
  activeAnalyses: Record<string, AnalysisResult>;
  qualityReports: Record<string, QualityReport>;
  insightReports: Record<string, InsightReport>;
  selectedAnalysisId: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: AnalysisState = {
  analyses: {},
  activeAnalyses: {},
  qualityReports: {},
  insightReports: {},
  selectedAnalysisId: null,
  isLoading: false,
  error: null
};

const analysisSlice = createSlice({
  name: 'analysis',
  initialState,
  reducers: {
    setAnalysis(state, action: PayloadAction<AnalysisResult>) {
      state.activeAnalyses[action.payload.id] = action.payload;
    },
    removeAnalysis(state, action: PayloadAction<string>) {
      delete state.activeAnalyses[action.payload];
      delete state.qualityReports[action.payload];
      delete state.insightReports[action.payload];
    },
    setQualityReport(
      state,
      action: PayloadAction<{ id: string; report: QualityReport }>
    ) {
      state.qualityReports[action.payload.id] = action.payload.report;
    },
    setInsightReport(
      state,
      action: PayloadAction<{ id: string; report: InsightReport }>
    ) {
      state.insightReports[action.payload.id] = action.payload.report;
    },
    setSelectedAnalysis(state, action: PayloadAction<string | null>) {
      state.selectedAnalysisId = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
    updateAnalysisProgress(
      state,
      action: PayloadAction<{ id: string; progress: number }>
    ) {
      if (state.activeAnalyses[action.payload.id]) {
        state.activeAnalyses[action.payload.id].progress = action.payload.progress;
      }
    }
  }
});

export const {
  setAnalysis,
  removeAnalysis,
  setQualityReport,
  setInsightReport,
  setSelectedAnalysis,
  setLoading,
  setError,
  updateAnalysisProgress
} = analysisSlice.actions;

export default analysisSlice.reducer;

