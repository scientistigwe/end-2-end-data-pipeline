// src/monitoring/store/monitoringSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { 
  MonitoringState,
  MetricsData,
  SystemHealth,
  ResourceUsage,
  Alert,
  TimeRange,
  MonitoringFilters
} from '../types/monitoring';

const initialState: MonitoringState = {
  metrics: null,
  systemHealth: null,
  alerts: [],
  resources: null,
  selectedTimeRange: '1h',
  filters: {},
  isLoading: false,
  error: null
};

const monitoringSlice = createSlice({
  name: 'monitoring',
  initialState,
  reducers: {
    setMetrics(state, action: PayloadAction<MetricsData[]>) {
      state.metrics = action.payload;
    },
    setSystemHealth(state, action: PayloadAction<SystemHealth>) {
      state.systemHealth = action.payload;
    },
    setAlerts(state, action: PayloadAction<Alert[]>) {
      state.alerts = action.payload;
    },
    addAlert(state, action: PayloadAction<Alert>) {
      state.alerts.unshift(action.payload);
    },
    updateAlert(state, action: PayloadAction<Alert>) {
      const index = state.alerts.findIndex(alert => alert.id === action.payload.id);
      if (index !== -1) {
        state.alerts[index] = action.payload;
      }
    },
    setResources(state, action: PayloadAction<ResourceUsage>) {
      state.resources = action.payload;
    },
    setTimeRange(state, action: PayloadAction<TimeRange>) {
      state.selectedTimeRange = action.payload;
    },
    setFilters(state, action: PayloadAction<MonitoringFilters>) {
      state.filters = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload ? new Error(action.payload) : null;
    },
    clearState(state) {
      Object.assign(state, initialState);
    }
  }
});

export const {
  setMetrics,
  setSystemHealth,
  setAlerts,
  addAlert,
  updateAlert,
  setResources,
  setTimeRange,
  setFilters,
  setLoading,
  setError,
  clearState
} = monitoringSlice.actions;

export type monitoringState = typeof initialState;
export default monitoringSlice.reducer;

