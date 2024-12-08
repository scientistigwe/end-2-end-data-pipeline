// src/components/reports/ReportsList.tsx
import React from "react";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Download, Trash2 } from "lucide-react";
import type { Report } from "../../types/report";

interface ReportsListProps {
  reports: Report[];
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  className?: string;
}

export const ReportsList: React.FC<ReportsListProps> = ({
  reports,
  onExport,
  onDelete,
  className = "",
}) => {
  const getStatusColor = (status: Report["status"]) => {
    switch (status) {
      case "completed":
        return "text-green-600";
      case "failed":
        return "text-red-600";
      case "generating":
        return "text-blue-600";
      default:
        return "text-gray-600";
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {reports.map((report) => (
        <Card key={report.id} className="p-4">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <h3 className="text-lg font-medium">{report.config.name}</h3>
              <p className="text-sm text-gray-500">
                Type: {report.config.type}
              </p>
              <p className="text-sm text-gray-500">
                Format: {report.config.format.toUpperCase()}
              </p>
              <p
                className={`text-sm font-medium ${getStatusColor(
                  report.status
                )}`}
              >
                Status: {report.status}
              </p>
              <p className="text-sm text-gray-500">
                Created: {new Date(report.createdAt).toLocaleString()}
              </p>
            </div>

            <div className="flex space-x-2">
              {report.status === "completed" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onExport(report.id)}
                >
                  <Download className="h-4 w-4" />
                  <span className="ml-2">Export</span>
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(report.id)}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
