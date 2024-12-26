// src/pipeline/providers/PipelineProvider.tsx
import React, { useCallback, useMemo, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { PipelineContext } from "../context/PipelineContext";
import { usePipeline } from "../hooks/usePipeline";
import { usePipelineExecution } from "../hooks/usePipelineExecution";
import { selectPipelines } from "../store/selectors";
import type { Pipeline, PipelineConfig } from "../types/metrics";

interface PipelineProviderProps {
  children: React.ReactNode;
}

export const PipelineProvider: React.FC<PipelineProviderProps> = ({
  children,
}) => {
  const dispatch = useDispatch();
  const pipelines = useSelector(selectPipelines);

  // Use ref for selected pipeline ID
  const selectedPipelineIdRef = useRef<string | null>(null);

  // Initialize hooks
  const {
    createPipeline,
    updatePipelineConfig,
    deletePipeline,
    isLoading,
    error,
    refetchPipelines,
  } = usePipeline();

  const pipelineExecution = usePipelineExecution(
    selectedPipelineIdRef.current || ""
  );

  // Memoized callbacks
  const isPipelineRunning = useCallback(
    (id: string) => {
      return pipelines[id]?.status === "running";
    },
    [pipelines]
  );

  const getPipelineStatus = useCallback(
    (id: string) => {
      return pipelines[id]?.status;
    },
    [pipelines]
  );

  const setSelectedPipelineId = useCallback((id: string | null) => {
    selectedPipelineIdRef.current = id;
  }, []);

  const startPipeline = useCallback(
    async (id: string, options?: { mode?: string }) => {
      setSelectedPipelineId(id);
      await pipelineExecution.startPipeline.mutateAsync({
        mode: options?.mode,
      });
      await refetchPipelines();
    },
    [pipelineExecution.startPipeline, refetchPipelines]
  );

  const stopPipeline = useCallback(
    async (id: string) => {
      setSelectedPipelineId(id);
      await pipelineExecution.stopPipeline.mutateAsync();
      await refetchPipelines();
    },
    [pipelineExecution.stopPipeline, refetchPipelines]
  );

  const retryPipeline = useCallback(
    async (id: string) => {
      setSelectedPipelineId(id);
      await pipelineExecution.retryPipeline.mutateAsync();
      await refetchPipelines();
    },
    [pipelineExecution.retryPipeline, refetchPipelines]
  );

  // Memoized context value
  const value = useMemo(
    () => ({
      selectedPipelineId: selectedPipelineIdRef.current,
      setSelectedPipelineId,
      createPipeline: createPipeline.mutateAsync,
      updatePipeline: updatePipelineConfig.mutateAsync,
      deletePipeline: deletePipeline.mutateAsync,
      startPipeline,
      stopPipeline,
      retryPipeline,
      isPipelineRunning,
      getPipelineStatus,
      isLoading: isLoading || pipelineExecution.isExecuting,
      error,
    }),
    [
      setSelectedPipelineId,
      createPipeline.mutateAsync,
      updatePipelineConfig.mutateAsync,
      deletePipeline.mutateAsync,
      startPipeline,
      stopPipeline,
      retryPipeline,
      isPipelineRunning,
      getPipelineStatus,
      isLoading,
      pipelineExecution.isExecuting,
      error,
    ]
  );

  return (
    <PipelineContext.Provider value={value}>
      {children}
    </PipelineContext.Provider>
  );
};
