// src/components/monitoring/HealthStatus.tsx
import React from "react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import type { SystemHealth } from "../../types/monitoring";

interface HealthStatusProps {
  health: SystemHealth;
  className?: string;
}

export const HealthStatus: React.FC<HealthStatusProps> = ({
  health,
  className = "",
}) => {
  const statusColors = {
    healthy: "bg-green-50 text-green-800",
    warning: "bg-yellow-50 text-yellow-800",
    critical: "bg-red-50 text-red-800",
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <Alert className={statusColors[health.status]}>
        <AlertTitle>System Status: {health.status.toUpperCase()}</AlertTitle>
        <AlertDescription>
          Last checked: {new Date(health.lastChecked).toLocaleString()}
        </AlertDescription>
      </Alert>

      <div className="space-y-2">
        {health.components.map((component) => (
          <Alert
            key={component.name}
            className={statusColors[component.status]}
          >
            <AlertTitle>{component.name}</AlertTitle>
            {component.message && (
              <AlertDescription>{component.message}</AlertDescription>
            )}
          </Alert>
        ))}
      </div>
    </div>
  );
};
