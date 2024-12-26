// src/pipeline/hooks/usePipelineLogs.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { useState, useEffect } from 'react';
import { pipelineApi } from '../api/pipelineApi';
import { setPipelineLogs } from '../store/pipelineSlice';
import type { PipelineLogs, PipelineError, LogLevel } from '../types';
import { PIPELINE_CONSTANTS } from '../constants';

interface UsePipelineLogsOptions {
  startTime?: string;
  endTime?: string;
  level?: keyof typeof PIPELINE_CONSTANTS.LOG_LEVELS;
  limit?: number;
  page?: number;
}

interface FormattedLog {
  timestamp: string;
  level: LogLevel;
  step?: string;
  message: string;
  metadata?: Record<string, unknown>;
}

// Helper Functions
const validateLogLevel = (level: string): LogLevel => {
  const validLevels = Object.values(PIPELINE_CONSTANTS.LOG_LEVELS);
  return validLevels.includes(level as LogLevel) 
    ? level as LogLevel 
    : PIPELINE_CONSTANTS.LOG_LEVELS.INFO;
};

const formatLog = (log: FormattedLog): FormattedLog => ({
  ...log,
  timestamp: new Date(log.timestamp).toISOString(),
  level: validateLogLevel(log.level)
});

const shouldRefetch = (hasError: boolean): boolean => {
  if (hasError) return false;
  return true;
};

const formatLogsForDownload = (logs: FormattedLog[]): string => {
  return logs.map(log => 
    `[${new Date(log.timestamp).toISOString()}] [${log.level}] ${
      log.step ? `[${log.step}] ` : ''
    }${log.message}`
  ).join('\n');
};

const downloadFile = async (
  content: string, 
  format: 'txt' | 'json',
  pipelineId: string
): Promise<void> => {
  const blob = new Blob(
    [content], 
    { type: format === 'json' ? 'application/json' : 'text/plain' }
  );
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  const timestamp = new Date().toISOString().split('T')[0];
  
  try {
    a.href = url;
    a.download = `pipeline-${pipelineId}-logs-${timestamp}.${format}`;
    document.body.appendChild(a);
    a.click();
  } finally {
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
};

export function usePipelineLogs(
  pipelineId: string,
  options: UsePipelineLogsOptions = {}
) {
  const dispatch = useDispatch();

  // Custom hook to handle refetch interval
  const useRefetchInterval = () => {
    const [shouldRefetch, setShouldRefetch] = useState(true);

    useEffect(() => {
      if (pipelineId) {
        setShouldRefetch(true);
      }
      return () => setShouldRefetch(false);
    }, [pipelineId]);

    return shouldRefetch ? PIPELINE_CONSTANTS.METRICS.REFRESH_INTERVAL : undefined;
  };

  const refetchInterval = useRefetchInterval();

  const {
    data,
    isLoading,
    error,
    refetch,
    isFetching
  } = useQuery<PipelineLogs, PipelineError>(
    ['pipelineLogs', pipelineId, options],
    async () => {
      try {
        const response = await pipelineApi.getPipelineLogs(pipelineId, {
          ...options,
          level: options.level ? PIPELINE_CONSTANTS.LOG_LEVELS[options.level] : undefined,
          limit: options.limit || PIPELINE_CONSTANTS.PAGINATION.DEFAULT_PAGE_SIZE
        });

        const formattedLogs = {
          ...response.data,
          logs: response.data.logs.map(formatLog)
        };
        
        dispatch(setPipelineLogs({ 
          pipelineId, 
          logs: formattedLogs 
        }));
        
        return formattedLogs;
      } catch (error) {
        const pipelineError = error as PipelineError;
        console.error('Error fetching pipeline logs:', pipelineError);
        throw pipelineError;
      }
    },
    {
      enabled: Boolean(pipelineId),
      refetchInterval,
      staleTime: PIPELINE_CONSTANTS.METRICS.REFRESH_INTERVAL / 2,
      retry: PIPELINE_CONSTANTS.STEPS.MAX_RETRIES,
      onError: (error: PipelineError) => {
        console.error('Error in logs query:', error);
      }
    }
  );

  const downloadLogs = async (format: 'txt' | 'json' = 'txt') => {
    try {
      const response = await pipelineApi.getPipelineLogs(pipelineId, {
        ...options,
        limit: undefined // Get all logs for download
      });

      const logs = response.data;
      const content = format === 'json' 
        ? JSON.stringify(logs, null, 2)
        : formatLogsForDownload(logs.logs);

      await downloadFile(content, format, pipelineId);
    } catch (error) {
      const pipelineError = error as PipelineError;
      console.error('Error downloading logs:', pipelineError);
      throw pipelineError;
    }
  };

  const getLogsByLevel = (level: LogLevel): FormattedLog[] => {
    return data?.logs.filter(log => log.level === level) || [];
  };

  return {
    logs: data,
    isLoading,
    isFetching,
    error,
    refresh: refetch,
    download: downloadLogs,
    hasError: !!error,
    isEmpty: !data || data.logs.length === 0,
    // Additional utility methods
    getLogsByLevel,
    totalLogs: data?.logs.length ?? 0,
    hasWarnings: data?.logs.some(log => log.level === PIPELINE_CONSTANTS.LOG_LEVELS.WARN) ?? false,
    hasErrors: data?.logs.some(log => log.level === PIPELINE_CONSTANTS.LOG_LEVELS.ERROR) ?? false,
  } as const;
}

export type UsePipelineLogsReturn = ReturnType<typeof usePipelineLogs>;