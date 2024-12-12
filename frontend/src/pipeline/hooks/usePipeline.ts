// src/pipeline/hooks/usePipeline.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { PipelineApi } from '../api/pipelineApi';
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
  const pipelineApi = new PipelineApi();

  // List pipelines
  const { data: pipelines, isLoading } = useQuery(
    ['pipelines'],
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await pipelineApi.listPipelines();
        dispatch(setPipelines(response));
        return response;
      } catch (error) {
        dispatch(setError(error instanceof Error ? error.message : 'Failed to fetch pipelines'));
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    },
    {
      staleTime: 30000, // Consider data stale after 30 seconds
      cacheTime: 300000, // Cache for 5 minutes
      retry: 3 // Retry failed requests 3 times
    }
  );

  // Get single pipeline
  const { data: pipeline, isLoading: isLoadingSingle } = useQuery(
    ['pipeline', pipelineId],
    async () => {
      if (!pipelineId) return null;
      const response = await pipelineApi.getPipeline(pipelineId);
      dispatch(updatePipelineAction(response));
      return response;
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
      const response = await pipelineApi.createPipeline(config);
      dispatch(updatePipelineAction(response));
      return response;
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
      const response = await pipelineApi.updatePipeline(id, updates);
      dispatch(updatePipelineAction(response));
      return response;
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
      await pipelineApi.deletePipeline(id);
      dispatch(removePipeline(id));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['pipelines']);
      }
    }
  );

  // Pipeline control mutations
  const startPipeline = useMutation(
    async ({ id, options }: { id: string; options?: { mode?: string; params?: Record<string, unknown> } }) => {
      return pipelineApi.startPipeline(id, options);
    }
  );

  const stopPipeline = useMutation(
    async (id: string) => {
      return pipelineApi.stopPipeline(id);
    }
  );

  const pausePipeline = useMutation(
    async (id: string) => {
      return pipelineApi.pausePipeline(id);
    }
  );

  const resumePipeline = useMutation(
    async (id: string) => {
      return pipelineApi.resumePipeline(id);
    }
  );

  const retryPipeline = useMutation(
    async (id: string) => {
      return pipelineApi.retryPipeline(id);
    }
  );

  return {
    // Queries
    pipelines,
    pipeline,
    isLoading: isLoading || isLoadingSingle,
    
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