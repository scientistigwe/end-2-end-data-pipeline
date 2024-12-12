// src/report/store/reportSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  Report,
  ReportMetadata,
  ReportStatus,
  ScheduleConfig
} from '../types/report';

interface ReportState {
  reports: Record<string, Report>;
  metadata: Record<string, ReportMetadata>;
  schedules: Record<string, ScheduleConfig>;
  selectedReportId: string | null;
  filters: {
    type?: string[];
    status?: ReportStatus[];
    dateRange?: {
      start: string;
      end: string;
    };
  };
  isLoading: boolean;
  error: string | null;
}

const initialState: ReportState = {
  reports: {},
  metadata: {},
  schedules: {},
  selectedReportId: null,
  filters: {},
  isLoading: false,
  error: null
};

const reportSlice = createSlice({
  name: 'report',
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
      delete state.metadata[action.payload];
      delete state.schedules[action.payload];
    },

    setReportMetadata(
      state,
      action: PayloadAction<{ id: string; metadata: ReportMetadata }>
    ) {
      state.metadata[action.payload.id] = action.payload.metadata;
    },

    setReportSchedule(
      state,
      action: PayloadAction<{ id: string; schedule: ScheduleConfig }>
    ) {
      state.schedules[action.payload.id] = action.payload.schedule;
    },

    updateReportStatus(
      state,
      action: PayloadAction<{ id: string; status: ReportStatus; error?: string }>
    ) {
      const { id, status, error } = action.payload;
      if (state.reports[id]) {
        state.reports[id].status = status;
        if (error) {
          state.reports[id].error = error;
        }
      }
    },

    setSelectedReport(state, action: PayloadAction<string | null>) {
      state.selectedReportId = action.payload;
    },

    setFilters(state, action: PayloadAction<ReportState['filters']>) {
      state.filters = action.payload;
    },

    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },

    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },

    resetReportState(state) {
      Object.assign(state, initialState);
    }
  }
});

export const {
  setReports,
  addReport,
  updateReport,
  removeReport,
  setReportMetadata,
  setReportSchedule,
  updateReportStatus,
  setSelectedReport,
  setFilters,
  setLoading,
  setError,
  resetReportState
} = reportSlice.actions;

export type reportState = typeof initialState;
export default reportSlice.reducer;


