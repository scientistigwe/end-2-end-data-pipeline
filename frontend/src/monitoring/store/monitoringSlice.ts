// src/store/monitoring/monitoringSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { 
  Alert,
  ResourceUsage 
} from '../types/monitoring';

export type AlertSeverity = 'low' | 'medium' | 'high';
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface MetricsData {
  value: number;
  timestamp: string;
  type: string;
  labels?: Record<string, string>;
}

export interface SystemHealth {
  status: HealthStatus;
  message?: string;
  lastChecked: string;
  components?: Record<string, {
    status: HealthStatus;
    message?: string;
  }>;
}


export interface MonitoringState {
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

export interface ResourceUsage {
  cpu: {
    usage: number;
    limit: number;
  };
  memory: {
    usage: number;
    limit: number;
  };
  disk: {
    usage: number;
    limit: number;
  };
  timestamp: string;
}

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
  MonitoringState,
  setMetrics,
  setSystemHealth,
  setAlerts,
  addAlert,
  setResources,
  setLoading,
  setError
} = monitoringSlice.actions;

export default monitoringSlice.reducer;

