// src/dataSource/hooks/useStreamSource.ts
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { StreamSourceConfig, StreamMetrics } from '../types/dataSources';

export const useStreamSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const {
    data: metrics,
    isLoading: isLoadingMetrics,
    error: metricsError,
    refetch: refreshMetrics
  } = useQuery(
    ['streamMetrics', connectionId],
    async () => {
      if (!connectionId) return null;
      try {
        const response = await DataSourceService.getStreamMetrics(connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.METRICS_FETCH_FAILED);
      }
    },
    {
      enabled: !!connectionId,
      refetchInterval: 5000 // Refresh every 5 seconds
    }
  );

  const { mutateAsync: connect, isLoading: isConnecting } = useMutation(
    async (config: StreamSourceConfig['config']) => {
      try {
        const response = await DataSourceService.connectStream(config);
        setConnectionId(response.connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.STREAM_CONNECTION_FAILED);
      }
    }
  );

  const disconnect = async () => {
    if (connectionId) {
      try {
        await DataSourceService.disconnectSource(connectionId);
        setConnectionId(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.DISCONNECT_FAILED);
      }
    }
  };

  return {
    connect,
    disconnect,
    connectionId,
    metrics,
    isConnecting,
    isLoadingMetrics,
    metricsError,
    refreshMetrics
  };
};
