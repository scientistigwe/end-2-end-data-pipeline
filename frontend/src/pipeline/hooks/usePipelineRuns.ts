// src/pipeline/hooks/usePipelineRuns.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { pipelineApi } from '../api/pipelineApi';
import { setPipelineRuns } from '../store/pipelineSlice';
import type { 
  PipelineRun, 
  PipelineError, 
  PipelineStatus,
  PipelineStepRun
} from '../types';
import { PIPELINE_CONSTANTS } from '../constants';

interface UsePipelineRunsOptions {
  limit?: number;
  page?: number;
  status?: PipelineStatus;
  sortBy?: keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS;
  sortOrder?: keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS;
}

interface PipelineRunStats {
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
  averageDuration: number;
  successRate: number;
  recentFailures: number;  // Failures in last 24h
  lastSuccessfulRun?: PipelineRun;
  lastFailedRun?: PipelineRun;
  stepSuccessRate: Record<string, number>;
  averageStepDurations: Record<string, number>;
  commonFailureSteps: Array<{ stepId: string; failureCount: number }>;
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
    refetch,
    isFetching
  } = useQuery<PipelineRun[], PipelineError>(
    ['pipelineRuns', pipelineId, options],
    async () => {
      try {
        const response = await pipelineApi.getPipelineRuns(pipelineId, options);
        const runs = response.data;
        
        // Sort runs based on options
        const sortedRuns = sortPipelineRuns(runs, options.sortBy, options.sortOrder);

        // Format timestamps and ensure data consistency
        const formattedRuns = formatPipelineRuns(sortedRuns);

        // Dispatch to Redux store
        dispatch(setPipelineRuns({ pipelineId, runs: formattedRuns }));
        
        return formattedRuns;
      } catch (error) {
        const pipelineError = error as PipelineError;
        console.error('Error fetching pipeline runs:', pipelineError);
        throw pipelineError;
      }
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: (data) => shouldRefetch(data) ? 
        PIPELINE_CONSTANTS.RUNS.REFRESH.ACTIVE_INTERVAL : 
        PIPELINE_CONSTANTS.RUNS.REFRESH.INTERVAL,
      staleTime: PIPELINE_CONSTANTS.RUNS.REFRESH.STALE_TIME,
      retry: PIPELINE_CONSTANTS.RUNS.RETRY.COUNT,
      onError: (error: PipelineError) => {
        console.error('Error in runs query:', error);
      }
    }
  );

  // Helper function to determine if we should refetch
  const shouldRefetch = (runs: PipelineRun[] | undefined): boolean => {
    if (!runs) return false;
    return runs.some(run => run.status === PIPELINE_CONSTANTS.STATUS.RUNNING || 
                          run.status === PIPELINE_CONSTANTS.STATUS.PAUSED);
  };

  // Sort pipeline runs based on options
  const sortPipelineRuns = (
    runs: PipelineRun[],
    sortBy?: keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS,
    sortOrder?: keyof typeof PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS
  ): PipelineRun[] => {
    return [...runs].sort((a, b) => {
      let comparison = 0;
      const sortField = sortBy ? PIPELINE_CONSTANTS.RUNS.SORTING.FIELDS[sortBy] : 'startedAt';
      const order = sortOrder ? 
        PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS[sortOrder] : 
        PIPELINE_CONSTANTS.RUNS.SORTING.ORDERS.DESC;
      
      switch (sortField) {
        case 'completedAt':
          comparison = (new Date(b.completedAt || 0).getTime()) - 
                      (new Date(a.completedAt || 0).getTime());
          break;
        case 'duration':
          comparison = (b.duration || 0) - (a.duration || 0);
          break;
        case 'startedAt':
        default:
          comparison = new Date(b.startedAt).getTime() - 
                      new Date(a.startedAt).getTime();
      }

      return order === 'asc' ? -comparison : comparison;
    });
  };

  // Rest of the code remains the same...
  const formatPipelineRuns = (runs: PipelineRun[]): PipelineRun[] => {
    return runs.map(run => ({
      ...run,
      startedAt: new Date(run.startedAt).toISOString(),
      completedAt: run.completedAt ? new Date(run.completedAt).toISOString() : undefined,
      duration: run.completedAt ? 
        new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime() : 
        undefined,
      steps: formatPipelineSteps(run.steps)
    }));
  };

  const formatPipelineSteps = (steps: PipelineStepRun[]): PipelineStepRun[] => {
    return steps.map(step => ({
      ...step,
      startedAt: new Date(step.startedAt).toISOString(),
      completedAt: step.completedAt ? 
        new Date(step.completedAt).toISOString() : 
        undefined,
      duration: step.completedAt ? 
        new Date(step.completedAt).getTime() - new Date(step.startedAt).getTime() : 
        undefined
    }));
  };

  const calculateStats = (runs: PipelineRun[]): PipelineRunStats => {
    const last24Hours = Date.now() - 24 * 60 * 60 * 1000;
    
    const successfulRuns = runs.filter(run => 
      run.status === PIPELINE_CONSTANTS.STATUS.COMPLETED);
    const failedRuns = runs.filter(run => 
      run.status === PIPELINE_CONSTANTS.STATUS.FAILED);
    const recentFailures = failedRuns.filter(
      run => new Date(run.startedAt).getTime() > last24Hours
    ).length;

    // Rest of calculateStats remains the same...
    const stepStats = runs.reduce((acc, run) => {
      run.steps.forEach(step => {
        if (!acc[step.stepId]) {
          acc[step.stepId] = {
            total: 0,
            successful: 0,
            durations: []
          };
        }
        
        acc[step.stepId].total++;
        if (step.status === PIPELINE_CONSTANTS.STATUS.COMPLETED) {
          acc[step.stepId].successful++;
        }
        if (step.duration) {
          acc[step.stepId].durations.push(step.duration);
        }
      });
      return acc;
    }, {} as Record<string, { total: number; successful: number; durations: number[] }>);

    const stepSuccessRate: Record<string, number> = {};
    const averageStepDurations: Record<string, number> = {};
    
    Object.entries(stepStats).forEach(([stepId, stats]) => {
      stepSuccessRate[stepId] = (stats.successful / stats.total) * 100;
      averageStepDurations[stepId] = stats.durations.reduce((a, b) => a + b, 0) / 
        stats.durations.length || 0;
    });

    const failureSteps = runs
      .filter(run => run.status === PIPELINE_CONSTANTS.STATUS.FAILED)
      .reduce((acc, run) => {
        const failedStep = run.steps.find(
          step => step.status === PIPELINE_CONSTANTS.STATUS.FAILED
        )?.stepId;
        if (failedStep) {
          acc[failedStep] = (acc[failedStep] || 0) + 1;
        }
        return acc;
      }, {} as Record<string, number>);

    const commonFailureSteps = Object.entries(failureSteps)
      .map(([stepId, count]) => ({ stepId, failureCount: count }))
      .sort((a, b) => b.failureCount - a.failureCount)
      .slice(0, 5);

    return {
      totalRuns: runs.length,
      successfulRuns: successfulRuns.length,
      failedRuns: failedRuns.length,
      averageDuration: runs.reduce((acc, run) => acc + (run.duration || 0), 0) / runs.length || 0,
      successRate: (successfulRuns.length / runs.length) * 100 || 0,
      recentFailures,
      lastSuccessfulRun: successfulRuns[0],
      lastFailedRun: failedRuns[0],
      stepSuccessRate,
      averageStepDurations,
      commonFailureSteps
    };
  };

  const stats = data ? calculateStats(data) : null;

  // Helper methods
  const getRunById = (runId: string): PipelineRun | undefined => {
    return data?.find(run => run.id === runId);
  };

  const getLatestRun = (): PipelineRun | undefined => {
    return data?.[0];
  };

  const getRunsByStatus = (status: PipelineStatus): PipelineRun[] => {
    return data?.filter(run => run.status === status) || [];
  };

  return {
    runs: data || [],
    isLoading,
    isFetching,
    error,
    refresh: refetch,
    stats,
    getRunById,
    getLatestRun,
    getRunsByStatus,
    isEmpty: !data || data.length === 0,
    hasError: !!error,
    hasActiveRun: data?.some(run => 
      run.status === PIPELINE_CONSTANTS.STATUS.RUNNING
    ) ?? false,
    runCount: data?.length ?? 0,
    lastRun: getLatestRun(),
    lastSuccessfulRun: stats?.lastSuccessfulRun,
    lastFailedRun: stats?.lastFailedRun
  } as const;
}

export type UsePipelineRunsReturn = ReturnType<typeof usePipelineRuns>;