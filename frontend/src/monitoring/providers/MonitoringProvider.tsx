// src/monitoring/providers/MonitoringProvider.tsx
import React, { useState, useCallback } from "react";
import { useDispatch } from "react-redux";
import { MonitoringContext } from "../context/MonitoringContext";
import { MonitoringService } from "../services/monitoringService";
import { handleApiError } from "../../common/utils/api/apiUtils";
import { MONITORING_MESSAGES } from "../constants";
import {
  setMetrics,
  setSystemHealth,
  setAlerts,
  setResources,
  setLoading,
  setError,
} from "../store/monitoringSlice";
import type {
  MetricsData,
  SystemHealth,
  ResourceUsage,
  Alert,
  MonitoringConfig,
  AlertConfig,
} from "../types/metrics";

interface MonitoringProviderProps {
  children: React.ReactNode;
  pipelineId: string;
}

export const MonitoringProvider: React.FC<MonitoringProviderProps> = ({
  children,
  pipelineId,
}) => {
  const dispatch = useDispatch();

  // State
  const [metrics, setMetricsState] = useState<MetricsData | null>(null);
  const [health, setHealthState] = useState<SystemHealth | null>(null);
  const [resources, setResourcesState] = useState<ResourceUsage | null>(null);
  const [alerts, setAlertsState] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<Error | null>(null);

  // Actions
  const startMonitoring = useCallback(
    async (config: MonitoringConfig) => {
      setIsLoading(true);
      dispatch(setLoading(true));

      try {
        await MonitoringService.startMonitoring(pipelineId, config);
        await refreshAll();
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        const errorMessage = MONITORING_MESSAGES.ERRORS.START_FAILED;
        setErrorState(new Error(errorMessage));
        dispatch(setError(errorMessage));
      } finally {
        setIsLoading(false);
        dispatch(setLoading(false));
      }
    },
    [dispatch, pipelineId]
  );

  const configureAlerts = useCallback(
    async (config: AlertConfig) => {
      try {
        await MonitoringService.configureAlerts(pipelineId, config);
        const alerts = await MonitoringService.getAlertHistory(pipelineId);
        setAlertsState(alerts);
        dispatch(setAlerts(alerts));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_CONFIG_FAILED);
      }
    },
    [dispatch, pipelineId]
  );

  const acknowledgeAlert = useCallback(
    async (alertId: string) => {
      try {
        await MonitoringService.acknowledgeAlert(pipelineId, alertId);
        const alerts = await MonitoringService.getAlertHistory(pipelineId);
        setAlertsState(alerts);
        dispatch(setAlerts(alerts));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_ACKNOWLEDGE_FAILED);
      }
    },
    [dispatch, pipelineId]
  );

  const resolveAlert = useCallback(
    async (
      alertId: string,
      resolution?: { comment?: string; action?: string }
    ) => {
      try {
        await MonitoringService.resolveAlert(pipelineId, alertId, resolution);
        const alerts = await MonitoringService.getAlertHistory(pipelineId);
        setAlertsState(alerts);
        dispatch(setAlerts(alerts));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_RESOLVE_FAILED);
      }
    },
    [dispatch, pipelineId]
  );

  const refreshAll = useCallback(async () => {
    setIsLoading(true);
    try {
      const [metricsData, healthData, resourcesData, alertsData] =
        await Promise.all([
          MonitoringService.getMetrics(pipelineId),
          MonitoringService.getHealth(pipelineId),
          MonitoringService.getResourceUsage(pipelineId),
          MonitoringService.getAlertHistory(pipelineId),
        ]);

      setMetricsState(metricsData);
      setHealthState(healthData);
      setResourcesState(resourcesData);
      setAlertsState(alertsData);

      dispatch(setMetrics(metricsData));
      dispatch(setSystemHealth(healthData));
      dispatch(setResources(resourcesData));
      dispatch(setAlerts(alertsData));

      setErrorState(null);
    } catch (err) {
      handleApiError(err);
      const errorMessage = "Failed to refresh monitoring data";
      setErrorState(new Error(errorMessage));
      dispatch(setError(errorMessage));
    } finally {
      setIsLoading(false);
    }
  }, [dispatch, pipelineId]);

  const clearError = useCallback(() => {
    setErrorState(null);
    dispatch(setError(null));
  }, [dispatch]);

  const value = {
    // State
    metrics,
    health,
    resources,
    alerts,
    isLoading,
    error,

    // Actions
    startMonitoring,
    configureAlerts,
    acknowledgeAlert,
    resolveAlert,
    refreshAll,
    clearError,
  };

  return (
    <MonitoringContext.Provider value={value}>
      {children}
    </MonitoringContext.Provider>
  );
};
