// src/components/monitoring/AlertsList.tsx
import React from "react";
import { Alert, AlertTitle, AlertDescription } from "../../components/ui/alert";
import type { Alert as AlertType } from "../types/monitoring";

interface AlertsListProps {
  alerts: AlertType[];
  className?: string;
}

export const AlertsList: React.FC<AlertsListProps> = ({
  alerts,
  className = "",
}) => {
  const severityColors = {
    info: "bg-blue-50 text-blue-800",
    warning: "bg-yellow-50 text-yellow-800",
    critical: "bg-red-50 text-red-800",
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {alerts.map((alert) => (
        <Alert
          key={alert.id}
          className={`${severityColors[alert.severity]} ${
            alert.resolved ? "opacity-50" : ""
          }`}
        >
          <AlertTitle>
            {alert.metric} - {alert.severity.toUpperCase()}
          </AlertTitle>
          <AlertDescription>
            <p>{alert.message}</p>
            <p className="text-sm mt-2">
              {new Date(alert.timestamp).toLocaleString()}
            </p>
            {alert.resolved && (
              <p className="text-sm mt-1">
                Resolved at: {new Date(alert.resolvedAt!).toLocaleString()}
              </p>
            )}
          </AlertDescription>
        </Alert>
      ))}
    </div>
  );
};
