// src/pipeline/hooks/usePipelineLogs.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { pipelineApi } from '../api/pipelineApi';
import { setPipelineLogs } from '../store/pipelineSlice';
import type { PipelineLogs } from '../types/pipeline';

interface UsePipelineLogsOptions {
  startTime?: string;
  endTime?: string;
  level?: string;
  limit?: number;
  page?: number;
}

export function usePipelineLogs(
  pipelineId: string,
  options: UsePipelineLogsOptions = {}
) {
  const dispatch = useDispatch();

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching
  } = useQuery<PipelineLogs, Error>(
    ['pipelineLogs', pipelineId, options],
    async () => {
      try {
        const response = await pipelineApi.getPipelineLogs(pipelineId, options);
        dispatch(setPipelineLogs({ pipelineId, logs: response }));
        return response;
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error('Failed to fetch pipeline logs');
      }
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval: 5000,
      staleTime: 4000,
      retry: 3,
      onError: (error) => {
        console.error('Error fetching pipeline logs:', error);
      }
    }
  );

  const downloadLogs = async (format: 'txt' | 'json' = 'txt') => {
    try {
      const logs = await pipelineApi.getPipelineLogs(pipelineId, {
        ...options,
        limit: undefined // Get all logs when downloading
      });

      const content = format === 'json' 
        ? JSON.stringify(logs, null, 2)
        : logs.logs.map(log => 
            `[${new Date(log.timestamp).toISOString()}] [${log.level}] ${log.step ? `[${log.step}] ` : ''}${log.message}`
          ).join('\n');

      const fileType = format === 'json' ? 'application/json' : 'text/plain';
      const blob = new Blob([content], { type: fileType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const timestamp = new Date().toISOString().split('T')[0];
      
      a.href = url;
      a.download = `pipeline-${pipelineId}-logs-${timestamp}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading logs:', error);
      throw new Error('Failed to download logs');
    }
  };

  return {
    logs: data,
    isLoading,
    isFetching,
    error,
    refresh: refetch,
    download: downloadLogs,
    hasError: !!error,
    isEmpty: !data || data.logs.length === 0
  } as const;
}

// Type inference for the hook's return type
export type UsePipelineLogsReturn = ReturnType<typeof usePipelineLogs>;