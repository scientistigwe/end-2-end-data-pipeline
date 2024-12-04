// src/hooks/sources/useApiSource.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/dataSourceApi';
import { handleApiError } from '../../utils/apiUtils';

interface ApiConfig {
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  auth?: {
    type: 'basic' | 'bearer' | 'oauth2';
    credentials: Record<string, string>;
  };
  params?: Record<string, any>;
  body?: any;
}

export const useApiSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  // Connect to API
  const { mutate: connect, isLoading: isConnecting } = useMutation(
    async (config: ApiConfig) => {
      const response = await dataSourceApi.connectApi(config);
      if (response.data?.connectionId) {
        setConnectionId(response.data.connectionId);
      }
      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Test connection
  const { mutate: testConnection } = useMutation(
    (config: ApiConfig) => dataSourceApi.testApiConnection(config)
  );

  // Get connection status
  const { data: status, refetch: refreshStatus } = useQuery(
    ['apiStatus', connectionId],
    () => dataSourceApi.getApiStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  // Fetch data
  const { mutate: fetchData } = useMutation(
    (params: Record<string, any>) =>
      dataSourceApi.fetchApiData(connectionId!, params)
  );

  // Disconnect
  const disconnect = useCallback(async () => {
    if (connectionId) {
      await dataSourceApi.disconnectApi(connectionId);
      setConnectionId(null);
    }
  }, [connectionId]);

  return {
    connect,
    testConnection,
    disconnect,
    fetchData,
    refreshStatus,
    connectionId,
    status,
    isConnecting
  };
};