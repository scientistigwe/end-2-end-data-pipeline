// src/components/monitoring/MetricsCard.tsx
import React from "react";
import { useMonitoring } from "../../hooks/reportAndMonitoring/useMonitoring";
import { LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";

interface MetricsCardProps {
  pipelineId: string;
  metricKey: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  pipelineId,
  metricKey,
}) => {
  const { metrics, realtimeData } = useMonitoring({
    pipelineId,
    enableRealtime: true,
  });

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium mb-4">{metricKey}</h3>
      <div className="h-64">
        <LineChart width={500} height={200} data={realtimeData}>
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#8884d8" />
        </LineChart>
      </div>
    </div>
  );
};
