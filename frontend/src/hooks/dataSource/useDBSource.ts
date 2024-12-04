// src/hooks/sources/useDBSource.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/dataSourceApi';
import { handleApiError } from '../../utils/apiUtils';

interface DBConfig {
  type: 'postgresql' | 'mysql' | 'mssql' | 'oracle';
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl?: boolean;
  options?: Record<string, any>;
}

interface QueryConfig {
  query: string;
  params?: any[];
  timeout?: number;
}

export const useDBSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [lastQueryId, setLastQueryId] = useState<string | null>(null);

  // Connect to database
  const { mutate: connect, isLoading: isConnecting } = useMutation(
    async (config: DBConfig) => {
      const response = await dataSourceApi.connectDatabase(config);
      if (response.data?.connectionId) {
        setConnectionId(response.data.connectionId);
      }
      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Execute query
  const { mutate: executeQuery, isLoading: isQuerying } = useMutation(
    async (config: QueryConfig) => {
      const response = await dataSourceApi.executeQuery(connectionId!, config);
      if (response.data?.queryId) {
        setLastQueryId(response.data.queryId);
      }
      return response;
    }
  );

  // Get query results
  const { data: queryResults, refetch: refreshResults } = useQuery(
    ['queryResults', lastQueryId],
    () => dataSourceApi.getQueryResults(lastQueryId!),
    {
      enabled: !!lastQueryId
    }
  );

  // Get connection status
  const { data: status, refetch: refreshStatus } = useQuery(
    ['dbStatus', connectionId],
    () => dataSourceApi.getDatabaseStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  // Disconnect
  const disconnect = useCallback(async () => {
    if (connectionId) {
      await dataSourceApi.disconnectDatabase(connectionId);
      setConnectionId(null);
      setLastQueryId(null);
    }
  }, [connectionId]);

  return {
    connect,
    disconnect,
    executeQuery,
    refreshResults,
    refreshStatus,
    connectionId,
    status,
    queryResults,
    isConnecting,
    isQuerying
  };
};
