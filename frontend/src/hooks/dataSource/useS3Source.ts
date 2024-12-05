// src/hooks/sources/useS3Source.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/api/dataSourceAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { S3SourceConfig } from '../../hooks/dataSource/types';
import type { 
  SourceConnectionResponse,
  SourceConnectionStatus,
  S3Object 
} from '../../types/source';
import type { ApiResponse } from '../../types/api';



export function useS3Source(path?: string) {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const { mutate: connect, isLoading: isConnecting } = useMutation<
    ApiResponse<SourceConnectionResponse>,
    Error,
    S3SourceConfig['config']
  >(
    (config) => dataSourceApi.connectS3(config),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        if (response.data?.connectionId) {
          setConnectionId(response.data.connectionId);
        }
      }
    }
  );

  const { data: objects, refetch: refreshObjects } = useQuery<
    ApiResponse<{ objects: S3Object[] }>,
    Error
  >(
    ['s3Objects', connectionId, path],
    () => dataSourceApi.listS3Objects(connectionId!, path),
    {
      enabled: !!connectionId
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
    ['s3Status', connectionId],
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
    refreshObjects,
    refreshStatus,
    connectionId,
    objects: objects?.data?.objects,
    status: status?.data?.status,
    isConnecting
  } as const;
}