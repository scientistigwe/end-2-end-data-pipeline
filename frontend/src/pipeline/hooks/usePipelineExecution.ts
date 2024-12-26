// src/pipeline/hooks/usePipelineExecution.ts
import { useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { pipelineApi } from '../api/pipelineApi';
import { updatePipelineStatus } from '../store/pipelineSlice';
import type { PipelineRun, PipelineError, PipelineStatus } from '../types';

export function usePipelineExecution(pipelineId: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const updateStatus = (status: PipelineStatus, previousStatus: PipelineStatus) => {
    dispatch(updatePipelineStatus({
      id: pipelineId,
      status,
      previousStatus,
      timestamp: new Date().toISOString()
    }));
  };

  const invalidateQueries = () => {
    queryClient.invalidateQueries(['pipeline', pipelineId]);
    queryClient.invalidateQueries(['pipelineRuns', pipelineId]);
    queryClient.invalidateQueries(['pipeline-status', pipelineId]);
    queryClient.invalidateQueries(['pipeline-metrics', pipelineId]);
  };

  const handleError = (error: unknown) => {
    console.error('Pipeline execution error:', error);
    const pipelineError = error as PipelineError;
    return pipelineError;
  };

  const startPipeline = useMutation<
    PipelineRun,
    PipelineError,
    { mode?: string; params?: Record<string, unknown> }
  >(
    async (options) => {
      try {
        const currentStatus = queryClient.getQueryData(['pipeline-status', pipelineId]) as { status: PipelineStatus } | undefined;
        const response = await pipelineApi.startPipeline(pipelineId, options);
        updateStatus('running', currentStatus?.status || 'idle');
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => invalidateQueries(),
      onError: (error) => {
        updateStatus('failed', 'running');
      }
    }
  );

  const stopPipeline = useMutation<void, PipelineError>(
    async () => {
      try {
        const currentStatus = queryClient.getQueryData(['pipeline-status', pipelineId]) as { status: PipelineStatus } | undefined;
        await pipelineApi.stopPipeline(pipelineId);
        updateStatus('cancelled', currentStatus?.status || 'running');
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => invalidateQueries()
    }
  );

  const retryPipeline = useMutation<PipelineRun, PipelineError>(
    async () => {
      try {
        const currentStatus = queryClient.getQueryData(['pipeline-status', pipelineId]) as { status: PipelineStatus } | undefined;
        const response = await pipelineApi.retryPipeline(pipelineId);
        updateStatus('running', currentStatus?.status || 'failed');
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => invalidateQueries(),
      onError: (error) => {
        updateStatus('failed', 'running');
      }
    }
  );

  const pausePipeline = useMutation<void, PipelineError>(
    async () => {
      try {
        const currentStatus = queryClient.getQueryData(['pipeline-status', pipelineId]) as { status: PipelineStatus } | undefined;
        await pipelineApi.pausePipeline(pipelineId);
        updateStatus('paused', currentStatus?.status || 'running');
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => invalidateQueries()
    }
  );

  const resumePipeline = useMutation<void, PipelineError>(
    async () => {
      try {
        const currentStatus = queryClient.getQueryData(['pipeline-status', pipelineId]) as { status: PipelineStatus } | undefined;
        await pipelineApi.resumePipeline(pipelineId);
        updateStatus('running', currentStatus?.status || 'paused');
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => invalidateQueries()
    }
  );

  return {
    startPipeline,
    stopPipeline,
    retryPipeline,
    pausePipeline,
    resumePipeline,
    isExecuting: 
      startPipeline.isLoading || 
      stopPipeline.isLoading || 
      retryPipeline.isLoading ||
      pausePipeline.isLoading ||
      resumePipeline.isLoading
  } as const;
}

export type UsePipelineExecutionReturn = ReturnType<typeof usePipelineExecution>;