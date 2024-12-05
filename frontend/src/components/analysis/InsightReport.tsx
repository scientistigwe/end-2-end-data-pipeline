// src/components/analysis/AnalysisStatus.tsx
import React from "react";
import { Progress } from "@/components/ui/progress";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { AlertCircle, CheckCircle, Clock, Play } from "lucide-react";
import type { AnalysisResult } from "../../types/analysis";

interface AnalysisStatusProps {
  analysis: AnalysisResult;
  className?: string;
}

export const AnalysisStatus: React.FC<AnalysisStatusProps> = ({
  analysis,
  className = "",
}) => {
  const getStatusIcon = () => {
    switch (analysis.status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case "running":
        return <Play className="h-5 w-5 text-blue-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Analysis Status</h3>
          {getStatusIcon()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex justify-between text-sm">
            <span>Progress</span>
            <span>{analysis.progress}%</span>
          </div>
          <Progress value={analysis.progress} />

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Started</span>
              <span>{new Date(analysis.startedAt).toLocaleString()}</span>
            </div>
            {analysis.completedAt && (
              <div className="flex justify-between">
                <span>Completed</span>
                <span>{new Date(analysis.completedAt).toLocaleString()}</span>
              </div>
            )}
            {analysis.error && (
              <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-md">
                {analysis.error}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
