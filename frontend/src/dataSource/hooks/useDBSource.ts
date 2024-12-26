// src/dataSource/hooks/useDBSource.ts
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { DBSourceConfig, SchemaInfo } from '../types/base';

export const useDBSource = () => {
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const {
    data: schema,
    isLoading: isLoadingSchema,
    error: schemaError,
    refetch: refreshSchema
  } = useQuery(
    ['dbSchema', connectionId],
    async () => {
      if (!connectionId) return null;
      try {
        const response = await DataSourceService.getDatabaseSchema(connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.SCHEMA_FETCH_FAILED);
      }
    },
    { enabled: !!connectionId }
  );

  const { mutateAsync: connect, isLoading: isConnecting } = useMutation(
    async (config: DBSourceConfig['config']) => {
      try {
        const response = await DataSourceService.connectDatabase(config);
        setConnectionId(response.connectionId);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.DB_CONNECTION_FAILED);
      }
    }
  );

  const { mutateAsync: executeQuery } = useMutation(
    async ({ query, params }: { query: string; params?: unknown[] }) => {
      if (!connectionId) throw new Error('No active connection');
      try {
        const response = await DataSourceService.executeDatabaseQuery(
          connectionId,
          query,
          params
        );
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.QUERY_FAILED);
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
    executeQuery,
    connectionId,
    schema,
    isConnecting,
    isLoadingSchema,
    schemaError,
    refreshSchema
  };
};



