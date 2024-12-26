// src/report/components/ReportViewer.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Button } from "@/common/components/ui/button";
import { Download, RefreshCw } from "lucide-react";
import { useReportMetadata } from "../hooks/useReportMetadata";
import type { Report } from "../types/models";
import { dateUtils } from "@/common";

interface ReportViewerProps {
  report: Report;
  onExport: () => void;
  onRefresh: () => void;
  className?: string;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  report,
  onExport,
  onRefresh,
  className = "",
}) => {
  const { data: metadata } = useReportMetadata(report.id);

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">{report.config.name}</h2>
          <p className="text-sm text-gray-500">
            Generated:{" "}
            {dateUtils.formatDate(report.createdAt, { includeTime: true })}
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {report.status === "completed" && (
            <Button onClick={onExport}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {metadata?.metrics && (
          <div className="grid grid-cols-3 gap-4">
            {metadata.metrics.map((metric) => (
              <MetricCard
                key={metric.name}
                name={metric.name}
                value={metric.value}
                status={metric.status}
              />
            ))}
          </div>
        )}

        {metadata?.summary && (
          <div className="prose max-w-none">
            <h3>Summary</h3>
            <p>{metadata.summary}</p>
          </div>
        )}

        {report.error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg">
            {report.error}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

interface MetricCardProps {
  name: string;
  value: number;
  status: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ name, value, status }) => (
  <div className="p-4 bg-gray-50 rounded-lg">
    <h4 className="text-sm font-medium text-gray-500">{name}</h4>
    <p className="text-2xl font-bold">{value}</p>
    <p className={`text-sm ${getStatusColor(status)}`}>{status}</p>
  </div>
);

function getStatusColor(status: string): string {
  switch (status) {
    case "healthy":
      return "text-green-600";
    case "warning":
      return "text-yellow-600";
    case "critical":
      return "text-red-600";
    default:
      return "text-gray-600";
  }
}
