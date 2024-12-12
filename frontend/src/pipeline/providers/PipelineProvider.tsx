// src/pipeline/providers/PipelineProvider.tsx
import React, { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { PipelineContext } from '../context/PipelineContext';
import { usePipeline } from '../hooks/usePipeline';
import { usePipelineExecution } from '../hooks/usePipelineExecution';
import { selectPipelines } from '../store/selectors';
import type { Pipeline, PipelineConfig } from '../types/pipeline';

interface PipelineProviderProps {
  children: React.ReactNode;
}

export const PipelineProvider: React.FC<PipelineProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const pipelines = useSelector(selectPipelines);
  
  const {
    createPipeline,
    updatePipelineConfig,
    deletePipeline,
    isLoading,
    error
  } = usePipeline();

  const {
    startPipeline: startPipelineExecution,
    stopPipeline: stopPipelineExecution,
    retryPipeline: retryPipelineExecution
  } = usePipelineExecution(selectedPipelineId || '');

  const isPipelineRunning = useCallback((id: string) => {
    return pipelines[id]?.status === 'running';
  }, [pipelines]);

  const getPipelineStatus = useCallback((id: string) => {
    return pipelines[id]?.status;
  }, [pipelines]);

  const startPipeline = useCallback(async (id: string, options?: { mode?: string }) => {
    setSelectedPipelineId(id);
    await startPipelineExecution.mutateAsync(options);
  }, [startPipelineExecution]);

  const stopPipeline = useCallback(async (id: string) => {
    setSelectedPipelineId(id);
    await stopPipelineExecution.mutateAsync();
  }, [stopPipelineExecution]);

  const retryPipeline = useCallback(async (id: string) => {
    setSelectedPipelineId(id);
    await retryPipelineExecution.mutateAsync();
  }, [retryPipelineExecution]);

  const value = {
    selectedPipelineId,
    setSelectedPipelineId,
    createPipeline: createPipeline.mutateAsync,
    updatePipeline: updatePipelineConfig.mutateAsync,
    deletePipeline: deletePipeline.mutateAsync,
    startPipeline,
    stopPipeline,
    retryPipeline,
    isPipelineRunning,
    getPipelineStatus,
    isLoading,
    error
  };

  return (
    <PipelineContext.Provider value={value}>
      {children}
    </PipelineContext.Provider>
  );
};
