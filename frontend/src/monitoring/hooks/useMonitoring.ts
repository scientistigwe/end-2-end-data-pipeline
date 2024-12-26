// src/monitoring/hooks/useMonitoring.ts
import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { MonitoringService } from '../services/monitoringService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { MONITORING_CONFIG, MONITORING_MESSAGES } from '../constants';
import {
  setMetrics,
  setSystemHealth,
  setAlerts,
  addAlert,
  setResources,
  setError,
  setLoading
} from '../store/monitoringSlice';
import type {
  MonitoringConfig,
  AlertConfig,
  MetricsData
} from '../types/metrics';

interface UseMonitoringOptions {
  pipelineId: string;
  metricsInterval?: number;
  healthInterval?: number;
  resourceInterval?: number;
}

export const useMonitoring = ({
  pipelineId,
  metricsInterval = MONITORING_CONFIG.REFRESH_INTERVAL,
  healthInterval = MONITORING_CONFIG.HEALTH_CHECK_INTERVAL,
  resourceInterval = MONITORING_CONFIG.RESOURCE_CHECK_INTERVAL
}: UseMonitoringOptions) => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Fetch Metrics
  const {
    data: metrics,
    isLoading: isLoadingMetrics,
    error: metricsError,
    refetch: refreshMetrics
  } = useQuery(
    ['metrics', pipelineId],
    async () => {
      try {
        return await MonitoringService.getMetrics(pipelineId);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.METRICS_FETCH_FAILED);
      }
    },
    {
      refetchInterval: metricsInterval,
      enabled: Boolean(pipelineId),
      onSuccess: (data) => {
        dispatch(setMetrics(data));
      },
      onError: (error) => {
        dispatch(setError((error as Error).message));
      }
    }
  );

  // Fetch Health Status
  const {
    data: health,
    refetch: refreshHealth
  } = useQuery(
    ['health', pipelineId],
    async () => {
      try {
        return await MonitoringService.getHealth(pipelineId);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.HEALTH_FETCH_FAILED);
      }
    },
    {
      refetchInterval: healthInterval,
      enabled: Boolean(pipelineId),
      onSuccess: (data) => {
        dispatch(setSystemHealth(data));
      }
    }
  );

  // Fetch Resource Usage
  const {
    data: resources,
    refetch: refreshResources
  } = useQuery(
    ['resources', pipelineId],
    async () => {
      try {
        return await MonitoringService.getResourceUsage(pipelineId);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.RESOURCE_FETCH_FAILED);
      }
    },
    {
      refetchInterval: resourceInterval,
      enabled: Boolean(pipelineId),
      onSuccess: (data) => {
        dispatch(setResources(data));
      }
    }
  );

  // Mutations
  const { mutateAsync: startMonitoring, isLoading: isStarting } = useMutation(
    async (config: MonitoringConfig) => {
      dispatch(setLoading(true));
      try {
        await MonitoringService.startMonitoring(pipelineId, config);
        await Promise.all([
          refreshMetrics(),
          refreshHealth(),
          refreshResources()
        ]);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.START_FAILED);
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  const { mutateAsync: configureAlerts } = useMutation(
    async (config: AlertConfig) => {
      try {
        await MonitoringService.configureAlerts(pipelineId, config);
        await queryClient.invalidateQueries(['alerts', pipelineId]);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_CONFIG_FAILED);
      }
    }
  );

  const { mutateAsync: acknowledgeAlert } = useMutation(
    async (alertId: string) => {
      try {
        await MonitoringService.acknowledgeAlert(pipelineId, alertId);
        await queryClient.invalidateQueries(['alerts', pipelineId]);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_ACKNOWLEDGE_FAILED);
      }
    }
  );

  const { mutateAsync: resolveAlert } = useMutation(
    async ({ alertId, resolution }: { alertId: string; resolution?: { comment?: string; action?: string } }) => {
      try {
        await MonitoringService.resolveAlert(pipelineId, alertId, resolution);
        await queryClient.invalidateQueries(['alerts', pipelineId]);
      } catch (err) {
        handleApiError(err);
        throw new Error(MONITORING_MESSAGES.ERRORS.ALERT_RESOLVE_FAILED);
      }
    }
  );

  const refreshAll = useCallback(async () => {
    try {
      await Promise.all([
        refreshMetrics(),
        refreshHealth(),
        refreshResources()
      ]);
    } catch (err) {
      handleApiError(err);
    }
  }, [refreshMetrics, refreshHealth, refreshResources]);

  return {
    // Data
    metrics,
    health,
    resources,
    
    // Loading States
    isLoading: isLoadingMetrics || isStarting,
    error: metricsError as Error | null,
    
    // Actions
    startMonitoring,
    configureAlerts,
    acknowledgeAlert,
    resolveAlert,
    refreshAll,
    refreshMetrics,
    refreshHealth,
    refreshResources
  };
};