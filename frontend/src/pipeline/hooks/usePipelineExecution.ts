import { useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { PipelineApi } from '../api/pipelineApi';
import { updatePipelineStatus } from '../store/pipelineSlice';
import type { PipelineRun } from '../types/pipeline';

export function usePipelineExecution(pipelineId: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  const pipelineApi = new PipelineApi();

  const startPipeline = useMutation<
    PipelineRun,
    Error,
    { mode?: string; params?: Record<string, unknown> }
  >(
    async (options) => {
      const response = await pipelineApi.startPipeline(pipelineId, options);
      dispatch(updatePipelineStatus({ id: pipelineId, status: 'running' }));
      return response;
    },
    {
      onSuccess: () => {
        // Invalidate relevant queries
        queryClient.invalidateQueries(['pipeline', pipelineId]);
        queryClient.invalidateQueries(['pipelineRuns', pipelineId]);
      },
      onError: (error) => {
        console.error('Failed to start pipeline:', error);
        dispatch(updatePipelineStatus({ id: pipelineId, status: 'failed' }));
      }
    }
  );

  const stopPipeline = useMutation<void, Error>(
    async () => {
      await pipelineApi.stopPipeline(pipelineId);
      dispatch(updatePipelineStatus({ id: pipelineId, status: 'cancelled' }));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipeline', pipelineId]);
        queryClient.invalidateQueries(['pipelineRuns', pipelineId]);
      },
      onError: (error) => {
        console.error('Failed to stop pipeline:', error);
      }
    }
  );

  const retryPipeline = useMutation<PipelineRun, Error>(
    async () => {
      const response = await pipelineApi.retryPipeline(pipelineId);
      dispatch(updatePipelineStatus({ id: pipelineId, status: 'running' }));
      return response;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipeline', pipelineId]);
        queryClient.invalidateQueries(['pipelineRuns', pipelineId]);
      },
      onError: (error) => {
        console.error('Failed to retry pipeline:', error);
        dispatch(updatePipelineStatus({ id: pipelineId, status: 'failed' }));
      }
    }
  );

  const pausePipeline = useMutation<void, Error>(
    async () => {
      await pipelineApi.pausePipeline(pipelineId);
      dispatch(updatePipelineStatus({ id: pipelineId, status: 'paused' }));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipeline', pipelineId]);
      }
    }
  );

  const resumePipeline = useMutation<void, Error>(
    async () => {
      await pipelineApi.resumePipeline(pipelineId);
      dispatch(updatePipelineStatus({ id: pipelineId, status: 'running' }));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipeline', pipelineId]);
      }
    }
  );

  return {
    startPipeline,
    stopPipeline,
    retryPipeline,
    pausePipeline,
    resumePipeline,
    isExecuting: startPipeline.isLoading || 
                 stopPipeline.isLoading || 
                 retryPipeline.isLoading ||
                 pausePipeline.isLoading ||
                 resumePipeline.isLoading
  } as const;
}

export type UsePipelineExecutionReturn = ReturnType<typeof usePipelineExecution>;