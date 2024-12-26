// src/dataSource/components/cards/ApiSourceCard.tsx
import React from "react";
import {
  Card,
  CardHeader,
  CardContent,
} from "../../../common/components/ui/card";
import { Badge } from "../../../common/components/ui/badge";
import type { ApiSourceConfig } from "../../types/base";

interface ApiSourceCardProps {
  source: ApiSourceConfig;
  status?: string;
  metrics?: {
    responseTime?: number;
    successRate?: number;
    lastSuccess?: string;
  };
  className?: string;
}

export const ApiSourceCard: React.FC<ApiSourceCardProps> = ({
  source,
  status = "disconnected",
  metrics,
  className = "",
}) => {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div>
          <Badge variant="outline">{source.config.method}</Badge>
          <h3 className="text-lg font-medium mt-2">{source.name}</h3>
        </div>
        <Badge
          variant={status === "connected" ? "success" : "secondary"}
          className="ml-2"
        >
          {status}
        </Badge>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p>Endpoint: {source.config.url}</p>
            {source.config.rateLimit && (
              <p>Rate Limit: {source.config.rateLimit.requests}/min</p>
            )}
          </div>

          {metrics && (
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Response Time</p>
                <p className="font-medium">{metrics.responseTime}ms</p>
              </div>
              <div>
                <p className="text-muted-foreground">Success Rate</p>
                <p className="font-medium">{metrics.successRate}%</p>
              </div>
              <div>
                <p className="text-muted-foreground">Last Success</p>
                <p className="font-medium">
                  {metrics.lastSuccess
                    ? new Date(metrics.lastSuccess).toLocaleString()
                    : "Never"}
                </p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
