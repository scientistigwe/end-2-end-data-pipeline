// src/dataSource/hooks/useApiSource.ts - REFACTORED
import { useState } from 'react';
import { useMutation } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '@/common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { ApiSourceConfig } from '../types/apiSource';

export const useApiSource = () => {
    const [connectionId, setConnectionId] = useState<string | null>(null);

    // Connection handling
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

    // Endpoint testing
    const { mutateAsync: testEndpoint, isLoading: isTesting } = useMutation(
        async (url: string) => {
            try {
                const response = await DataSourceService.testApiEndpoint(url);
                return response;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.API_TEST_FAILED);
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
        testEndpoint,
        validate,
        connectionId,
        isConnecting,
        isDisconnecting,
        isTesting,
        isValidating
    };
};