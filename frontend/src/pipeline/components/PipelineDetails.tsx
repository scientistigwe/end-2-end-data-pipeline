// src/components/pipeline/PipelineDetails.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "../../components/ui/tabs";
import { PipelineMetricsChart } from "../PipelineMetricsChart";
import { PipelineRuns } from "../PipelineRuns";
import { PipelineLogs } from "../PipelineLogs";
import type { Pipeline, PipelineMetrics, PipelineRun } from "../types/pipeline";

interface PipelineDetailsProps {
  pipeline: Pipeline;
  runs: PipelineRun[];
  metrics: PipelineMetrics[];
  onRunClick: (runId: string) => void;
  className?: string;
}

export const PipelineDetails: React.FC<PipelineDetailsProps> = ({
  pipeline,
  runs,
  metrics,
  onRunClick,
  className = "",
}) => {
  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold">{pipeline.name}</h2>
              <p className="text-gray-600">{pipeline.description}</p>
            </div>
            <Badge className="text-lg">{pipeline.status}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm text-gray-600">Success Rate</h3>
              <p className="text-2xl font-bold">
                {(
                  (pipeline.stats.successfulRuns / pipeline.stats.totalRuns) *
                  100
                ).toFixed(1)}
                %
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm text-gray-600">Total Runs</h3>
              <p className="text-2xl font-bold">{pipeline.stats.totalRuns}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm text-gray-600">Avg Duration</h3>
              <p className="text-2xl font-bold">
                {(pipeline.stats.averageDuration / 1000).toFixed(1)}s
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm text-gray-600">Uptime</h3>
              <p className="text-2xl font-bold">
                {(pipeline.stats.uptime * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="metrics">
        <TabsList>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="runs">Runs History</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics">
          <PipelineMetricsChart metrics={metrics} />
        </TabsContent>

        <TabsContent value="runs">
          <PipelineRuns runs={runs} onRunClick={onRunClick} />
        </TabsContent>

        <TabsContent value="logs">
          <PipelineLogs pipelineId={pipeline.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
};
