// src/monitoring/context/MonitoringContext.tsx
import { createContext, useContext } from 'react';
import type {
  MetricsData,
  SystemHealth,
  ResourceUsage,
  Alert,
  MonitoringConfig,
  AlertConfig
} from '../types/monitoring';

interface MonitoringContextValue {
  // State
  metrics: MetricsData | null;
  health: SystemHealth | null;
  resources: ResourceUsage | null;
  alerts: Alert[];
  isLoading: boolean;
  error: Error | null;

  // Actions
  startMonitoring: (config: MonitoringConfig) => Promise<void>;
  configureAlerts: (config: AlertConfig) => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<void>;
  resolveAlert: (alertId: string, resolution?: { comment?: string; action?: string }) => Promise<void>;
  refreshAll: () => Promise<void>;
  clearError: () => void;
}

export const MonitoringContext = createContext<MonitoringContextValue | undefined>(undefined);

export const useMonitoringContext = () => {
  const context = useContext(MonitoringContext);
  if (!context) {
    throw new Error('useMonitoringContext must be used within a MonitoringProvider');
  }
  return context;
};