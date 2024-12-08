// src/components/sources/DBSourceCard.tsx
import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import type { DBSourceConfig } from "../../types/dataSources";

interface DBSourceCardProps {
  source: DBSourceConfig;
  status?: string;
  metrics?: {
    totalTables?: number;
    totalRows?: number;
    lastSync?: string;
    connectionPool?: {
      active: number;
      idle: number;
      max: number;
    };
  };
}

export const DBSourceCard: React.FC<DBSourceCardProps> = ({
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
          <p>Type: {source.config.type}</p>
          <p>
            Host: {source.config.host}:{source.config.port}
          </p>
          <p>Database: {source.config.database}</p>
          {source.config.schema && <p>Schema: {source.config.schema}</p>}
          {source.config.ssl && <p>SSL: Enabled</p>}
        </div>

        {metrics && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-sm">
              <p className="text-gray-500">Tables</p>
              <p className="font-medium">
                {metrics.totalTables?.toLocaleString()}
              </p>
            </div>
            <div className="text-sm">
              <p className="text-gray-500">Total Rows</p>
              <p className="font-medium">
                {metrics.totalRows?.toLocaleString()}
              </p>
            </div>

            {metrics.connectionPool && (
              <div className="col-span-2">
                <p className="text-sm text-gray-500">Connection Pool</p>
                <div className="mt-1 flex gap-4 text-sm">
                  <span className="text-green-600">
                    {metrics.connectionPool.active} active
                  </span>
                  <span className="text-blue-600">
                    {metrics.connectionPool.idle} idle
                  </span>
                  <span className="text-gray-600">
                    {metrics.connectionPool.max} max
                  </span>
                </div>
              </div>
            )}

            {metrics.lastSync && (
              <div className="col-span-2 text-sm">
                <p className="text-gray-500">Last Synced</p>
                <p className="font-medium">
                  {new Date(metrics.lastSync).toLocaleString()}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
