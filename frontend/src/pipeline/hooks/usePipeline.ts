// src/pipeline/hooks/usePipeline.ts
import { useQuery, useMutation, useQueryClient, UseQueryResult } from 'react-query';
import { useDispatch } from 'react-redux';
import { useCallback, useEffect } from 'react';
import { pipelineApi } from '../api/pipelineApi';
import {
  setPipelines,
  updatePipeline as updatePipelineAction,
  removePipeline,
  setError,
  setLoading,
  updatePipelineStatus
} from '../store/pipelineSlice';
import type { 
  Pipeline, 
  PipelineConfig, 
  PipelineError,
  PipelineStatus,
  PipelineEventMap,
  PipelineLogs,
  PipelineMetrics,
  PipelineRun
} from '../types';
import { PIPELINE_EVENTS } from '../api/pipelineApi';

export function usePipeline(pipelineId?: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Event subscription setup
  useEffect(() => {
    if (!pipelineId) return;

    const statusChangeUnsubscribe = pipelineApi.subscribeToEvents(
      PIPELINE_EVENTS.STATUS_CHANGE,
      (event: PipelineEventMap['pipeline:statusChange']) => {
        const { pipelineId: id, status, previousStatus, timestamp } = event.detail;
        dispatch(updatePipelineStatus({ 
          id, 
          status, 
          previousStatus, 
          timestamp 
        }));
        queryClient.invalidateQueries(['pipeline', id]);
      }
    );

    const runCompleteUnsubscribe = pipelineApi.subscribeToEvents(
      PIPELINE_EVENTS.RUN_COMPLETE,
      () => {
        queryClient.invalidateQueries(['pipeline', pipelineId]);
        queryClient.invalidateQueries(['pipeline-runs', pipelineId]);
      }
    );

    return () => {
      statusChangeUnsubscribe();
      runCompleteUnsubscribe();
    };
  }, [pipelineId, dispatch, queryClient]);

  // Error handling
  const handleError = useCallback((error: unknown) => {
    const pipelineError = error as PipelineError;
    dispatch(setError(pipelineError.message || 'An unknown error occurred'));
    return error;
  }, [dispatch]);

  // Loading state management
  const setLoadingState = useCallback((loading: boolean) => {
    dispatch(setLoading(loading));
  }, [dispatch]);

  // Pipeline Queries
  const pipelinesQuery = useQuery<Pipeline[]>(
    ['pipelines'],
    async () => {
      try {
        const response = await pipelineApi.listPipelines();
        dispatch(setPipelines(response.data));
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      staleTime: 30000,
      cacheTime: 300000,
      retry: 3
    }
  );

  const pipelineQuery = useQuery<Pipeline | null>(
    ['pipeline', pipelineId],
    async () => {
      if (!pipelineId) return null;
      try {
        const response = await pipelineApi.getPipeline(pipelineId);
        dispatch(updatePipelineAction(response.data));
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      enabled: Boolean(pipelineId),
      staleTime: 30000,
      retry: 3
    }
  );

  // Pipeline Status Query
  const pipelineStatusQuery = useQuery<{
    status: PipelineStatus;
    progress: number;
    currentStep?: string;
  } | null>(
    ['pipeline-status', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getPipelineStatus(pipelineId);
      return response.data;
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: (data) => 
        data?.status === 'running' ? 5000 : false,
      retry: 3
    }
  );

  // Pipeline Logs Query
  const pipelineLogsQuery = useQuery<PipelineLogs>(
    ['pipeline-logs', pipelineId],
    async () => {
      if (!pipelineId) throw new Error('Pipeline ID required');
      const response = await pipelineApi.getPipelineLogs(pipelineId);
      return response.data;
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: () => 
        pipelineStatusQuery.data?.status === 'running' ? 10000 : false
    }
  );

  // Pipeline Metrics Query
  const pipelineMetricsQuery = useQuery<PipelineMetrics[]>(
    ['pipeline-metrics', pipelineId],
    async () => {
      if (!pipelineId) throw new Error('Pipeline ID required');
      const response = await pipelineApi.getPipelineMetrics(pipelineId);
      return response.data;
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: () => 
        pipelineStatusQuery.data?.status === 'running' ? 30000 : false
    }
  );

  // CRUD Mutations
  const createPipeline = useMutation<Pipeline, Error, PipelineConfig>(
    async (config) => {
      try {
        const response = await pipelineApi.createPipeline(config);
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: (data) => {
        dispatch(updatePipelineAction(data));
        queryClient.invalidateQueries(['pipelines']);
      }
    }
  );

  const updatePipelineConfig = useMutation<
    Pipeline,
    Error,
    { id: string; updates: Partial<PipelineConfig> }
  >(
    async ({ id, updates }) => {
      try {
        const response = await pipelineApi.updatePipeline(id, updates);
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: (data) => {
        dispatch(updatePipelineAction(data));
        queryClient.invalidateQueries(['pipelines']);
        if (pipelineId) {
          queryClient.invalidateQueries(['pipeline', pipelineId]);
        }
      }
    }
  );

  const deletePipeline = useMutation<void, Error, string>(
    async (id) => {
      try {
        await pipelineApi.deletePipeline(id);
        dispatch(removePipeline(id));
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipelines']);
      }
    }
  );

  // Pipeline Control Mutations
  const controlMutationConfig = {
    onSuccess: () => {
      if (pipelineId) {
        queryClient.invalidateQueries(['pipeline-status', pipelineId]);
        queryClient.invalidateQueries(['pipeline', pipelineId]);
      }
    }
  };

  const startPipeline = useMutation<
    PipelineRun,
    Error,
    { id: string; options?: { mode?: string; params?: Record<string, unknown> } }
  >(
    async ({ id, options }) => {
      try {
        const response = await pipelineApi.startPipeline(id, options);
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    controlMutationConfig
  );

  const stopPipeline = useMutation<void, Error, string>(
    async (id) => {
      try {
        await pipelineApi.stopPipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    },
    controlMutationConfig
  );

  const pausePipeline = useMutation<void, Error, string>(
    async (id) => {
      try {
        await pipelineApi.pausePipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    },
    controlMutationConfig
  );

  const resumePipeline = useMutation<void, Error, string>(
    async (id) => {
      try {
        await pipelineApi.resumePipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    },
    controlMutationConfig
  );

  const retryPipeline = useMutation<PipelineRun, Error, string>(
    async (id) => {
      try {
        const response = await pipelineApi.retryPipeline(id);
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },
    controlMutationConfig
  );

  // Validation Mutation
  const validatePipelineConfig = useMutation<
    { valid: boolean; errors?: string[] },
    Error,
    PipelineConfig
  >(
    async (config) => {
      try {
        const response = await pipelineApi.validatePipelineConfig(config);
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  return {
    // Queries
    pipelines: pipelinesQuery.data,
    pipeline: pipelineQuery.data,
    pipelineStatus: pipelineStatusQuery.data,
    pipelineLogs: pipelineLogsQuery.data,
    pipelineMetrics: pipelineMetricsQuery.data,
    isLoading: pipelinesQuery.isLoading || pipelineQuery.isLoading,
    
    // CRUD Operations
    createPipeline,
    updatePipelineConfig,
    deletePipeline,
    
    // Pipeline Controls
    startPipeline,
    stopPipeline,
    pausePipeline,
    resumePipeline,
    retryPipeline,
    
    // Validation
    validatePipelineConfig,
    
    // Helper methods
    refetchPipelines: () => queryClient.invalidateQueries(['pipelines']),
    refetchPipeline: () => pipelineId && queryClient.invalidateQueries(['pipeline', pipelineId]),
    refetchStatus: () => pipelineId && queryClient.invalidateQueries(['pipeline-status', pipelineId]),
    refetchLogs: () => pipelineId && queryClient.invalidateQueries(['pipeline-logs', pipelineId]),
    refetchMetrics: () => pipelineId && queryClient.invalidateQueries(['pipeline-metrics', pipelineId])
  } as const;
}

export type UsePipelineReturn = ReturnType<typeof usePipeline>;