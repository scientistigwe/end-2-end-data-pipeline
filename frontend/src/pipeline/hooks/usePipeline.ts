// src/pipeline/hooks/usePipeline.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { useCallback } from 'react';
import { pipelineApi } from '../api/pipelineApi';
import {
  setPipelines,
  updatePipeline as updatePipelineAction,
  removePipeline,
  setError,
  setLoading
} from '../store/pipelineSlice';
import type { Pipeline, PipelineConfig } from '../types/pipeline';

export function usePipeline(pipelineId?: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Separate loading state management
  const setLoadingState = useCallback((loading: boolean) => {
    dispatch(setLoading(loading));
  }, [dispatch]);

  const handleError = useCallback((error: unknown) => {
    const errorMessage = error instanceof Error ? error.message : 'An error occurred';
    dispatch(setError(errorMessage));
    return error;
  }, [dispatch]);

  // List pipelines
  const pipelinesQuery = useQuery(
    ['pipelines'],
    async () => {
      try {
        const response = await pipelineApi.listPipelines();
        dispatch(setPipelines(response));
        return response;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      staleTime: 30000,
      cacheTime: 300000,
      retry: 3,
      onSettled: () => setLoadingState(false),
      onMutate: () => setLoadingState(true)
    }
  );

  // Get single pipeline
  const pipelineQuery = useQuery(
    ['pipeline', pipelineId],
    async () => {
      if (!pipelineId) return null;
      try {
        const response = await pipelineApi.getPipeline(pipelineId);
        dispatch(updatePipelineAction(response));
        return response;
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

  // Create pipeline
  const createPipeline = useMutation<Pipeline, Error, PipelineConfig>(
    async (config) => {
      try {
        const response = await pipelineApi.createPipeline(config);
        dispatch(updatePipelineAction(response));
        return response;
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

  // Update pipeline
  const updatePipelineConfig = useMutation(
    async ({ id, updates }: { id: string; updates: Partial<PipelineConfig> }) => {
      try {
        const response = await pipelineApi.updatePipeline(id, updates);
        dispatch(updatePipelineAction(response));
        return response;
      } catch (error) {
        throw handleError(error);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipelines']);
        if (pipelineId) {
          queryClient.invalidateQueries(['pipeline', pipelineId]);
        }
      }
    }
  );

  // Delete pipeline
  const deletePipeline = useMutation(
    async (id: string) => {
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

  // Pipeline control mutations with proper error handling
  const startPipeline = useMutation(
    async ({ id, options }: { id: string; options?: { mode?: string; params?: Record<string, unknown> } }) => {
      try {
        return await pipelineApi.startPipeline(id, options);
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  const stopPipeline = useMutation(
    async (id: string) => {
      try {
        return await pipelineApi.stopPipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  const pausePipeline = useMutation(
    async (id: string) => {
      try {
        return await pipelineApi.pausePipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  const resumePipeline = useMutation(
    async (id: string) => {
      try {
        return await pipelineApi.resumePipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  const retryPipeline = useMutation(
    async (id: string) => {
      try {
        return await pipelineApi.retryPipeline(id);
      } catch (error) {
        throw handleError(error);
      }
    }
  );

  return {
    // Queries
    pipelines: pipelinesQuery.data,
    pipeline: pipelineQuery.data,
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
    
    // Helper methods
    refetchPipelines: () => queryClient.invalidateQueries(['pipelines']),
    refetchPipeline: () => pipelineId && queryClient.invalidateQueries(['pipeline', pipelineId])
  } as const;
}

export type UsePipelineReturn = ReturnType<typeof usePipeline>;