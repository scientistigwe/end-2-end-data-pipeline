// src/report/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store';
import type { Report, ReportMetadata, ReportStatus } from '../types/report';

// Base selectors
export const selectReportState = (state: RootState) => state.report;
export const selectReports = (state: RootState) => state.report.reports;
export const selectMetadata = (state: RootState) => state.report.metadata;
export const selectSchedules = (state: RootState) => state.report.schedules;
export const selectSelectedReportId = (state: RootState) => 
  state.report.selectedReportId;
export const selectFilters = (state: RootState) => state.report.filters;

// Derived selectors
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
  [selectMetadata, selectSelectedReportId],
  (metadata, selectedId): ReportMetadata | null =>
    selectedId ? metadata[selectedId] ?? null : null
);

export const selectFilteredReports = createSelector(
  [selectReportsList, selectFilters],
  (reports, filters) => {
    return reports.filter(report => {
      if (filters.type?.length && !filters.type.includes(report.config.type)) {
        return false;
      }
      if (filters.status?.length && !filters.status.includes(report.status)) {
        return false;
      }
      if (filters.dateRange) {
        const reportDate = new Date(report.createdAt);
        const start = new Date(filters.dateRange.start);
        const end = new Date(filters.dateRange.end);
        if (reportDate < start || reportDate > end) {
          return false;
        }
      }
      return true;
    });
  }
);

export const selectReportsByStatus = createSelector(
  selectReportsList,
  (reports) => {
    return reports.reduce((acc, report) => {
      if (!acc[report.status]) {
        acc[report.status] = [];
      }
      acc[report.status].push(report);
      return acc;
    }, {} as Record<ReportStatus, Report[]>);
  }
);

export const selectReportStats = createSelector(
  selectReportsList,
  (reports) => ({
    total: reports.length,
    completed: reports.filter(r => r.status === 'completed').length,
    failed: reports.filter(r => r.status === 'failed').length,
    generating: reports.filter(r => r.status === 'generating').length,
    success_rate: reports.length > 0
      ? (reports.filter(r => r.status === 'completed').length / reports.length) * 100
      : 0
  })
);
