// src/monitoring/components/health/HealthStatusCard.tsx
import React from "react";
import {
  Card,
  CardHeader,
  CardContent,
} from "../../../common/components/ui/card";
import { Badge } from "../../../common/components/ui/badge";
import { Activity, CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import type { SystemHealth } from "../../types/metrics";

interface HealthStatusCardProps {
  health: SystemHealth;
  className?: string;
}

export const HealthStatusCard: React.FC<HealthStatusCardProps> = ({
  health,
  className = "",
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "warning":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "critical":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
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
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">System Health</h3>
          <Badge className={getStatusColor(health.status)}>
            {health.status.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {health.components.map((component) => (
            <div
              key={component.name}
              className="flex items-center justify-between p-2 rounded-lg border"
            >
              <div className="flex items-center space-x-2">
                {getStatusIcon(component.status)}
                <span className="font-medium">{component.name}</span>
              </div>
              {component.message && (
                <span className="text-sm text-muted-foreground">
                  {component.message}
                </span>
              )}
            </div>
          ))}

          <div className="text-sm text-muted-foreground pt-2 border-t">
            Last checked: {new Date(health.lastChecked).toLocaleString()}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
