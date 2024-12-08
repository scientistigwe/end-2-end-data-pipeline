// src/store/reports/reportsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { Report, ReportMetadata } from '../../types/report';
import { MonitoringState } from '../../monitoring/store/monitoringSlice'
interface ReportsState {
  reports: Record<string, Report>;
  metadata: Record<string, ReportMetadata>;
  selectedReportId: string | null;
  isLoading: boolean;
  error: string | null;
  monitoring: MonitoringState;
  activeReport: string | null;

}

const initialState: ReportsState = {
  reports: {},
  metadata: {},
  selectedReportId: null,
  isLoading: false,
  error: null
};

const reportsSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    setReports(state, action: PayloadAction<Report[]>) {
      state.reports = action.payload.reduce((acc, report) => {
        acc[report.id] = report;
        return acc;
      }, {} as Record<string, Report>);
    },
    addReport(state, action: PayloadAction<Report>) {
      state.reports[action.payload.id] = action.payload;
    },
    updateReport(state, action: PayloadAction<Partial<Report> & { id: string }>) {
      const { id, ...changes } = action.payload;
      if (state.reports[id]) {
        state.reports[id] = { ...state.reports[id], ...changes };
      }
    },
    removeReport(state, action: PayloadAction<string>) {
      delete state.reports[action.payload];
    },
    setReportMetadata(
      state,
      action: PayloadAction<{ id: string; metadata: ReportMetadata }>
    ) {
      state.metadata[action.payload.id] = action.payload.metadata;
    },
    setSelectedReport(state, action: PayloadAction<string | null>) {
      state.selectedReportId = action.payload;
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
  setReports,
  addReport,
  updateReport,
  removeReport,
  setReportMetadata,
  setSelectedReport,
  setLoading,
  setError
} = reportsSlice.actions;

export default reportsSlice.reducer;

