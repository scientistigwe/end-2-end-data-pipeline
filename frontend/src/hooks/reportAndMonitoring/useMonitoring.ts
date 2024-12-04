// src/hooks/monitoring/useMonitoring.ts
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { monitoringApi } from '../../services/monitoringApi';
import { WebSocketClient } from '../../utils/websocketUtils';
import { handleApiError } from '../../utils/apiUtils';

interface MonitoringConfig {
  metrics: string[];
  interval?: number;
  alertThresholds?: Record<string, number>;
}

interface MetricsData {
  timestamp: string;
  metrics: Record<string, number>;
  status: 'healthy' | 'warning' | 'critical';
}

export const useMonitoring = (pipelineId: string) => {
  const [realtimeData, setRealtimeData] = useState<MetricsData[]>([]);
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);

  // Start Monitoring
  const { mutate: startMonitoring, isLoading: isStarting } = useMutation(
    async (config: MonitoringConfig) => {
      return monitoringApi.startMonitoring(pipelineId, config);
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Get Pipeline Metrics
  const { data: metrics, refetch: refreshMetrics } = useQuery(
    ['pipelineMetrics', pipelineId],
    () => monitoringApi.getPipelineMetrics(pipelineId),
    {
      refetchInterval: 5000,
      enabled: !!pipelineId
    }
  );

  // Get System Health
  const { data: systemHealth } = useQuery(
    ['systemHealth', pipelineId],
    () => monitoringApi.getSystemHealth(pipelineId),
    {
      refetchInterval: 10000,
      enabled: !!pipelineId
    }
  );

  // Get Performance Metrics
  const { data: performance } = useQuery(
    ['performanceMetrics', pipelineId],
    () => monitoringApi.getPerformanceMetrics(pipelineId),
    {
      refetchInterval: 5000,
      enabled: !!pipelineId
    }
  );

  // WebSocket Connection for Real-time Updates
  useEffect(() => {
    if (pipelineId) {
      const client = new WebSocketClient(
        `ws://your-api/monitoring/${pipelineId}`
      );

      const handleMessage = (message: MetricsData) => {
        setRealtimeData(prev => [...prev, message].slice(-100)); // Keep last 100 records
      };

      client.connect();
      const unsubscribe = client.subscribe(handleMessage);
      setWsClient(client);

      return () => {
        unsubscribe();
        client.disconnect();
        setWsClient(null);
      };
    }
  }, [pipelineId]);

  // Configure Alerts
  const { mutate: configureAlerts } = useMutation(
    async (config: {
      metricName: string;
      threshold: number;
      condition: 'above' | 'below';
      severity: 'warning' | 'critical';
    }) => monitoringApi.configureAlerts(pipelineId, config)
  );

  // Get Alert History
  const { data: alertHistory } = useQuery(
    ['alertHistory', pipelineId],
    () => monitoringApi.getAlertHistory(pipelineId),
    {
      enabled: !!pipelineId
    }
  );

  // Get Resource Usage
  const { data: resourceUsage } = useQuery(
    ['resourceUsage', pipelineId],
    () => monitoringApi.getResourceUsage(pipelineId),
    {
      refetchInterval: 10000,
      enabled: !!pipelineId
    }
  );

  return {
    startMonitoring,
    configureAlerts,
    refreshMetrics,
    metrics,
    systemHealth,
    performance,
    realtimeData,
    alertHistory,
    resourceUsage,
    isStarting
  };
};

