// src/pipeline/components/PipelineExecutionControls.tsx
import React from 'react';
import { Button } from '@/common/components/ui/button';
import { usePipelineContext } from '../context/PipelineContext';

interface PipelineExecutionControlsProps {
  pipelineId: string;
}

export const PipelineExecutionControls: React.FC<PipelineExecutionControlsProps> = ({
  pipelineId
}) => {
  const {
    startPipeline,
    stopPipeline,
    retryPipeline,
    isPipelineRunning,
    getPipelineStatus
  } = usePipelineContext();

  const status = getPipelineStatus(pipelineId);
  const isRunning = isPipelineRunning(pipelineId);

  return (
    <div className="space-x-2">
      {!isRunning && (
        <Button
          onClick={() => startPipeline(pipelineId)}
          disabled={status === 'running'}
        >
          Start Pipeline
        </Button>
      )}
      
      {isRunning && (
        <Button
          onClick={() => stopPipeline(pipelineId)}
          variant="destructive"
        >
          Stop Pipeline
        </Button>
      )}
      
      {status === 'failed' && (
        <Button
          onClick={() => retryPipeline(pipelineId)}
          variant="outline"
        >
          Retry Pipeline
        </Button>
      )}
    </div>
  );
};