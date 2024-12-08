// src/components/pipeline/PipelineRuns.tsx
import React from "react";
import { Card } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import type { PipelineRun } from "../types/pipeline";

interface PipelineRunsProps {
  runs: PipelineRun[];
  onRunClick: (runId: string) => void;
  className?: string;
}

export const PipelineRuns: React.FC<PipelineRunsProps> = ({
  runs,
  onRunClick,
  className = "",
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "running":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {runs.map((run) => (
        <Card
          key={run.id}
          className="p-4 hover:bg-gray-50 cursor-pointer"
          onClick={() => onRunClick(run.id)}
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Badge className={getStatusColor(run.status)}>
                  {run.status}
                </Badge>
                <span className="text-sm text-gray-500">
                  Run #{run.id.slice(0, 8)}
                </span>
              </div>
              <div>
                <p className="text-sm text-gray-600">
                  Started: {new Date(run.startedAt).toLocaleString()}
                </p>
                {run.completedAt && (
                  <p className="text-sm text-gray-600">
                    Completed: {new Date(run.completedAt).toLocaleString()}
                  </p>
                )}
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm font-medium">
                Duration: {(run.duration || 0) / 1000}s
              </p>
              {run.error && (
                <p className="text-sm text-red-600">
                  Error: {run.error.message}
                </p>
              )}
            </div>
          </div>

          <div className="mt-4">
            <h4 className="text-sm font-medium mb-2">Step Progress</h4>
            <div className="space-y-2">
              {run.steps.map((step) => (
                <div key={step.id} className="flex items-center space-x-2">
                  <Badge
                    variant="outline"
                    className={getStatusColor(step.status)}
                  >
                    {step.status}
                  </Badge>
                  <span className="text-sm">{step.id}</span>
                  {step.duration && (
                    <span className="text-sm text-gray-500">
                      ({(step.duration / 1000).toFixed(1)}s)
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
