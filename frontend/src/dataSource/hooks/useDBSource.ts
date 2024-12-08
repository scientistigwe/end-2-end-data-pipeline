// src/hooks/sources/useDBSource.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { DBSourceConfig } from '../types/dataSources';
import type { 
  SourceConnectionResponse,
  ConnectionTestResponse,
  SourceConnectionStatus,
  SchemaInfo 
} from '../types/dataSources';
import type { ApiResponse } from '../../common/types/api';

export function useDBSource() {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const { mutate: connect, isLoading: isConnecting } = useMutation<
    ApiResponse<SourceConnectionResponse>,
    Error,
    DBSourceConfig['config']
  >(
    (config) => dataSourceApi.connectDatabase(config),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        setConnectionId(response.data?.connectionId || null);
      }
    }
  );

  const { data: schema } = useQuery<ApiResponse<SchemaInfo>, Error>(
    ['dbSchema', connectionId],
    () => dataSourceApi.getDatabaseSchema(connectionId!),
    { enabled: !!connectionId }
  );

  const { mutate: executeQuery } = useMutation<
    ApiResponse<unknown>,
    Error,
    string
  >(
    (query) => dataSourceApi.executeDatabaseQuery(connectionId!, query),
    { onError: handleApiError }
  );

  const { data: status, refetch: refreshStatus } = useQuery<
    ApiResponse<{
      status: SourceConnectionStatus;
      lastChecked: string;
      error?: string;
    }>,
    Error
  >(
    ['dbStatus', connectionId],
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
    disconnect,
    executeQuery,
    refreshStatus,
    connectionId,
    schema: schema?.data,
    status: status?.data?.status,
    isConnecting
  };
}



