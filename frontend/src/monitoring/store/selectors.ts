// src/store/monitoring/selectors.ts
import type { RootState } from '../../../../store/index';

export const selectMetrics = (state: RootState) => state.monitoring.metrics;
export const selectSystemHealth = (state: RootState) => state.monitoring.systemHealth;
export const selectAlerts = (state: RootState) => state.monitoring.alerts;
export const selectResources = (state: RootState) => state.monitoring.resources;
export const selectIsLoading = (state: RootState) => state.monitoring.isLoading;
export const selectError = (state: RootState) => state.monitoring.error;