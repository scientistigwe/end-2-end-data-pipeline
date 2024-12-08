// src/components/pipeline/PipelineList.tsx
import React from "react";
import { Card } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Play, Square, Settings, Trash2 } from "lucide-react";
import type { Pipeline } from "../types/pipeline";

interface PipelineListProps {
  pipelines: Pipeline[];
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string) => void;
  className?: string;
}

export const PipelineList: React.FC<PipelineListProps> = ({
  pipelines,
  onStart,
  onStop,
  onEdit,
  onDelete,
  onSelect,
  className = "",
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "stopped":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {pipelines.map((pipeline) => (
        <Card
          key={pipeline.id}
          className="p-4 hover:bg-gray-50 cursor-pointer"
          onClick={() => onSelect(pipeline.id)}
        >
          <div className="flex justify-between items-start">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-medium">{pipeline.name}</h3>
                <Badge className={getStatusColor(pipeline.status)}>
                  {pipeline.status}
                </Badge>
              </div>
              <p className="text-sm text-gray-600">{pipeline.description}</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">{pipeline.mode}</Badge>
                {pipeline.tags?.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex space-x-2">
              {pipeline.status === "running" ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onStop(pipeline.id);
                  }}
                >
                  <Square className="h-4 w-4 mr-1" />
                  Stop
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    onStart(pipeline.id);
                  }}
                >
                  <Play className="h-4 w-4 mr-1" />
                  Start
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(pipeline.id);
                }}
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-red-600 hover:text-red-700"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(pipeline.id);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Total Runs</p>
              <p className="font-medium">{pipeline.stats.totalRuns}</p>
            </div>
            <div>
              <p className="text-gray-500">Success Rate</p>
              <p className="font-medium">
                {(
                  (pipeline.stats.successfulRuns / pipeline.stats.totalRuns) *
                  100
                ).toFixed(1)}
                %
              </p>
            </div>
            <div>
              <p className="text-gray-500">Avg Duration</p>
              <p className="font-medium">
                {(pipeline.stats.averageDuration / 1000).toFixed(1)}s
              </p>
            </div>
            <div>
              <p className="text-gray-500">Last Run</p>
              <p className="font-medium">
                {pipeline.lastRun
                  ? new Date(pipeline.lastRun).toLocaleString()
                  : "Never"}
              </p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
