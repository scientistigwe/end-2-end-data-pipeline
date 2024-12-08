// src/hooks/pipeline/usePipeline.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { pipelineApi } from '../../api/pipelineAPI';
import { handleApiError } from '../../common/utils/api/apiUtils';
import {
  setPipelines,
  updatePipeline,
  updatePipelineStatus,
  setPipelineRuns,
  addPipelineRun,
  setPipelineLogs,
  setPipelineMetrics,
  setLoading,
} from '../store/pipelineSlice';
import type { PipelineConfig } from '../types/pipeline';

export function usePipeline(pipelineId?: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // List pipelines
  const { data: pipelines, refetch: refreshPipelines } = useQuery(
    ['pipelines'],
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await pipelineApi.listPipelines();
        if (response.data) {
          dispatch(setPipelines(response.data));
        }
        return response.data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Create pipeline
  const { mutate: createPipeline } = useMutation(
    async (config: PipelineConfig) => {
          const response = await pipelineApi.createPipeline(config);
          if (response.data) {
              dispatch(updatePipeline(response.data));
          }
          return response.data;
    },
    {
      onError: handleApiError,
      onSuccess: () => {
        queryClient.invalidateQueries(['pipelines']);
      }
    }
  );

  // Update pipeline
  const { mutate: updatePipelineConfig } = useMutation(
    async ({
      id,
      updates
    }: {
      id: string;
      updates: Partial<PipelineConfig>;
    }) => {
          const response = await pipelineApi.updatePipeline(id, updates);
          if (response.data) {
              dispatch(updatePipeline(response.data));
          }
          return response.data;
    },
    {
      onError: handleApiError
    }
  );

  // Start pipeline
  const { mutate: startPipeline } = useMutation(
    async ({
      id,
      options
    }: {
      id: string;
      options?: { mode?: string; params?: Record<string, unknown> };
    }) => {
        const response = await pipelineApi.startPipeline(id, options);
        if (response.data) {
          dispatch(updatePipelineStatus({ id, status: 'running' }));
          dispatch(addPipelineRun({ pipelineId: id, run: response.data }));
        }
        return response.data;
    },
    {
      onError: handleApiError
    }
  );

  // Stop pipeline
  const { mutate: stopPipeline } = useMutation(
    async (id: string) => {
      await pipelineApi.stopPipeline(id);
      dispatch(updatePipelineStatus({ id, status: 'stopped' }));
    },
    {
      onError: handleApiError
    }
  );

  // Get pipeline runs
  const { data: runs } = useQuery(
    ['pipelineRuns', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getPipelineRuns(pipelineId);
      if (response.data) {
        dispatch(setPipelineRuns({ pipelineId, runs: response.data }));
      }
      return response.data;
    },
    {
      enabled: !!pipelineId
    }
  );

  // Get pipeline logs
  const { data: logs, refetch: refreshLogs } = useQuery(
    ['pipelineLogs', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getPipelineLogs(pipelineId);
    if (response.data) {
  dispatch(setPipelineLogs({ pipelineId, logs: response.data }));
}
return response.data;
    },
    {
      enabled: !!pipelineId
    }
  );

  // Get pipeline metrics
  const { data: metrics } = useQuery(
    ['pipelineMetrics', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getPipelineMetrics(pipelineId);
      if (response.data) {
        dispatch(setPipelineMetrics({ pipelineId, metrics: response.data }));
      }
      return response.data;
    },
    {
      enabled: !!pipelineId,
      refetchInterval: 30000 // Refresh every 30 seconds
    }
  );

  return {
    // Data
    pipelines,
    runs,
    logs,
    metrics,

    // Actions
    createPipeline,
    updatePipelineConfig,
    startPipeline,
    stopPipeline,
    refreshPipelines,
    refreshLogs
  } as const;
}