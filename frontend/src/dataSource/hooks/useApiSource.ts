// src/dataSource/hooks/useApiSource.ts
import { useState } from 'react';
import { useMutation } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { ApiSourceConfig } from '../types/base';

export const useApiSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const { mutateAsync: connect, isLoading: isConnecting } = useMutation(
    async (config: ApiSourceConfig['config']) => {
      try {
        const response = await DataSourceService.connectApi(config);
        setConnectionId(response.connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.API_CONNECTION_FAILED);
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
    isConnecting,
    connectionId
  };
};