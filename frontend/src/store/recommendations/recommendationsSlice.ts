// src/store/recommendations/recommendationsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Recommendation,
  RecommendationHistory,
  RecommendationFilters
} from '../../types/recommendations';

interface RecommendationsState {
  recommendations: Record<string, Recommendation>;
  history: Record<string, RecommendationHistory[]>;
  filters: RecommendationFilters;
  selectedRecommendationId: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: RecommendationsState = {
  recommendations: {},
  history: {},
  filters: {},
  selectedRecommendationId: null,
  isLoading: false,
  error: null
};

const recommendationsSlice = createSlice({
  name: 'recommendations',
  initialState,
  reducers: {
    setRecommendations(state, action: PayloadAction<Recommendation[]>) {
      state.recommendations = action.payload.reduce((acc, rec) => {
        acc[rec.id] = rec;
        return acc;
      }, {} as Record<string, Recommendation>);
    },
    updateRecommendation(state, action: PayloadAction<Recommendation>) {
      state.recommendations[action.payload.id] = action.payload;
    },
    setRecommendationHistory(
      state,
      action: PayloadAction<{ pipelineId: string; history: RecommendationHistory[] }>
    ) {
      state.history[action.payload.pipelineId] = action.payload.history;
    },
    addHistoryEntry(
      state,
      action: PayloadAction<{ pipelineId: string; entry: RecommendationHistory }>
    ) {
      if (!state.history[action.payload.pipelineId]) {
        state.history[action.payload.pipelineId] = [];
      }
      state.history[action.payload.pipelineId].unshift(action.payload.entry);
    },
    setFilters(state, action: PayloadAction<RecommendationFilters>) {
      state.filters = action.payload;
    },
    setSelectedRecommendation(state, action: PayloadAction<string | null>) {
      state.selectedRecommendationId = action.payload;
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
  setRecommendations,
  updateRecommendation,
  setRecommendationHistory,
  addHistoryEntry,
  setFilters,
  setSelectedRecommendation,
  setLoading,
  setError
} = recommendationsSlice.actions;

export default recommendationsSlice.reducer;

