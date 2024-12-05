// src/store/decisions/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../types';

export const selectDecisions = (state: RootState) => 
  state.decisions.decisions;

export const selectDecisionDetails = (state: RootState) => 
  state.decisions.details;

export const selectDecisionHistory = (state: RootState) => 
  state.decisions.history;

export const selectImpactAnalyses = (state: RootState) => 
  state.decisions.impact;

export const selectFilters = (state: RootState) => 
  state.decisions.filters;

export const selectSelectedDecisionId = (state: RootState) => 
  state.decisions.selectedDecisionId;

export const selectFilteredDecisions = createSelector(
  [selectDecisions, selectFilters],
  (decisions, filters) => {
    return Object.values(decisions).filter(decision => {
      if (filters.types && !filters.types.includes(decision.type)) return false;
      if (filters.status && !filters.status.includes(decision.status)) return false;
      if (filters.urgency && !filters.urgency.includes(decision.urgency)) return false;
      if (filters.assignedTo && decision.assignedTo) {
        if (!decision.assignedTo.some(user => filters.assignedTo?.includes(user))) {
          return false;
        }
      }
      if (filters.dateRange) {
        const decisionDate = new Date(decision.createdAt);
        const start = new Date(filters.dateRange.start);
        const end = new Date(filters.dateRange.end);
        if (decisionDate < start || decisionDate > end) return false;
      }
      return true;
    });
  }
);