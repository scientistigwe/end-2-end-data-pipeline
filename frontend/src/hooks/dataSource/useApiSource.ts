// src/hooks/sources/useApiSource.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/api/dataSourceAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { ApiSourceConfig } from '../../hooks/dataSource/types';
import type { 
  SourceConnectionResponse,
  ConnectionTestResponse,
  SourceConnectionStatus 
} from '../../types/source';
import type { ApiResponse } from '../../types/api';

export function useApiSource() {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const { mutate: connect, isLoading: isConnecting } = useMutation<
    ApiResponse<SourceConnectionResponse>,
    Error,
    ApiSourceConfig['config']
  >(
    (config) => dataSourceApi.connectApi(config),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        if (response.data?.connectionId) {
          setConnectionId(response.data.connectionId);
        }
      }
    }
  );

  const { mutate: testConnection } = useMutation<
    ApiResponse<ConnectionTestResponse>,
    Error,
    string
  >(
    (connId) => dataSourceApi.testApiConnection(connId),
    {
      onError: handleApiError
    }
  );

  const { data: status, refetch: refreshStatus } = useQuery<
    ApiResponse<{
      status: SourceConnectionStatus;
      lastChecked: string;
      error?: string;
    }>,
    Error
  >(
    ['apiStatus', connectionId],
    () => dataSourceApi.getSourceStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  const disconnect = async () => {
    if (connectionId) {
      await dataSourceApi.disconnectSource(connectionId);
      setConnectionId(null);
    }
  };

  return {
    connect,
    testConnection,
    disconnect,
    refreshStatus,
    connectionId,
    status: status?.data?.status,
    isConnecting
  } as const;
}