// src/hooks/pipeline/usePipeline.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { pipelineApi } from '../../services/api/pipelineAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { 
  ApiResponse, 
  PipelineConfig, 
  PipelineStatus,
  PipelineResponse,
  PipelineLogs 
} from '../../services/api/types';
import type { UsePipelineProps, UsePipelineResult } from './types';

export const usePipeline = ({ 
  pipelineId, 
  onError, 
  onSuccess 
}: UsePipelineProps): UsePipelineResult => {
  const [status, setStatus] = useState<PipelineStatus>('idle');

  // Common error handler
  const handleError = (error: unknown) => {
    handleApiError(error);
    onError?.(error instanceof Error ? error : new Error('Unknown error occurred'));
  };

  const startPipelineMutation = useMutation<
    ApiResponse<PipelineResponse>,
    Error,
    PipelineConfig
  >(
    (config) => pipelineApi.start(config),
    {
      onSuccess: (response) => {
        setStatus('running');
        onSuccess?.(response.data);
      },
      onError: handleError
    }
  );

  const stopPipelineMutation = useMutation<
    ApiResponse<void>,
    Error,
    void
  >(
    () => {
      if (!pipelineId) throw new Error('Pipeline ID is required');
      return pipelineApi.stop(pipelineId);
    },
    {
      onSuccess: () => {
        setStatus('stopped');
        onSuccess?.({ status: 'stopped' });
      },
      onError: handleError
    }
  );

  const statusQuery = useQuery<PipelineResponse | null, Error>(
    ['pipelineStatus', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getStatus(pipelineId);
      return response.data ?? null;
    },
    {
      enabled: !!pipelineId && status === 'running',
      refetchInterval: 3000,
      onError: handleError
    }
  );

  const logsQuery = useQuery<PipelineLogs | null, Error>(
    ['pipelineLogs', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getLogs(pipelineId);
      return response.data ?? null;
    },
    {
      enabled: !!pipelineId,
      refetchInterval: status === 'running' ? 5000 : false,
      onError: handleError
    }
  );

  return {
    // Actions
    startPipeline: startPipelineMutation.mutate,
    stopPipeline: stopPipelineMutation.mutate,
    refreshStatus: statusQuery.refetch,
    refreshLogs: logsQuery.refetch,

    // State
    status,
    pipelineStatus: statusQuery.data,
    logs: logsQuery.data,

    // Loading States
    isStarting: startPipelineMutation.isLoading,
    isStopping: stopPipelineMutation.isLoading,
    isLoading: statusQuery.isLoading || logsQuery.isLoading,

    // Error State
    error: startPipelineMutation.error ?? 
           stopPipelineMutation.error ?? 
           statusQuery.error ?? 
           logsQuery.error ?? 
           null
  };
};