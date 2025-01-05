// src/dataSource/hooks/useStreamSource.ts - REFACTORED
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '@/common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { StreamSourceConfig } from '../types/streamSource';

export const useStreamSource = () => {
    const [connectionId, setConnectionId] = useState<string | null>(null);

    // Metrics fetching
    const {
        data: metrics,
        isLoading: isLoadingMetrics,
        error: metricsError,
        refetch: refreshMetrics
    } = useQuery(
        ['streamMetrics', connectionId],
        async () => {
            if (!connectionId) return null;
            try {
                const response = await DataSourceService.getStreamMetrics(connectionId);
                return response;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.METRICS_FETCH_FAILED);
            }
        },
        {
            enabled: !!connectionId,
            refetchInterval: 5000, // Poll every 5 seconds when component is mounted
            staleTime: 1000 // Consider data fresh for 1 second
        }
    );

    // Connection handling
    const { mutateAsync: connect, isLoading: isConnecting } = useMutation(
        async (config: StreamSourceConfig['config']) => {
            try {
                const response = await DataSourceService.connectStream(config);
                setConnectionId(response.connectionId);
                return response;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.STREAM_CONNECTION_FAILED);
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
        validate,
        connectionId,
        metrics,
        isConnecting,
        isDisconnecting,
        isLoadingMetrics,
        isValidating,
        metricsError,
        refreshMetrics
    };
};