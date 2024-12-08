import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { 
  ApiSourceConfig, 
  SourceConnectionResponse, 
  ConnectionTestResponse,
  SourceStatusResponse
} from '../types/dataSources';
import type { ApiResponse } from '../../common/types/api';

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
        setConnectionId(response.data?.connectionId || null);
      }
    }
  );

  const { mutate: testEndpoint } = useMutation<
    ApiResponse<ConnectionTestResponse>,
    Error,
    string
  >(
    (url) => dataSourceApi.testApiEndpoint(url),
    {
      onError: handleApiError
    }
  );

  const { data: status, refetch: refreshStatus } = useQuery<
    ApiResponse<SourceStatusResponse>,
    Error
  >(
    ['apiStatus', connectionId],
    () => dataSourceApi.getSourceStatus(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  const { mutate: executeRequest } = useMutation<
    ApiResponse<unknown>,
    Error,
    { method: string; url: string; body?: unknown }
  >(
    (params) => dataSourceApi.executeApiRequest(connectionId!, params),
    {
      onError: handleApiError
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
    disconnect,
    testEndpoint,
    executeRequest,
    refreshStatus,
    connectionId,
    status: status?.data?.status,
    responseTime: status?.data?.responseTime,
    lastChecked: status?.data?.lastChecked,
    error: status?.data?.error,
    isConnecting
  } as const;
}