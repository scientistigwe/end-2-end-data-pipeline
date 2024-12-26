// src/monitoring/components/tables/MetricsTable.tsx
import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../common/components/ui/table";
import { Badge } from "../../../common/components/ui/badge";
import type { MetricsData, MetricStatus } from "../../types/metrics";

interface MetricsTableProps {
  metrics: MetricsData[];
  className?: string;
}

export const MetricsTable: React.FC<MetricsTableProps> = ({
  metrics,
  className = "",
}) => {
  const getStatusColor = (status: MetricStatus) => {
    switch (status) {
      case "healthy":
        return "bg-green-100 text-green-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      case "critical":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className={className}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Metric</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Timestamp</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((metric, index) => (
            <TableRow key={index}>
              <TableCell>{metric.type}</TableCell>
              <TableCell className="font-medium">
                {Object.entries(metric.values).map(([key, value]) => (
                  <div key={key}>
                    {key}: {value}
                  </div>
                ))}
              </TableCell>
              <TableCell>
                <Badge className={getStatusColor(metric.status)}>
                  {metric.status}
                </Badge>
              </TableCell>
              <TableCell>
                {new Date(metric.timestamp).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};
