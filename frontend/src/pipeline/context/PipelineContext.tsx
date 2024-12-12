// src/pipeline/context/PipelineContext.tsx
import { createContext, useContext } from 'react';
import type { Pipeline, PipelineConfig, PipelineStatus } from '../types/pipeline';

interface PipelineContextValue {
  // Pipeline State
  selectedPipelineId: string | null;
  setSelectedPipelineId: (id: string | null) => void;
  
  // Pipeline Operations
  createPipeline: (config: PipelineConfig) => Promise<Pipeline>;
  updatePipeline: (id: string, updates: Partial<PipelineConfig>) => Promise<Pipeline>;
  deletePipeline: (id: string) => Promise<void>;
  
  // Pipeline Execution
  startPipeline: (id: string, options?: { mode?: string }) => Promise<void>;
  stopPipeline: (id: string) => Promise<void>;
  retryPipeline: (id: string) => Promise<void>;
  
  // Pipeline Status
  isPipelineRunning: (id: string) => boolean;
  getPipelineStatus: (id: string) => PipelineStatus | undefined;
  
  // Loading States
  isLoading: boolean;
  error: string | null;
}

const PipelineContext = createContext<PipelineContextValue | undefined>(undefined);

export function usePipelineContext() {
  const context = useContext(PipelineContext);
  if (context === undefined) {
    throw new Error('usePipelineContext must be used within a PipelineProvider');
  }
  return context;
}

export { PipelineContext };


