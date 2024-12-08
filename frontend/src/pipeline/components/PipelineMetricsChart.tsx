// src/components/pipeline/PipelineMetricsChart.tsx
import React, { useState } from "react";
import { Card, CardHeader, CardContent } from "../../components/ui/card";
import { Select } from "../../components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PipelineMetrics } from "../types/pipeline";

interface PipelineMetricsChartProps {
  metrics: PipelineMetrics[];
  className?: string;
}

export const PipelineMetricsChart: React.FC<PipelineMetricsChartProps> = ({
  metrics,
  className = "",
}) => {
  const [selectedMetric, setSelectedMetric] = useState("throughput");

  const formatMetricValue = (value: number) => {
    switch (selectedMetric) {
      case "latency":
        return `${value.toFixed(2)}ms`;
      case "errorRate":
        return `${(value * 100).toFixed(2)}%`;
      case "cpu":
      case "memory":
        return `${(value * 100).toFixed(1)}%`;
      default:
        return value.toFixed(2);
    }
  };

  const getMetricColor = () => {
    switch (selectedMetric) {
      case "errorRate":
        return "#ef4444";
      case "latency":
        return "#f59e0b";
      case "throughput":
        return "#10b981";
      default:
        return "#6366f1";
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Pipeline Metrics</h3>
          <Select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            <option value="throughput">Throughput</option>
            <option value="latency">Latency</option>
            <option value="errorRate">Error Rate</option>
            <option value="cpu">CPU Usage</option>
            <option value="memory">Memory Usage</option>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              />
              <YAxis tickFormatter={formatMetricValue} />
              <Tooltip
                labelFormatter={(value) => new Date(value).toLocaleString()}
                formatter={(value: number) => [
                  formatMetricValue(value),
                  selectedMetric,
                ]}
              />
              <Line
                type="monotone"
                dataKey={`metrics.${selectedMetric}`}
                stroke={getMetricColor()}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
