// src/hooks/sources/useStreamSource.ts
import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/api/analysisAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import { WebSocketClient } from '../../utils/helpers/websocketUtil';

interface StreamConfig {
  type: 'kafka' | 'rabbitmq';
  connection: {
    host: string;
    port: number;
    username?: string;
    password?: string;
    ssl?: boolean;
  };
  topic?: string;
  queue?: string;
  groupId?: string;
  options?: Record<string, any>;
}

export const useStreamSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);

  // Connect to stream
  const { mutate: connect, isLoading: isConnecting } = useMutation(
    async (config: StreamConfig) => {
      const response = await dataSourceApi.connectStream(config);
      if (response.data?.connectionId) {
        setConnectionId(response.data.connectionId);
      }
      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Get connection status
  const { data: status, refetch: refreshStatus } = useQuery(
    ['streamStatus', connectionId],
    () => dataSourceApi.getStreamStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  // WebSocket connection for real-time messages
  useEffect(() => {
    if (connectionId) {
      const client = new WebSocketClient(
        `ws://your-api/stream/${connectionId}`
      );

      const handleMessage = (message: any) => {
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

  // Disconnect
  const disconnect = useCallback(async () => {
    if (connectionId) {
      wsClient?.disconnect();
      await dataSourceApi.disconnectStream(connectionId);
      setConnectionId(null);
      setMessages([]);
    }
  }, [connectionId, wsClient]);

  // Pause/Resume streaming
  const pauseStream = useCallback(async () => {
    if (connectionId) {
      await dataSourceApi.pauseStream(connectionId);
    }
  }, [connectionId]);

  const resumeStream = useCallback(async () => {
    if (connectionId) {
      await dataSourceApi.resumeStream(connectionId);
    }
  }, [connectionId]);

  return {
    connect,
    disconnect,
    pauseStream,
    resumeStream,
    refreshStatus,
    connectionId,
    status,
    messages,
    isConnecting
  };
};