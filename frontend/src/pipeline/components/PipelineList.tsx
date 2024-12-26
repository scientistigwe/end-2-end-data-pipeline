// src/pipeline/components/PipelineList.tsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import type { Pipeline } from "../types/metrics";
import { getStatusColor } from "../utils/formatters";

interface PipelineListProps {
  pipelines: Pipeline[];
  onPipelineSelect?: (id: string) => void;
  className?: string;
  isLoading?: boolean;
}

export const PipelineList: React.FC<PipelineListProps> = ({
  pipelines,
  onPipelineSelect,
  className = "",
  isLoading = false,
}) => {
  const navigate = useNavigate();

  const handlePipelineClick = (id: string) => {
    if (onPipelineSelect) {
      onPipelineSelect(id);
    } else {
      navigate(`/pipelines/${id}`);
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {pipelines.map((pipeline) => (
        <Card
          key={pipeline.id}
          className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
          onClick={() => handlePipelineClick(pipeline.id)}
        >
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-medium">{pipeline.name}</h3>
                <Badge className={getStatusColor(pipeline.status)}>
                  {pipeline.status}
                </Badge>
              </div>
              {pipeline.description && (
                <p className="text-sm text-gray-600">{pipeline.description}</p>
              )}
              <div className="flex space-x-2 text-sm text-gray-500">
                <span>
                  Created: {new Date(pipeline.createdAt).toLocaleDateString()}
                </span>
                <span>•</span>
                <span>Mode: {pipeline.mode}</span>
              </div>
            </div>

            <div className="text-right">
              <div className="text-sm text-gray-600">
                Last run:{" "}
                {pipeline.lastRun
                  ? new Date(pipeline.lastRun).toLocaleString()
                  : "Never"}
              </div>
              {pipeline.stats && (
                <div className="mt-2 text-sm">
                  Success rate:{" "}
                  {(
                    (pipeline.stats.successfulRuns / pipeline.stats.totalRuns) *
                    100
                  ).toFixed(1)}
                  %
                </div>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
