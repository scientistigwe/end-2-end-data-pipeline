// src/hooks/usePipeline.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { pipelineApi } from '../../services/api/pipelineAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import { PipelineConfig, PipelineStatus } from '../../services/api/types';

interface UsePipelineProps {
  pipelineId?: string;
  onError?: (error: any) => void;
  onSuccess?: (data: any) => void;
}

export const usePipeline = ({ pipelineId, onError, onSuccess }: UsePipelineProps) => {
  const [status, setStatus] = useState<PipelineStatus>('idle');

  // Start pipeline mutation
  const { mutate: startPipeline, isLoading: isStarting } = useMutation(
    (config: PipelineConfig) => pipelineApi.start(config),
    {
      onSuccess: (response) => {
        setStatus('running');
        onSuccess?.(response.data);
      },
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  // Status polling
  const { data: pipelineStatus, refetch: refreshStatus } = useQuery(
    ['pipelineStatus', pipelineId],
    () => pipelineApi.getStatus(pipelineId!),
    {
      enabled: !!pipelineId && status === 'running',
      refetchInterval: 3000,
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  // Stop pipeline mutation
  const { mutate: stopPipeline } = useMutation(
    () => pipelineApi.stop(pipelineId!),
    {
      onSuccess: () => {
        setStatus('stopped');
        onSuccess?.({ status: 'stopped' });
      },
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  // Get logs query
  const { data: logs, refetch: refreshLogs } = useQuery(
    ['pipelineLogs', pipelineId],
    () => pipelineApi.getLogs(pipelineId!),
    {
      enabled: !!pipelineId,
      refetchInterval: status === 'running' ? 5000 : false
    }
  );

  return {
    startPipeline,
    stopPipeline,
    refreshStatus,
    refreshLogs,
    status,
    pipelineStatus,
    logs,
    isStarting
  };
};
