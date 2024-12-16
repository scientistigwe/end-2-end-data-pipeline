// src/pipeline/hooks/usePipelineRuns.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { pipelineApi } from '../api/pipelineApi';
import { setPipelineRuns } from '../store/pipelineSlice';
import type { PipelineRun } from '../types/pipeline';

interface UsePipelineRunsOptions {
  limit?: number;
  page?: number;
  status?: string;
}

export function usePipelineRuns(
  pipelineId: string,
  options: UsePipelineRunsOptions = {}
) {
  const dispatch = useDispatch();

  const {
    data,
    isLoading,
    error,
    refetch
  } = useQuery<PipelineRun[]>(
    ['pipelineRuns', pipelineId, options],
    async () => {
      try {
        const response = await pipelineApi.getPipelineRuns(pipelineId, options);
        
        // Sort runs by start time, most recent first
        const sortedRuns = [...response].sort((a, b) => 
          new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
        );

        // Dispatch to Redux store
        dispatch(setPipelineRuns({ pipelineId, runs: sortedRuns }));
        
        return sortedRuns;
      } catch (error) {
        console.error('Error fetching pipeline runs:', error);
        throw error;
      }
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: 10000, // Refresh every 10 seconds
      staleTime: 5000,
      retry: 3,
      onError: (error) => {
        console.error('Error in runs query:', error);
      }
    }
  );

  const refresh = async () => {
    try {
      await refetch();
    } catch (error) {
      console.error('Error refreshing runs:', error);
    }
  };

  // Calculate some useful statistics
  const stats = data ? {
    totalRuns: data.length,
    successfulRuns: data.filter(run => run.status === 'completed').length,
    failedRuns: data.filter(run => run.status === 'failed').length,
    averageDuration: data.reduce((acc, run) => acc + (run.duration || 0), 0) / data.length
  } : null;

  return {
    runs: data || [],
    isLoading,
    error,
    refresh,
    stats,
    isEmpty: !data || data.length === 0,
    hasError: !!error
  } as const;
}

// Type inference for the hook's return type
export type UsePipelineRunsReturn = ReturnType<typeof usePipelineRuns>;