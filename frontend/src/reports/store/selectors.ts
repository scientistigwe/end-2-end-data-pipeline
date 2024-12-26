// src/report/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store/rootReducer';
import type { Report, ReportMetadata, ReportStatus, ScheduleConfig } from '../types/models';
import type { reportState } from './reportSlice';

// Base selectors with proper state path and typing
export const selectReportState = (state: RootState): reportState => 
  state.reports;

export const selectReports = (state: RootState): Record<string, Report> => 
  state.reports?.reports || {};

export const selectMetadata = (state: RootState): Record<string, ReportMetadata> => 
  state.reports?.metadata || {};

export const selectSchedules = (state: RootState): Record<string, ScheduleConfig> => 
  state.reports?.schedules || {};

export const selectSelectedReportId = (state: RootState): string | null => 
  state.reports?.selectedReportId || null;

export const selectFilters = (state: RootState): reportState['filters'] => 
  state.reports?.filters || {};

export const selectIsLoading = (state: RootState): boolean => 
  state.reports?.isLoading || false;

export const selectError = (state: RootState): string | null => 
  state.reports?.error || null;

// Derived selectors
export const selectReportsList = createSelector(
  selectReports,
  (reports): Report[] => Object.values(reports)
);

export const selectSelectedReport = createSelector(
  [selectReports, selectSelectedReportId],
  (reports, selectedId): Report | null => 
    selectedId ? reports[selectedId] || null : null
);

export const selectSelectedReportMetadata = createSelector(
  [selectMetadata, selectSelectedReportId],
  (metadata, selectedId): ReportMetadata | null =>
    selectedId ? metadata[selectedId] || null : null
);

export const selectSelectedReportSchedule = createSelector(
  [selectSchedules, selectSelectedReportId],
  (schedules, selectedId): ScheduleConfig | null =>
    selectedId ? schedules[selectedId] || null : null
);

export const selectFilteredReports = createSelector(
  [selectReportsList, selectFilters],
  (reports, filters): Report[] => {
    if (!filters) return reports;
    
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
  (reports): Record<ReportStatus, Report[]> => {
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
  (reports): {
    total: number;
    completed: number;
    failed: number;
    generating: number;
    success_rate: number;
  } => ({
    total: reports.length,
    completed: reports.filter(r => r.status === 'completed').length,
    failed: reports.filter(r => r.status === 'failed').length,
    generating: reports.filter(r => r.status === 'generating').length,
    success_rate: reports.length > 0
      ? (reports.filter(r => r.status === 'completed').length / reports.length) * 100
      : 0
  })
);

// Additional useful selectors
export const selectReportById = (id: string) => createSelector(
  selectReports,
  (reports): Report | null => reports[id] || null
);

export const selectReportMetadataById = (id: string) => createSelector(
  selectMetadata,
  (metadata): ReportMetadata | null => metadata[id] || null
);

export const selectReportScheduleById = (id: string) => createSelector(
  selectSchedules,
  (schedules): ScheduleConfig | null => schedules[id] || null
);