// src/hooks/sources/useStreamSource.ts
import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { StreamSourceConfig } from '../types/dataSources';
import type { 
  SourceConnectionResponse,
  SourceConnectionStatus,
  StreamMetrics,
  StreamMessage 
} from '../types/dataSources';
import type { ApiResponse } from '../../common/types/api';

export function useStreamSource() {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const { mutate: connect, isLoading: isConnecting } = useMutation<
    ApiResponse<SourceConnectionResponse>,
    Error,
    StreamSourceConfig['config']
  >(
    (config) => dataSourceApi.connectStream(config),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        setConnectionId(response.data?.connectionId || null);
      }
    }
  );

  const { data: metrics, refetch: refreshMetrics } = useQuery<
    ApiResponse<StreamMetrics>,
    Error
  >(
    ['streamMetrics', connectionId],
    () => dataSourceApi.getStreamMetrics(connectionId!),
    {
      enabled: !!connectionId && isConnected,
      refetchInterval: 1000
    }
  );

  const onMessage = useCallback((message: StreamMessage) => {
    setMessages(prev => [...prev.slice(-999), message]);
  }, []);

  useEffect(() => {
    if (connectionId) {
      const ws = new WebSocket(
        `${process.env.REACT_APP_WS_URL}/stream/${connectionId}`
      );

      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => setIsConnected(false);
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          onMessage(message);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      return () => {
        ws.close();
        setIsConnected(false);
      };
    }
  }, [connectionId, onMessage]);

  const disconnect = async () => {
    if (connectionId) {
      await dataSourceApi.disconnectSource(connectionId);
      setConnectionId(null);
      setMessages([]);
      setIsConnected(false);
    }
  };

  return {
    connect,
    disconnect,
    refreshMetrics,
    connectionId,
    messages,
    metrics: metrics?.data,
    isConnected,
    isConnecting
  };
}