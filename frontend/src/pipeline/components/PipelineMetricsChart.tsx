import React, { useState, useMemo } from "react";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Select } from "@/common/components/ui/inputs/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { usePipelineMetrics } from "../hooks/usePipelineMetrics";
import { usePipeline } from "../hooks/usePipeline";
import { formatMetricValue, getMetricColor } from "../utils/formatters";

type MetricKey = "throughput" | "latency" | "errorRate" | "cpu" | "memory";

type PipelineMetricsChartProps = {
  className?: string;
} & (
  | {
      showGlobalMetrics: true;
      pipelineId?: never; // pipelineId not needed for global metrics
    }
  | {
      showGlobalMetrics?: false;
      pipelineId: string; // pipelineId required for single pipeline metrics
    }
);


export const PipelineMetricsChart: React.FC<PipelineMetricsChartProps> = ({
    pipelineId,
    className = "",
    showGlobalMetrics = false
  }) => {
    const [selectedMetric, setSelectedMetric] = useState<MetricKey>("throughput");
    const { metrics, isLoading, isEmpty, hasError, refresh } = usePipelineMetrics(
      showGlobalMetrics ? undefined : pipelineId
    );
    const { pipelines } = usePipeline();
  const handleMetricChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(event.target.value as MetricKey);
  };

  const processedMetrics = useMemo(() => {
    if (!showGlobalMetrics || !pipelines?.length) {
      return metrics;
    }

    // Create a map to store aggregated metrics by timestamp
    const aggregatedData = new Map();

    pipelines.forEach(pipeline => {
      const pipelineMetrics = pipeline.metrics || [];
      pipelineMetrics.forEach(metric => {
        const timestamp = metric.timestamp;
        const existing = aggregatedData.get(timestamp);

        if (existing) {
          // Update existing metrics
          existing.metrics.throughput += metric.metrics.throughput;
          existing.metrics.latency = Math.max(existing.metrics.latency, metric.metrics.latency);
          existing.metrics.errorRate = (existing.metrics.errorRate + metric.metrics.errorRate) / 2;
          existing.metrics.cpu += metric.metrics.resourceUsage.cpu;
          existing.metrics.memory += metric.metrics.resourceUsage.memory;
          existing.count += 1;
        } else {
          // Initialize new metric entry
          aggregatedData.set(timestamp, {
            timestamp,
            metrics: {
              throughput: metric.metrics.throughput,
              latency: metric.metrics.latency,
              errorRate: metric.metrics.errorRate,
              cpu: metric.metrics.resourceUsage.cpu,
              memory: metric.metrics.resourceUsage.memory
            },
            count: 1
          });
        }
      });
    });

    // Calculate averages and format final data
    return Array.from(aggregatedData.values())
      .map(({ timestamp, metrics: m, count }) => ({
        timestamp,
        metrics: {
          throughput: m.throughput,
          latency: m.latency,
          errorRate: m.errorRate,
          cpu: m.cpu / count,
          memory: m.memory / count
        }
      }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [showGlobalMetrics, pipelines, metrics]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div>Loading metrics...</div>
        </CardContent>
      </Card>
    );
  }

  if (hasError) {
    return (
      <Card className={className}>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 mb-2">Failed to load metrics</p>
            <button
              onClick={() => refresh()}
              className="text-sm text-blue-500 hover:underline"
            >
              Try again
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">
            {showGlobalMetrics ? "Global Metrics" : "Pipeline Metrics"}
          </h3>
          <Select
            value={selectedMetric}
            onChange={handleMetricChange}
            className="w-[180px]"
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
          {!isEmpty && processedMetrics?.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={processedMetrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis
                  tickFormatter={(value) => formatMetricValue(selectedMetric, value)}
                />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                  formatter={(value: number) => [
                    formatMetricValue(selectedMetric, value),
                    selectedMetric,
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey={`metrics.${selectedMetric}`}
                  stroke={getMetricColor(selectedMetric)}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              No metrics data available
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};