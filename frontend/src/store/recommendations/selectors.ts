// src/store/recommendations/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../types';

export const selectRecommendations = (state: RootState) => 
  state.recommendations.recommendations;

export const selectRecommendationHistory = (state: RootState) => 
  state.recommendations.history;

export const selectFilters = (state: RootState) => 
  state.recommendations.filters;

export const selectSelectedRecommendationId = (state: RootState) =>
  state.recommendations.selectedRecommendationId;

export const selectFilteredRecommendations = createSelector(
  [selectRecommendations, selectFilters],
  (recommendations, filters) => {
    return Object.values(recommendations).filter(rec => {
      if (filters.types && !filters.types.includes(rec.type)) return false;
      if (filters.impact && !filters.impact.includes(rec.impact)) return false;
      if (filters.status && !filters.status.includes(rec.status)) return false;
      if (filters.minConfidence && rec.confidence < filters.minConfidence) return false;
      return true;
    });
  }
);
