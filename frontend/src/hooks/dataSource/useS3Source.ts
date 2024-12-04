// src/hooks/sources/useS3Source.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/dataSourceApi';
import { handleApiError } from '../../utils/apiUtils';

interface S3Config {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  bucket: string;
  prefix?: string;
  endpoint?: string;
}

interface S3Operation {
  operation: 'list' | 'get' | 'put' | 'delete';
  path: string;
  options?: Record<string, any>;
}

export const useS3Source = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [currentBucket, setCurrentBucket] = useState<string | null>(null);

  // Connect to S3
  const { mutate: connect, isLoading: isConnecting } = useMutation(
    async (config: S3Config) => {
      const response = await dataSourceApi.connectS3(config);
      if (response.data?.connectionId) {
        setConnectionId(response.data.connectionId);
        setCurrentBucket(config.bucket);
      }
      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // List objects
  const { data: objects, refetch: refreshObjects } = useQuery(
    ['s3Objects', connectionId, currentBucket],
    () => dataSourceApi.listS3Objects(connectionId!, currentBucket!),
    {
      enabled: !!connectionId && !!currentBucket
    }
  );

  // Perform S3 operation
  const { mutate: performOperation } = useMutation(
    (operation: S3Operation) =>
      dataSourceApi.performS3Operation(connectionId!, operation)
  );

  // Get connection status
  const { data: status, refetch: refreshStatus } = useQuery(
    ['s3Status', connectionId],
    () => dataSourceApi.getS3Status(connectionId!),
    {
      enabled: !!connectionId,
      refetchInterval: 5000
    }
  );

  // Disconnect
  const disconnect = useCallback(async () => {
    if (connectionId) {
      await dataSourceApi.disconnectS3(connectionId);
      setConnectionId(null);
      setCurrentBucket(null);
    }
  }, [connectionId]);

  return {
    connect,
    disconnect,
    performOperation,
    refreshObjects,
    refreshStatus,
    connectionId,
    currentBucket,
    objects,
    status,
    isConnecting
  };
};

