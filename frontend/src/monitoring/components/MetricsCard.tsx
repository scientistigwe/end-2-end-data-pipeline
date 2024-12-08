// src/components/monitoring/MetricsCard.tsx
import React from "react";
import { Card, CardHeader, CardContent } from "../../components/ui/card";
import type { MetricsData } from "../types/monitoring";

interface MetricsCardProps {
  metrics: MetricsData;
  title: string;
  className?: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  metrics,
  title,
  className = "",
}) => {
  return (
    <Card className={`${className}`}>
      <CardHeader>
        <h3 className="text-lg font-medium">{title}</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.entries(metrics.values).map(([key, value]) => (
            <div key={key} className="flex justify-between items-center">
              <span className="text-sm text-gray-600">{key}</span>
              <span className="font-medium">{value}</span>
            </div>
          ))}
          <div className="mt-4 pt-4 border-t">
            <span className="text-sm text-gray-500">
              Last updated: {new Date(metrics.timestamp).toLocaleString()}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
