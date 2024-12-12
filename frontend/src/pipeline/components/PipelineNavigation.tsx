// src/pipeline/components/PipelineNavigation.tsx
import React from "react";
import { Button } from "@/common/components/ui/button";
import { usePipelineNavigation } from "../routes/navigationUtils";

interface PipelineNavigationProps {
  pipelineId: string;
}

export const PipelineNavigation: React.FC<PipelineNavigationProps> = ({
  pipelineId,
}) => {
  const navigation = usePipelineNavigation();

  return (
    <div className="space-x-2">
      <Button
        variant="outline"
        onClick={() => navigation.goToPipelineDetails(pipelineId)}
      >
        Details
      </Button>
      <Button
        variant="outline"
        onClick={() => navigation.goToPipelineRuns(pipelineId)}
      >
        Runs
      </Button>
      <Button
        variant="outline"
        onClick={() => navigation.goToPipelineMetrics(pipelineId)}
      >
        Metrics
      </Button>
    </div>
  );
};
