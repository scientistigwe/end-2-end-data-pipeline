// src/store/reports/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../../../store/index';
import type { Report, ReportMetadata } from '../../types/report';

export const selectReports = (state: RootState) => state.reports.reports;
export const selectReportMetadata = (state: RootState) => state.reports.metadata;
export const selectSelectedReportId = (state: RootState) => 
  state.reports.selectedReportId;
export const selectIsLoading = (state: RootState) => state.reports.isLoading;
export const selectError = (state: RootState) => state.reports.error;

export const selectReportsList = createSelector(
  selectReports,
  (reports): Report[] => Object.values(reports)
);

export const selectSelectedReport = createSelector(
  [selectReports, selectSelectedReportId],
  (reports, selectedId): Report | null => 
    selectedId ? reports[selectedId] ?? null : null
);

export const selectSelectedReportMetadata = createSelector(
  [selectReportMetadata, selectSelectedReportId],
  (metadata, selectedId): ReportMetadata | null =>
    selectedId ? metadata[selectedId] ?? null : null
);