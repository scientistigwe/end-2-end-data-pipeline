// src/hooks/pipeline/types.ts
import { UseMutateFunction, RefetchOptions, RefetchQueryFilters } from 'react-query';
import { 
  ApiResponse, 
  PipelineConfig, 
  PipelineStatus,
  PipelineResponse 
} from '../../services/api/types';

export interface PipelineLogs {
  logs: Array<{
    timestamp: string;
    level: 'info' | 'warn' | 'error';
    message: string;
    metadata?: Record<string, unknown>;
  }>;
}

export interface UsePipelineProps {
  pipelineId?: string;
  onError?: (error: Error) => void;
  onSuccess?: <T>(data: T) => void;
}

export interface UsePipelineResult {
  // Actions
  startPipeline: UseMutateFunction<
    ApiResponse<PipelineResponse>,
    Error,
    PipelineConfig,
    unknown
  >;
  stopPipeline: UseMutateFunction<ApiResponse<void>, Error, void, unknown>;
  refreshStatus: <TPageData>(options?: RefetchOptions & RefetchQueryFilters<TPageData>) => Promise<unknown>;
  refreshLogs: <TPageData>(options?: RefetchOptions & RefetchQueryFilters<TPageData>) => Promise<unknown>;

  // State
  status: PipelineStatus;
  pipelineStatus: PipelineResponse | null | undefined;
  logs: PipelineLogs | null | undefined;

  // Loading States
  isStarting: boolean;
  isStopping: boolean;
  isLoading: boolean;

  // Error State
  error: Error | null;
}