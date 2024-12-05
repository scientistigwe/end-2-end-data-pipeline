// src/store/decisions/decisionsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Decision,
  DecisionDetails,
  DecisionHistoryEntry,
  DecisionFilters,
  DecisionComment,
  DecisionImpactAnalysis
} from '../../types/decisions';

interface DecisionsState {
  decisions: Record<string, Decision>;
  details: Record<string, DecisionDetails>;
  history: Record<string, DecisionHistoryEntry[]>;
  impact: Record<string, DecisionImpactAnalysis>;
  filters: DecisionFilters;
  selectedDecisionId: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: DecisionsState = {
  decisions: {},
  details: {},
  history: {},
  impact: {},
  filters: {},
  selectedDecisionId: null,
  isLoading: false,
  error: null
};

const decisionsSlice = createSlice({
  name: 'decisions',
  initialState,
  reducers: {
    setDecisions(state, action: PayloadAction<Decision[]>) {
      state.decisions = action.payload.reduce((acc, decision) => {
        acc[decision.id] = decision;
        return acc;
      }, {} as Record<string, Decision>);
    },
    updateDecision(state, action: PayloadAction<Decision>) {
      state.decisions[action.payload.id] = action.payload;
    },
    setDecisionDetails(
      state,
      action: PayloadAction<{ id: string; details: DecisionDetails }>
    ) {
      state.details[action.payload.id] = action.payload.details;
    },
    setDecisionHistory(
      state,
      action: PayloadAction<{ pipelineId: string; history: DecisionHistoryEntry[] }>
    ) {
      state.history[action.payload.pipelineId] = action.payload.history;
    },
    addHistoryEntry(
      state,
      action: PayloadAction<{ pipelineId: string; entry: DecisionHistoryEntry }>
    ) {
      if (!state.history[action.payload.pipelineId]) {
        state.history[action.payload.pipelineId] = [];
      }
      state.history[action.payload.pipelineId].unshift(action.payload.entry);
    },
    setImpactAnalysis(
      state,
      action: PayloadAction<{ decisionId: string; analysis: DecisionImpactAnalysis }>
    ) {
      state.impact[action.payload.decisionId] = action.payload.analysis;
    },
    addComment(
      state,
      action: PayloadAction<{ decisionId: string; comment: DecisionComment }>
    ) {
      const details = state.details[action.payload.decisionId];
      if (details) {
        details.comments = details.comments || [];
        details.comments.push(action.payload.comment);
      }
    },
    setFilters(state, action: PayloadAction<DecisionFilters>) {
      state.filters = action.payload;
    },
    setSelectedDecision(state, action: PayloadAction<string | null>) {
      state.selectedDecisionId = action.payload;
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
  setDecisions,
  updateDecision,
  setDecisionDetails,
  setDecisionHistory,
  addHistoryEntry,
  setImpactAnalysis,
  addComment,
  setFilters,
  setSelectedDecision,
  setLoading,
  setError
} = decisionsSlice.actions;

export default decisionsSlice.reducer;

