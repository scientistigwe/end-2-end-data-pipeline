// src/dataSource/hooks/useS3Source.ts
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { S3SourceConfig, S3BucketInfo } from '../types/dataSources';

export const useS3Source = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const {
    data: bucketInfo,
    isLoading: isLoadingBucketInfo,
    error: bucketError,
    refetch: refreshBucketInfo
  } = useQuery(
    ['s3BucketInfo', connectionId],
    async () => {
      if (!connectionId) return null;
      try {
        const response = await DataSourceService.getBucketInfo(connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.BUCKET_INFO_FAILED);
      }
    },
    { enabled: !!connectionId }
  );

  const { mutateAsync: connect, isLoading: isConnecting } = useMutation(
    async (config: S3SourceConfig['config']) => {
      try {
        const response = await DataSourceService.connectS3(config);
        setConnectionId(response.connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.S3_CONNECTION_FAILED);
      }
    }
  );

  const { mutateAsync: downloadObject } = useMutation(
    async (key: string) => {
      if (!connectionId) throw new Error('No active connection');
      try {
        const response = await DataSourceService.downloadS3Object(connectionId, key);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.DOWNLOAD_FAILED);
      }
    }
  );

  const disconnect = async () => {
    if (connectionId) {
      try {
        await DataSourceService.disconnectSource(connectionId);
        setConnectionId(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.DISCONNECT_FAILED);
      }
    }
  };

  return {
    connect,
    disconnect,
    downloadObject,
    connectionId,
    bucketInfo,
    isConnecting,
    isLoadingBucketInfo,
    bucketError,
    refreshBucketInfo
  };
};
