// src/report/components/ReportList.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
import { Download, Trash2, Calendar, MoreVertical } from "lucide-react";
import type { Report } from "../types/report";
import { formatDateTime } from "../utils/formatters";

interface ReportListProps {
  reports: Report[];
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  onSchedule: (id: string) => void;
  className?: string;
}

export const ReportList: React.FC<ReportListProps> = ({
  reports,
  onExport,
  onDelete,
  onSchedule,
  className = "",
}) => {
  return (
    <div className={`space-y-4 ${className}`}>
      {reports.map((report) => (
        <Card key={report.id} className="p-4">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-medium">{report.config.name}</h3>
                <Badge variant={getStatusVariant(report.status)}>
                  {report.status}
                </Badge>
              </div>
              <p className="text-sm text-gray-500">
                Type: {report.config.type}
              </p>
              <p className="text-sm text-gray-500">
                Created: {formatDateTime(report.createdAt)}
              </p>
            </div>

            <div className="flex items-center space-x-2">
              {report.status === "completed" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onExport(report.id)}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSchedule(report.id)}
              >
                <Calendar className="h-4 w-4 mr-2" />
                Schedule
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(report.id)}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          </div>

          {report.error && (
            <div className="mt-2 p-2 bg-red-50 text-red-700 rounded text-sm">
              {report.error}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
};

function getStatusVariant(status: Report["status"]): string {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "generating":
      return "default";
    default:
      return "secondary";
  }
}
