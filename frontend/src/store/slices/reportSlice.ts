// store/slices/reportsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Define types
type ReportType = 'quality' | 'insight' | 'performance' | 'summary';
type ReportStatus = 'generating' | 'completed' | 'failed';
type ReportFrequency = 'daily' | 'weekly' | 'monthly';
type ScheduledReportStatus = 'active' | 'paused';

// Define interfaces
interface TimeRange {
  start: string;
  end: string;
}

interface ReportMetadata {
  pipelineId?: string;
  timeRange?: TimeRange;
  filters?: Record<string, any>;
  lastExported?: string;
  exportHistory?: Array<{
    timestamp: string;
    format: string;
    by?: string;
  }>;
  tags?: string[];
  version?: string;
}

interface Report {
  id: string;
  type: ReportType;
  status: ReportStatus;
  createdAt: string;
  completedAt?: string;
  data?: any;
  error?: string;
  metadata: ReportMetadata;
  progress?: number;
  generatedBy?: string;
  lastViewed?: string;
}

interface ScheduledReport {
  id: string;
  reportType: ReportType;
  frequency: ReportFrequency;
  recipients: string[];
  nextRunAt: string;
  lastRunAt?: string;
  status: ScheduledReportStatus;
  configuration: {
    timeRange?: TimeRange;
    filters?: Record<string, any>;
    format?: string;
  };
  metadata: {  // Note: metadata is required with required createdAt and updatedAt
    createdBy?: string;
    createdAt: string;    // Required
    updatedAt: string;    // Required
    description?: string;
  };
}

interface ReportsState {
  activeReports: Record<string, Report>;
  scheduledReports: Record<string, ScheduledReport>;
  generatingReports: string[];
  selectedReportId: string | null;
  error: string | null;
  filters: {
    type?: ReportType[];
    status?: ReportStatus[];
    timeRange?: TimeRange;
  };
}

// Define payload types
interface StartReportGenerationPayload {
  id: string;
  type: ReportType;
  metadata: ReportMetadata;
  generatedBy?: string;
}

interface UpdateReportProgressPayload {
  id: string;
  progress: number;
}

const initialState: ReportsState = {
  activeReports: {},
  scheduledReports: {},
  generatingReports: [],
  selectedReportId: null,
  error: null,
  filters: {}
};

export const reportsSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    // Report Generation
    startReportGeneration(state, action: PayloadAction<StartReportGenerationPayload>) {
      const { id, type, metadata, generatedBy } = action.payload;
      state.activeReports[id] = {
        id,
        type,
        status: 'generating',
        createdAt: new Date().toISOString(),
        metadata,
        generatedBy,
        progress: 0
      };
      state.generatingReports.push(id);
    },

    updateReportProgress(state, action: PayloadAction<UpdateReportProgressPayload>) {
      const { id, progress } = action.payload;
      if (state.activeReports[id]) {
        state.activeReports[id].progress = Math.min(Math.max(progress, 0), 100);
      }
    },

    reportGenerationComplete(
      state,
      action: PayloadAction<{ id: string; data: any; version?: string }>
    ) {
      const { id, data, version } = action.payload;
      const report = state.activeReports[id];
      if (report) {
        report.status = 'completed';
        report.data = data;
        report.completedAt = new Date().toISOString();
        report.progress = 100;
        if (version) {
          report.metadata.version = version;
        }
        state.generatingReports = state.generatingReports.filter(rid => rid !== id);
      }
    },

    reportGenerationFailed(
      state,
      action: PayloadAction<{ id: string; error: string }>
    ) {
      const { id, error } = action.payload;
      if (state.activeReports[id]) {
        state.activeReports[id].status = 'failed';
        state.activeReports[id].error = error;
        state.activeReports[id].progress = 0;
        state.generatingReports = state.generatingReports.filter(rid => rid !== id);
      }
    },

    // Scheduled Reports
    scheduleReport(
      state,
      action: PayloadAction<Omit<ScheduledReport, 'status' | 'lastRunAt' | 'metadata'> & {
        description?: string;
        createdBy?: string;
      }>
    ) {
      const { description, createdBy, ...reportData } = action.payload;
      const timestamp = new Date().toISOString();
      
      const report: ScheduledReport = {
        ...reportData,
        status: 'active',
        metadata: {
          createdAt: timestamp,  // This is required
          updatedAt: timestamp,  // This is required
          createdBy,            // This is optional
          description          // This is optional
        }
      };
      state.scheduledReports[report.id] = report;
    },

    updateScheduledReport(
      state,
      action: PayloadAction<{
        id: string;
        updates: Partial<Omit<ScheduledReport, 'id' | 'metadata'>>;
        description?: string;
      }>
    ) {
      const { id, updates, description } = action.payload;
      const report = state.scheduledReports[id];
      if (report) {
        state.scheduledReports[id] = {
          ...report,
          ...updates,
          metadata: {
            ...report.metadata,
            updatedAt: new Date().toISOString(),
            description: description ?? report.metadata?.description
          }
        };
      }
    },

    removeScheduledReport(state, action: PayloadAction<string>) {
      delete state.scheduledReports[action.payload];
    },

    // Report Management
    setSelectedReport(state, action: PayloadAction<string | null>) {
      state.selectedReportId = action.payload;
      if (action.payload && state.activeReports[action.payload]) {
        state.activeReports[action.payload].lastViewed = new Date().toISOString();
      }
    },

    deleteReport(state, action: PayloadAction<string>) {
      const id = action.payload;
      delete state.activeReports[id];
      if (state.selectedReportId === id) {
        state.selectedReportId = null;
      }
    },

    clearAllReports(state) {
      state.activeReports = {};
      state.selectedReportId = null;
    },

    // Export Management
    markReportAsExported(
      state,
      action: PayloadAction<{ id: string; format: string; by?: string }>
    ) {
      const { id, format, by } = action.payload;
      const report = state.activeReports[id];
      if (report) {
        const exportRecord = {
          timestamp: new Date().toISOString(),
          format,
          by
        };
        report.metadata = {
          ...report.metadata,
          lastExported: exportRecord.timestamp,
          exportHistory: [
            ...(report.metadata.exportHistory || []),
            exportRecord
          ]
        };
      }
    },

    // Error Handling
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },

    clearError(state) {
      state.error = null;
    },

    // Filters
    setReportFilters(state, action: PayloadAction<ReportsState['filters']>) {
      state.filters = action.payload;
    },

    clearFilters(state) {
      state.filters = {};
    }
  }
});

// Export actions
export const {
  startReportGeneration,
  updateReportProgress,
  reportGenerationComplete,
  reportGenerationFailed,
  scheduleReport,
  updateScheduledReport,
  removeScheduledReport,
  setSelectedReport,
  deleteReport,
  clearAllReports,
  markReportAsExported,
  setError,
  clearError,
  setReportFilters,
  clearFilters
} = reportsSlice.actions;

// Selectors
export const selectAllReports = (state: RootState) => 
  Object.values(state.reports.activeReports);

export const selectFilteredReports = (state: RootState) => {
  const reports = Object.values(state.reports.activeReports);
  const filters = state.reports.filters;

  return reports.filter(report => {
    const matchesType = !filters.type?.length || 
      filters.type.includes(report.type);
    const matchesStatus = !filters.status?.length || 
      filters.status.includes(report.status);
    
    if (filters.timeRange) {
      const reportTime = new Date(report.createdAt).getTime();
      const startTime = new Date(filters.timeRange.start).getTime();
      const endTime = new Date(filters.timeRange.end).getTime();
      return matchesType && matchesStatus && 
        reportTime >= startTime && reportTime <= endTime;
    }
    
    return matchesType && matchesStatus;
  });
};

export const selectReportById = (id: string) => 
  (state: RootState) => state.reports.activeReports[id];

export const selectGeneratingReports = (state: RootState) => 
  state.reports.generatingReports;

export const selectScheduledReports = (state: RootState) => 
  Object.values(state.reports.scheduledReports);

export const selectActiveScheduledReports = (state: RootState) =>
  Object.values(state.reports.scheduledReports)
    .filter(report => report.status === 'active');

export const selectSelectedReport = (state: RootState) => 
  state.reports.selectedReportId 
    ? state.reports.activeReports[state.reports.selectedReportId]
    : null;

export const selectReportsError = (state: RootState) => 
  state.reports.error;

export const selectReportFilters = (state: RootState) =>
  state.reports.filters;

export default reportsSlice.reducer;