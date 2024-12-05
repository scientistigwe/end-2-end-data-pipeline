// src/hooks/sources/useStreamSource.ts
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/api/dataSourceAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import { WebSocketClient } from '../../utils/helpers/websocketUtil';
import type { StreamSourceConfig } from '../../hooks/dataSource/types';
import type { 
  SourceConnectionResponse,
  SourceConnectionStatus,
  StreamMetrics 
} from '../../types/source';
import type { ApiResponse } from '../../types/api';

export function useStreamSource() {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<unknown[]>([]);
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);

  const { mutate: connect, isLoading: isConnecting } = useMutation<
    ApiResponse<SourceConnectionResponse>,
    Error,
    StreamSourceConfig['config']
  >(
    (config) => dataSourceApi.connectStream(config),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        if (response.data?.connectionId) {
          setConnectionId(response.data.connectionId);
        }
      }
    }
  );

  const { data: status, refetch: refreshStatus } = useQuery<
    ApiResponse<{
      status: SourceConnectionStatus;
      metrics: StreamMetrics;
    }>,
    Error
  >(
    ['streamStatus', connectionId],
    () => dataSourceApi.getStreamStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  useEffect(() => {
    if (connectionId) {
      const client = new WebSocketClient(
        `ws://your-api/stream/${connectionId}`
      );

      const handleMessage = (message: unknown) => {
        setMessages(prev => [...prev, message].slice(-1000)); // Keep last 1000 messages
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
  }, [connectionId]);

  const disconnect = async () => {
    if (connectionId) {
      wsClient?.disconnect();
      await dataSourceApi.disconnectSource(connectionId);
      setConnectionId(null);
      setMessages([]);
    }
  };

  return {
    connect,
    disconnect,
    refreshStatus,
    connectionId,
    status: status?.data?.status,
    metrics: status?.data?.metrics,
    messages,
    isConnecting
  } as const;
}