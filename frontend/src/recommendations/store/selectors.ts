// src/recommendations/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store/rootReducer';

export const selectRecommendations = (state: RootState) => 
  Object.values(state.recommendations.recommendations);

export const selectRecommendationById = (id: string) => 
  createSelector(
    [(state: RootState) => state.recommendations.recommendations],
    (recommendations) => recommendations[id]
  );

export const selectRecommendationHistory = (state: RootState) => 
  state.recommendations.history;

export const selectRecommendationFilters = (state: RootState) => 
  state.recommendations.filters;

export const selectIsLoading = (state: RootState) => 
  state.recommendations.isLoading;

export const selectError = (state: RootState) => 
  state.recommendations.error;

