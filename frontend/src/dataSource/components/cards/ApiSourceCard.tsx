// src/components/sources/ApiSourceCard.tsx
import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import type { ApiSourceConfig } from "../../types/dataSources";

interface ApiSourceCardProps {
  source: ApiSourceConfig;
  status?: string;
  metrics?: {
    responseTime?: number;
    lastSuccess?: string;
    successRate?: number;
  };
}

export const ApiSourceCard: React.FC<ApiSourceCardProps> = ({
  source,
  status = "disconnected",
  metrics,
}) => {
  return (
    <Card className="p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{source.name}</h3>
        <Badge variant={status === "connected" ? "success" : "secondary"}>
          {status}
        </Badge>
      </div>

      <div className="mt-4">
        <div className="text-sm text-gray-600 space-y-1">
          <p>URL: {source.config.url}</p>
          <p>Method: {source.config.method}</p>
          {source.config.rateLimit && (
            <p>
              Rate Limit: {source.config.rateLimit.requests} /{" "}
              {source.config.rateLimit.period}s
            </p>
          )}
        </div>

        {metrics && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Avg Response</p>
              <p className="font-medium">{metrics.responseTime}ms</p>
            </div>
            <div>
              <p className="text-gray-500">Success Rate</p>
              <p className="font-medium">{metrics.successRate}%</p>
            </div>
            <div>
              <p className="text-gray-500">Last Success</p>
              <p className="font-medium">
                {metrics.lastSuccess
                  ? new Date(metrics.lastSuccess).toLocaleString()
                  : "Never"}
              </p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
