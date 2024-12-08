// src/hooks/sources/useS3Source.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../api/dataSourceApi';
import { handleApiError } from '../../common/utils/api/apiUtils';
import type { S3SourceConfig } from '../types/dataSources';
import type { 
  SourceConnectionResponse,
  SourceConnectionStatus,
  S3Object,
  S3BucketInfo 
} from '../types/dataSources';
import type { ApiResponse } from '../../common/types/api';

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
        setConnectionId(response.data?.connectionId || null);
      }
    }
  );

  const { data: objects, refetch: refreshObjects } = useQuery<
    ApiResponse<{ objects: S3Object[] }>,
    Error
  >(
    ['s3Objects', connectionId, path],
    () => dataSourceApi.listS3Objects(connectionId!, path),
    { enabled: !!connectionId }
  );

  const { data: bucketInfo } = useQuery<ApiResponse<S3BucketInfo>, Error>(
    ['s3BucketInfo', connectionId],
    () => dataSourceApi.getBucketInfo(connectionId!),
    { enabled: !!connectionId }
  );

  const { mutate: downloadObject } = useMutation<
    Blob,
    Error,
    { key: string }
  >(
    (params) => dataSourceApi.downloadS3Object(connectionId!, params.key),
    { onError: handleApiError }
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
    downloadObject,
    refreshObjects,
    connectionId,
    objects: objects?.data?.objects,
    bucketInfo: bucketInfo?.data,
    isConnecting
  };
}
