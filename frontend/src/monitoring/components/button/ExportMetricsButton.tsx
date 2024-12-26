// src/monitoring/components/buttons/ExportMetricsButton.tsx
import React from "react";
import { Button } from "../../../common/components/ui/button";
import { Download } from "lucide-react";
import type { MetricsData } from "../../types/metrics";

interface ExportMetricsButtonProps {
  metrics: MetricsData[];
  format?: "csv" | "json";
  className?: string;
}

export const ExportMetricsButton: React.FC<ExportMetricsButtonProps> = ({
  metrics,
  format = "csv",
  className = "",
}) => {
  const exportMetrics = () => {
    let content: string;
    let fileName: string;
    const timestamp = new Date().toISOString().split("T")[0];

    if (format === "csv") {
      const headers = [
        "type",
        "status",
        "timestamp",
        ...Object.keys(metrics[0]?.values || {}),
      ];
      const rows = metrics.map((metric) => [
        metric.type,
        metric.status,
        metric.timestamp,
        ...Object.values(metric.values),
      ]);
      content = [headers, ...rows].map((row) => row.join(",")).join("\n");
      fileName = `metrics-${timestamp}.csv`;
    } else {
      content = JSON.stringify(metrics, null, 2);
      fileName = `metrics-${timestamp}.json`;
    }

    const blob = new Blob([content], {
      type: format === "csv" ? "text/csv" : "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Button
      variant="outline"
      onClick={exportMetrics}
      className={`gap-2 ${className}`}
    >
      <Download className="h-4 w-4" />
      Export Metrics
    </Button>
  );
};
