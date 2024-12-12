// src/decisions/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/rootReducer';
import type { Decision, DecisionFilters, DecisionHistoryEntry, DecisionDetails } from '@/decisions/types/decisions';

// Base selectors with type assertions
const selectDecisionsState = (state: RootState) => state.decisions;

export const selectDecisions = createSelector(
  [selectDecisionsState],
  (decisionsState): Record<string, Decision> => decisionsState.decisions
);

export const selectDecisionHistory = createSelector(
  [selectDecisionsState],
  (decisionsState): DecisionHistoryEntry[] => decisionsState.history
);

export const selectFilters = createSelector(
  [selectDecisionsState],
  (decisionsState): DecisionFilters => decisionsState.filters
);

export const selectSelectedDecisionId = createSelector(
  [selectDecisionsState],
  (decisionsState): string | null => decisionsState.selectedDecisionId
);

// Memoized selectors
export const selectFilteredDecisions = createSelector(
  [selectDecisions, selectFilters],
  (decisions, filters): Decision[] => {
    return Object.values(decisions).filter((decision: Decision) => {
      if (!passesFilter(decision, filters)) {
        return false;
      }
      return true;
    });
  }
);

// Helper function to check if a decision passes all filters
const passesFilter = (decision: Decision, filters: DecisionFilters): boolean => {
  if (filters.types?.length && !filters.types.includes(decision.type)) {
    return false;
  }
  
  if (filters.status?.length && !filters.status.includes(decision.status)) {
    return false;
  }
  
  if (filters.urgency?.length && !filters.urgency.includes(decision.urgency)) {
    return false;
  }
  
  if (filters.assignedTo?.length && decision.assignedTo) {
    if (!decision.assignedTo.some(user => filters.assignedTo?.includes(user))) {
      return false;
    }
  }
  
  if (filters.dateRange) {
    const decisionDate = new Date(decision.createdAt); // Using createdAt from Decision interface
    const start = new Date(filters.dateRange.start);
    const end = new Date(filters.dateRange.end);
    if (decisionDate < start || decisionDate > end) {
      return false;
    }
  }
  
  return true;
};

// Selected decision selectors
export const selectSelectedDecision = createSelector(
  [selectDecisions, selectSelectedDecisionId],
  (decisions, selectedId): Decision | null => 
    selectedId ? decisions[selectedId] : null
);

// Helper selectors for specific decision data
export const selectDecisionOptions = createSelector(
  [selectSelectedDecision],
  (decision): Decision['options'] => decision?.options ?? []
);

export const selectDecisionContext = createSelector(
  [selectSelectedDecision],
  (decision): Decision['context'] => decision?.context ?? {}
);

export const selectDecisionAnalysis = createSelector(
  [selectSelectedDecision],
  (decision) => (decision as DecisionDetails)?.analysis ?? null
);

export const selectDecisionComments = createSelector(
  [selectSelectedDecision],
  (decision) => (decision as DecisionDetails)?.comments ?? []
);

export const selectSelectedDecisionHistory = createSelector(
  [selectDecisionHistory, selectSelectedDecisionId],
  (history, selectedId): DecisionHistoryEntry[] => 
    history.filter((record: DecisionHistoryEntry) => record.decisionId === selectedId)
);