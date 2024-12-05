// src/components/reports/ReportViewer.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import type { Report, ReportMetadata } from "../../types/reports";

interface ReportViewerProps {
  report: Report;
  metadata?: ReportMetadata;
  onExport: () => void;
  className?: string;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  report,
  metadata,
  onExport,
  className = "",
}) => {
  return (
    <Card className={`${className}`}>
      <CardHeader className="flex flex-row justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">{report.config.name}</h2>
          <p className="text-sm text-gray-500">
            Generated on {new Date(report.createdAt).toLocaleString()}
          </p>
        </div>
        {report.status === "completed" && (
          <Button onClick={onExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {metadata && (
          <>
            <div className="grid grid-cols-3 gap-4">
              {metadata.metrics.map((metric) => (
                <div key={metric.name} className="p-4 rounded-lg bg-gray-50">
                  <p className="text-sm text-gray-600">{metric.name}</p>
                  <p className="text-2xl font-bold">{metric.value}</p>
                  <p
                    className={`text-sm ${
                      metric.status === "healthy"
                        ? "text-green-600"
                        : metric.status === "warning"
                        ? "text-yellow-600"
                        : "text-red-600"
                    }`}
                  >
                    {metric.status}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-6">
              <h3 className="text-lg font-medium mb-2">Summary</h3>
              <p className="text-gray-700">{metadata.summary}</p>
            </div>
          </>
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
