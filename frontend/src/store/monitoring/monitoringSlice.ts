// src/store/monitoring/monitoringSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { 
  MetricsData, 
  SystemHealth, 
  Alert,
  ResourceUsage 
} from '../../types/monitoring';

interface MonitoringState {
  metrics: MetricsData | null;
  systemHealth: SystemHealth | null;
  alerts: Alert[];
  resources: ResourceUsage | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: MonitoringState = {
  metrics: null,
  systemHealth: null,
  alerts: [],
  resources: null,
  isLoading: false,
  error: null
};

const monitoringSlice = createSlice({
  name: 'monitoring',
  initialState,
  reducers: {
    setMetrics(state, action: PayloadAction<MetricsData>) {
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
    setResources(state, action: PayloadAction<ResourceUsage>) {
      state.resources = action.payload;
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
  setMetrics,
  setSystemHealth,
  setAlerts,
  addAlert,
  setResources,
  setLoading,
  setError
} = monitoringSlice.actions;

export default monitoringSlice.reducer;

