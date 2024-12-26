import React from "react";
import { Badge } from "@/common/components/ui/badge";
import { Card } from "@/common/components/ui/card";
import { Progress } from "@/common/components/ui/progress";
import { dateUtils } from "@/common"; // Import dateUtils
import type { DataSourceStatus as SourceStatus } from "../../types/base";

interface StatusMetrics {
  syncProgress?: number;
  lastSync?: string;
  nextSync?: string;
  recordsProcessed?: number;
  totalRecords?: number;
}

interface StatusComponentProps {
  status: SourceStatus;
  metrics?: StatusMetrics;
  className?: string;
}

export const DataSourceStatus: React.FC<StatusComponentProps> = ({
  status,
  metrics,
  className = "",
}) => {
  const getStatusColor = (currentStatus: SourceStatus): string => {
    const statusColors = {
      connected: "bg-green-100 text-green-800",
      connecting: "bg-yellow-100 text-yellow-800",
      error: "bg-red-100 text-red-800",
      disconnected: "bg-gray-100 text-gray-800",
      validating: "bg-blue-100 text-blue-800",
    };

    return statusColors[currentStatus] || statusColors.disconnected;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  };

  return (
    <Card className={className}>
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium">Status</h3>
          <Badge className={getStatusColor(status)}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </Badge>
        </div>

        {metrics && (
          <div className="space-y-4">
            {metrics.syncProgress !== undefined && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Sync Progress</span>
                  <span>{metrics.syncProgress.toFixed(1)}%</span>
                </div>
                <Progress value={metrics.syncProgress} />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 text-sm">
              {metrics.lastSync && (
                <div>
                  <span className="text-gray-500">Last Sync</span>
                  <p>
                    {dateUtils.formatDate(metrics.lastSync, {
                      includeTime: true,
                    })}
                  </p>
                </div>
              )}
              {metrics.nextSync && (
                <div>
                  <span className="text-gray-500">Next Sync</span>
                  <p>
                    {dateUtils.formatDate(metrics.nextSync, {
                      includeTime: true,
                    })}
                  </p>
                </div>
              )}
            </div>

            {metrics.recordsProcessed !== undefined && (
              <div className="text-sm">
                <span className="text-gray-500">Records Processed</span>
                <p>
                  {formatNumber(metrics.recordsProcessed)}
                  {metrics.totalRecords !== undefined &&
                    ` / ${formatNumber(metrics.totalRecords)}`}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
