// src/hooks/monitoring/useMonitoring.ts
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { useDispatch } from 'react-redux';
import { monitoringApi } from '../../api/monitoringAPI';
import { WebSocketClient } from '../../common/utils/api/websocketUtil';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { 
  setMetrics, 
  setSystemHealth, 
  setAlerts, 
  addAlert,
  setResources 
} from '../store/monitoringSlice';
import type { 
  MonitoringConfig,
  MetricsData,
  AlertConfig 
} from '../types/monitoring';

interface UseMonitoringOptions {
  pipelineId: string;
  metricsInterval?: number;
  healthInterval?: number;
  resourceInterval?: number;
}

export function useMonitoring({
  pipelineId,
  metricsInterval = 5000,
  healthInterval = 10000,
  resourceInterval = 10000
}: UseMonitoringOptions) {
  const dispatch = useDispatch();
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);

  // Start Monitoring
  const { mutate: startMonitoring, isLoading: isStarting } = useMutation(
    (config: MonitoringConfig) => monitoringApi.startMonitoring(pipelineId, config),
    {
      onError: handleApiError
    }
  );

  // Configure Alerts
  const { mutate: configureAlerts } = useMutation(
    (config: AlertConfig) => monitoringApi.configureAlerts(pipelineId, config),
    {
      onError: handleApiError
    }
  );

  // Fetch Metrics
  const { data: metricsData, refetch: refreshMetrics } = useQuery(
    ['metrics', pipelineId],
    () => monitoringApi.getMetrics(pipelineId),
    {
      refetchInterval: metricsInterval,
      enabled: !!pipelineId,
      onSuccess: (response) => {
        dispatch(setMetrics(response.data));
      },
      onError: handleApiError
    }
  );

  // Fetch Health
  const { data: healthData, refetch: refreshHealth } = useQuery(
    ['health', pipelineId],
    () => monitoringApi.getHealth(pipelineId),
    {
      refetchInterval: healthInterval,
      enabled: !!pipelineId,
      onSuccess: (response) => {
        dispatch(setSystemHealth(response.data));
      },
      onError: handleApiError
    }
  );

  // Fetch Resource Usage
  const { data: resourceData, refetch: refreshResources } = useQuery(
    ['resources', pipelineId],
    () => monitoringApi.getResourceUsage(pipelineId),
    {
      refetchInterval: resourceInterval,
      enabled: !!pipelineId,
      onSuccess: (response) => {
        dispatch(setResources(response.data));
      },
      onError: handleApiError
    }
  );

  // Fetch Alert History
  const { data: alertData } = useQuery(
    ['alerts', pipelineId],
    () => monitoringApi.getAlertHistory(pipelineId),
    {
      enabled: !!pipelineId,
      onSuccess: (response) => {
        dispatch(setAlerts(response.data));
      },
      onError: handleApiError
    }
  );

  // WebSocket Connection
  useEffect(() => {
    if (!pipelineId) return;

    const client = new WebSocketClient(
      `${process.env.REACT_APP_WS_URL}/monitoring/${pipelineId}`
    );

    const handleMessage = (message: MetricsData) => {
      dispatch(setMetrics(message));
    };

    client.connect();
    const unsubscribe = client.subscribe(handleMessage);
    setWsClient(client);

    return () => {
      unsubscribe();
      client.disconnect();
      setWsClient(null);
    };
  }, [pipelineId, dispatch]);

  // Refresh all data
  const refreshAll = async () => {
    await Promise.all([
      refreshMetrics(),
      refreshHealth(),
      refreshResources()
    ]);
  };

  return {
    // Data
    metrics: metricsData?.data,
    health: healthData?.data,
    resources: resourceData?.data,
    alerts: alertData?.data,

    // Actions
    startMonitoring,
    configureAlerts,
    refreshAll,
    refreshMetrics,
    refreshHealth,
    refreshResources,

    // Status
    isStarting,
    wsClient
  } as const;
}

