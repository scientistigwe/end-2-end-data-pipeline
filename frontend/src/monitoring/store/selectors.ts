// src/monitoring/store/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store/store';
import type { MetricsData, Alert, MetricStatus } from '../types/metrics';

// Basic selectors
export const selectMetrics = (state: RootState) => state.monitoring.metrics;
export const selectSystemHealth = (state: RootState) => state.monitoring.systemHealth;
export const selectAlerts = (state: RootState) => state.monitoring.alerts;
export const selectResources = (state: RootState) => state.monitoring.resources;
export const selectTimeRange = (state: RootState) => state.monitoring.selectedTimeRange;
export const selectFilters = (state: RootState) => state.monitoring.filters;
export const selectIsLoading = (state: RootState) => state.monitoring.isLoading;
export const selectError = (state: RootState) => state.monitoring.error;

// Memoized selectors
export const selectFilteredMetrics = createSelector(
  [selectMetrics, selectFilters],
  (metrics, filters) => {
    if (!metrics) return [];
    
    return metrics.filter(metric => {
      if (filters.metricTypes?.length && !filters.metricTypes.includes(metric.type)) {
        return false;
      }
      if (filters.status?.length && !filters.status.includes(metric.status)) {
        return false;
      }
      if (filters.search) {
        const search = filters.search.toLowerCase();
        return metric.type.toLowerCase().includes(search);
      }
      return true;
    });
  }
);

export const selectActiveAlerts = createSelector(
  [selectAlerts],
  (alerts) => alerts.filter(alert => !alert.resolved)
);

export const selectAlertsBySeverity = createSelector(
  [selectAlerts],
  (alerts) => {
    return alerts.reduce((acc, alert) => {
      if (!acc[alert.severity]) {
        acc[alert.severity] = [];
      }
      acc[alert.severity].push(alert);
      return acc;
    }, {} as Record<string, Alert[]>);
  }
);

export const selectSystemStatus = createSelector(
  [selectSystemHealth, selectActiveAlerts],
  (health, activeAlerts): MetricStatus => {
    if (!health) return 'critical';
    if (activeAlerts.some(alert => alert.severity === 'critical')) {
      return 'critical';
    }
    if (activeAlerts.some(alert => alert.severity === 'warning')) {
      return 'warning';
    }
    return health.status;
  }
);