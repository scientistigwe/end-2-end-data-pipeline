// src/dataSource/hooks/useDBSource.ts - REFACTORED
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '@/common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { DBSourceConfig } from '../types/dbSource';

export const useDBSource = () => {
    const [connectionId, setConnectionId] = useState<string | null>(null);

    // Schema fetching
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
        {
            enabled: !!connectionId,
            retry: 2,
            staleTime: 30000 // Consider schema fresh for 30 seconds
        }
    );

    // Connection handling
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

    // Query execution
    const { mutateAsync: executeQuery, isLoading: isExecutingQuery } = useMutation(
        async ({ 
            query, 
            params 
        }: { 
            query: string; 
            params?: unknown[] 
        }) => {
            if (!connectionId) {
                throw new Error('No active database connection');
            }
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

    // Disconnect handling
    const { mutateAsync: disconnect, isLoading: isDisconnecting } = useMutation(
        async () => {
            if (!connectionId) return;
            try {
                await DataSourceService.disconnectSource(connectionId);
                setConnectionId(null);
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.DISCONNECT_FAILED);
            }
        }
    );

    // Validation
    const { mutateAsync: validate, isLoading: isValidating } = useMutation(
        async () => {
            if (!connectionId) throw new Error('No active connection');
            return DataSourceService.validateDataSource(connectionId);
        }
    );

    return {
        connect,
        disconnect,
        executeQuery,
        validate,
        connectionId,
        schema,
        isConnecting,
        isDisconnecting,
        isExecutingQuery,
        isLoadingSchema,
        isValidating,
        schemaError,
        refreshSchema
    };
};