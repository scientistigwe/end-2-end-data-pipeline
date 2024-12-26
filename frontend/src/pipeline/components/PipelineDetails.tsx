// src/pipeline/components/PipelineDetails.tsx
import React, { useMemo } from "react";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/common/components/ui/tabs";
import { PipelineMetricsChart } from "../components/PipelineMetricsChart";
import { PipelineRuns } from "./PipelineRuns";
import { PipelineLogs } from "./PipelineLogs";
import type { Pipeline } from "../types/metrics";
import { getStatusColor } from "../utils/formatters";

interface PipelineDetailsProps {
  pipeline: Pipeline;
  className?: string;
}

export const PipelineDetails: React.FC<PipelineDetailsProps> = ({
  pipeline,
  className = "",
}) => {
  const metrics = useMemo(() => {
    const successRate = pipeline.stats.totalRuns
      ? (pipeline.stats.successfulRuns / pipeline.stats.totalRuns) * 100
      : 0;

    const avgDuration = pipeline.stats.averageDuration
      ? (pipeline.stats.averageDuration / 1000).toFixed(1)
      : "0";

    return {
      successRate: `${successRate.toFixed(1)}%`,
      totalRuns: pipeline.stats.totalRuns,
      avgDuration: `${avgDuration}s`,
      lastRun: pipeline.lastRun
        ? new Date(pipeline.lastRun).toLocaleString()
        : "Never",
    };
  }, [pipeline.stats, pipeline.lastRun]);

  return (
    <div className={`space-y-6 ${className}`}>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold">{pipeline.name}</h2>
              <p className="text-gray-600">{pipeline.description}</p>
            </div>
            <Badge className={getStatusColor(pipeline.status)}>
              {pipeline.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <MetricCard title="Success Rate" value={metrics.successRate} />
            <MetricCard title="Total Runs" value={metrics.totalRuns} />
            <MetricCard title="Avg Duration" value={metrics.avgDuration} />
            <MetricCard title="Last Run" value={metrics.lastRun} />
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">
                    Configuration
                  </h3>
                  <dl className="mt-2 space-y-2">
                    <div>
                      <dt className="text-sm font-medium">Mode</dt>
                      <dd className="text-sm text-gray-600">{pipeline.mode}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium">Created</dt>
                      <dd className="text-sm text-gray-600">
                        {new Date(pipeline.createdAt).toLocaleString()}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium">Steps</dt>
                      <dd className="text-sm text-gray-600">
                        {pipeline.steps.length} steps
                      </dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">
                    Execution
                  </h3>
                  <dl className="mt-2 space-y-2">
                    <div>
                      <dt className="text-sm font-medium">Current Step</dt>
                      <dd className="text-sm text-gray-600">
                        {pipeline.currentStep || "Not running"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium">Progress</dt>
                      <dd className="text-sm text-gray-600">
                        {pipeline.progress}%
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium">Attempts</dt>
                      <dd className="text-sm text-gray-600">
                        {pipeline.attempts}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics">
          <PipelineMetricsChart pipelineId={pipeline.id} />
        </TabsContent>

        <TabsContent value="runs">
          <PipelineRuns pipelineId={pipeline.id} />
        </TabsContent>

        <TabsContent value="logs">
          <PipelineLogs pipelineId={pipeline.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

interface MetricCardProps {
  title: string;
  value: string | number;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value }) => (
  <div className="p-4 bg-gray-50 rounded-lg">
    <h3 className="text-sm text-gray-600">{title}</h3>
    <p className="text-2xl font-bold">{value}</p>
  </div>
);
