// src/pipeline/pages/PipelineDetailsPage.tsx
import React from "react";
import { useParams } from "react-router-dom";
import { PipelineDetails } from "../components/PipelineDetails";
import { PipelineExecutionControls } from "../components/PipelineExecutionControls";
import { PipelineBreadcrumbs } from "../components/PipelineBreadcrumbs";
import { usePipeline } from "../hooks/usePipeline";
import { usePipelineExecution } from "../hooks/usePipelineExecution";

export const PipelineDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { pipeline, isLoading } = usePipeline(id);
  const execution = usePipelineExecution(id!);

  if (isLoading || !pipeline) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <PipelineBreadcrumbs />

      <div className="flex justify-between items-start">
        <h1 className="text-2xl font-bold">{pipeline.name}</h1>
        <PipelineExecutionControls
          pipelineId={id!}
          status={pipeline.status}
          onStart={execution.startPipeline}
          onStop={execution.stopPipeline}
          onRetry={execution.retryPipeline}
        />
      </div>

      <PipelineDetails pipeline={pipeline} />
    </div>
  );
};
