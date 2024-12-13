// src/analysis/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/rootReducer';

export const selectActiveAnalyses = (state: RootState) => 
  state.analysis.activeAnalyses;

export const selectQualityReports = (state: RootState) => 
  state.analysis.qualityReports;

export const selectInsightReports = (state: RootState) => 
  state.analysis.insightReports;

export const selectSelectedAnalysisId = (state: RootState) => 
  state.analysis.selectedAnalysisId;

export const selectSelectedAnalysis = createSelector(
  [selectActiveAnalyses, selectSelectedAnalysisId],
  (analyses, selectedId) => selectedId ? analyses[selectedId] : null
);

export const selectSelectedQualityReport = createSelector(
  [selectQualityReports, selectSelectedAnalysisId],
  (reports, selectedId) => selectedId ? reports[selectedId] : null
);

export const selectSelectedInsightReport = createSelector(
  [selectInsightReports, selectSelectedAnalysisId],
  (reports, selectedId) => selectedId ? reports[selectedId] : null
);