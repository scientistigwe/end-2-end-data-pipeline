// src/dataSource/hooks/useS3Source.ts - REFACTORED
import { useState } from 'react';
import { useMutation, useQuery } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '@/common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { S3SourceConfig } from '../types/s3Source';

export const useS3Source = () => {
    const [connectionId, setConnectionId] = useState<string | null>(null);
    const [currentPrefix, setCurrentPrefix] = useState<string>('');

    // Object listing
    const {
        data: objectList,
        isLoading: isLoadingObjects,
        error: objectError,
        refetch: refreshObjects
    } = useQuery(
        ['s3Objects', connectionId, currentPrefix],
        async () => {
            if (!connectionId) return null;
            try {
                const response = await DataSourceService.listS3Objects(connectionId, currentPrefix);
                return response;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.S3_LIST_FAILED);
            }
        },
        {
            enabled: !!connectionId,
            retry: 1,
            staleTime: 10000 // Consider object list fresh for 10 seconds
        }
    );

    // Connection handling
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

    // Disconnect handling
    const { mutateAsync: disconnect, isLoading: isDisconnecting } = useMutation(
        async () => {
            if (!connectionId) return;
            try {
                await DataSourceService.disconnectSource(connectionId);
                setConnectionId(null);
                setCurrentPrefix('');
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

    const navigateToPrefix = (prefix: string) => {
        setCurrentPrefix(prefix);
    };

    return {
        connect,
        disconnect,
        validate,
        navigateToPrefix,
        connectionId,
        currentPrefix,
        objectList,
        isConnecting,
        isDisconnecting,
        isLoadingObjects,
        isValidating,
        objectError,
        refreshObjects
    };
};