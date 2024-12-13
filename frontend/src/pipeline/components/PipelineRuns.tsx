import React from "react";
import { Card } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { usePipelineRuns } from "../hooks/usePipelineRuns";
import { getStatusColor } from "../utils/formatters";
import { dateUtils } from "@/common";

interface PipelineRunsProps {
  pipelineId: string;
  className?: string;
}

export const PipelineRuns: React.FC<PipelineRunsProps> = ({
  pipelineId,
  className = "",
}) => {
  const { runs, isLoading, hasError, refresh, stats, isEmpty } =
    usePipelineRuns(pipelineId);

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-pulse">Loading runs...</div>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-500 mb-2">Failed to load pipeline runs</p>
        <button
          onClick={() => refresh()}
          className="text-sm text-blue-500 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="p-4 text-center text-gray-500">
        No pipeline runs available
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {stats && (
        <Card className="p-4">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <h4 className="text-sm font-medium text-gray-500">Total Runs</h4>
              <p className="text-2xl font-bold">{stats.totalRuns}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">
                Success Rate
              </h4>
              <p className="text-2xl font-bold">
                {((stats.successfulRuns / stats.totalRuns) * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">Failed Runs</h4>
              <p className="text-2xl font-bold">{stats.failedRuns}</p>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-500">
                Avg Duration
              </h4>
              <p className="text-2xl font-bold">
                {dateUtils.formatDetailedDuration(stats.averageDuration)}
              </p>
            </div>
          </div>
        </Card>
      )}

      {runs.map((run) => (
        <Card key={run.id} className="p-4">
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
              <div className="text-sm text-gray-600">
                <p>Started: {dateUtils.formatDate(run.startedAt, { includeTime: true })}</p>
                {run.completedAt && (
                  <p>Completed: {dateUtils.formatDate(run.completedAt, { includeTime: true })}</p>
                )}
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm font-medium">
                Duration: {dateUtils.formatDetailedDuration(run.duration || 0)}
              </p>
              {run.error && (
                <p className="text-sm text-red-600 mt-2">
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
                  <span className="text-sm">{step.stepId}</span>
                  {step.duration && (
                    <span className="text-sm text-gray-500">
                      ({dateUtils.formatDetailedDuration(step.duration)})
                    </span>
                  )}
                  {step.error && (
                    <span className="text-sm text-red-600">
                      {step.error.message}
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