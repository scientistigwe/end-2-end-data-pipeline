// src/pipeline/pages/DashboardPage.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/common/components/ui/tabs";
import { PipelineMetricsChart } from "../components/PipelineMetricsChart";
import { PipelineList } from "../components/PipelineList";
import { usePipeline } from "../hooks/usePipeline";
import { useSelector } from "react-redux";
import { selectPipelineStats } from "../store/selectors";

export const DashboardPage: React.FC = () => {
  const { pipelines, isLoading } = usePipeline();
  const stats = useSelector(selectPipelineStats);

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Pipeline Dashboard</h1>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card className="p-4">
          <h3 className="text-sm font-medium text-gray-500">Total Pipelines</h3>
          <p className="text-2xl font-bold">{stats.total}</p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium text-gray-500">Running</h3>
          <p className="text-2xl font-bold text-blue-600">{stats.running}</p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium text-gray-500">Success Rate</h3>
          <p className="text-2xl font-bold text-green-600">
            {stats.success_rate.toFixed(1)}%
          </p>
        </Card>
        <Card className="p-4">
          <h3 className="text-sm font-medium text-gray-500">Failed</h3>
          <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
        </Card>
      </div>

      <Tabs defaultValue="active">
        <TabsList>
          <TabsTrigger value="active">Active Pipelines</TabsTrigger>
          <TabsTrigger value="metrics">Global Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="active">
          <PipelineList
            pipelines={pipelines?.filter((p) => p.status === "running") || []}
            isLoading={isLoading}
          />
        </TabsContent>

        <TabsContent value="metrics">
          <PipelineMetricsChart showGlobalMetrics />
        </TabsContent>
      </Tabs>
    </div>
  );
};
