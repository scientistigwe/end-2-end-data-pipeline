// store/slices/monitoringSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Define types
type Severity = 'high' | 'medium' | 'low';
type SystemHealthStatus = 'healthy' | 'warning' | 'critical';
type MetricType = 'latency' | 'throughput' | 'error_rate' | 'cpu_usage' | 'memory_usage' | 'custom';

// Define interfaces
interface Metric {
  timestamp: string;
  value: number;
  unit?: string;
  metadata?: Record<string, any>;
}

interface Alert {
  id: string;
  type: string;
  severity: Severity;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  resolvedAt?: string;
  metadata?: Record<string, any>;
}

interface SystemHealthMetrics {
  cpu: number;
  memory: number;
  disk: number;
  network: number;
  lastUpdated: string;
}

interface MonitoringState {
  metrics: Record<string, Metric[]>;
  alerts: Alert[];
  systemHealth: {
    status: SystemHealthStatus;
    metrics: SystemHealthMetrics;
    lastIncident?: string;
  };
  thresholds: Record<string, {
    warning: number;
    critical: number;
  }>;
}

// Define payload interfaces
interface UpdateMetricsPayload {
  metricKey: string;
  value: number;
  unit?: string;
  metadata?: Record<string, any>;
}

interface AddAlertPayload {
  type: string;
  severity: Severity;
  message: string;
  metadata?: Record<string, any>;
}

interface UpdateSystemHealthPayload {
  metrics: Partial<SystemHealthMetrics>;
}

interface UpdateThresholdPayload {
  metricKey: string;
  warning: number;
  critical: number;
}

const initialSystemHealthMetrics: SystemHealthMetrics = {
  cpu: 0,
  memory: 0,
  disk: 0,
  network: 0,
  lastUpdated: new Date().toISOString()
};

const initialState: MonitoringState = {
  metrics: {},
  alerts: [],
  systemHealth: {
    status: 'healthy',
    metrics: initialSystemHealthMetrics
  },
  thresholds: {}
};

export const monitoringSlice = createSlice({
  name: 'monitoring',
  initialState,
  reducers: {
    updateMetrics(state, action: PayloadAction<UpdateMetricsPayload>) {
      const { metricKey, value, unit, metadata } = action.payload;
      if (!state.metrics[metricKey]) {
        state.metrics[metricKey] = [];
      }
      
      // Keep only last 100 data points
      if (state.metrics[metricKey].length >= 100) {
        state.metrics[metricKey].shift();
      }
      
      state.metrics[metricKey].push({
        timestamp: new Date().toISOString(),
        value,
        unit,
        metadata
      });
    },

    addAlert(state, action: PayloadAction<AddAlertPayload>) {
      const alert: Alert = {
        id: Date.now().toString(),
        ...action.payload,
        timestamp: new Date().toISOString(),
        acknowledged: false
      };
      state.alerts.push(alert);
    },

    acknowledgeAlert(state, action: PayloadAction<string>) {
      const alert = state.alerts.find(a => a.id === action.payload);
      if (alert) {
        alert.acknowledged = true;
      }
    },

    resolveAlert(state, action: PayloadAction<string>) {
      const alert = state.alerts.find(a => a.id === action.payload);
      if (alert) {
        alert.resolvedAt = new Date().toISOString();
      }
    },

    updateSystemHealth(state, action: PayloadAction<UpdateSystemHealthPayload>) {
      const { metrics } = action.payload;
      state.systemHealth.metrics = {
        ...state.systemHealth.metrics,
        ...metrics,
        lastUpdated: new Date().toISOString()
      };

      // Update system status based on thresholds
      const cpuCritical = state.systemHealth.metrics.cpu > 90;
      const memCritical = state.systemHealth.metrics.memory > 90;
      const diskCritical = state.systemHealth.metrics.disk > 90;

      if (cpuCritical || memCritical || diskCritical) {
        state.systemHealth.status = 'critical';
        state.systemHealth.lastIncident = new Date().toISOString();
      } else if (state.systemHealth.metrics.cpu > 70 || 
                 state.systemHealth.metrics.memory > 70 || 
                 state.systemHealth.metrics.disk > 70) {
        state.systemHealth.status = 'warning';
      } else {
        state.systemHealth.status = 'healthy';
      }
    },

    updateThreshold(state, action: PayloadAction<UpdateThresholdPayload>) {
      state.thresholds[action.payload.metricKey] = {
        warning: action.payload.warning,
        critical: action.payload.critical
      };
    }
  }
});

// Export actions
export const {
  updateMetrics,
  addAlert,
  acknowledgeAlert,
  resolveAlert,
  updateSystemHealth,
  updateThreshold
} = monitoringSlice.actions;

// Selectors
export const selectMetrics = (state: RootState) => state.monitoring.metrics;
export const selectMetricByKey = (key: string) => 
  (state: RootState) => state.monitoring.metrics[key] || [];
export const selectAlerts = (state: RootState) => state.monitoring.alerts;
export const selectActiveAlerts = (state: RootState) => 
  state.monitoring.alerts.filter(alert => !alert.resolvedAt);
export const selectSystemHealth = (state: RootState) => state.monitoring.systemHealth;
export const selectThresholds = (state: RootState) => state.monitoring.thresholds;

export default monitoringSlice.reducer;