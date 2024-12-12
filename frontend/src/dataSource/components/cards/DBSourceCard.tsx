// src/dataSource/components/cards/DBSourceCard.tsx
import React from 'react';
import { Card, CardHeader, CardContent } from '../../../common/components/ui/card';
import { Badge } from '../../../common/components/ui/badge';
import { Database } from 'lucide-react';
import type { DBSourceConfig } from '../../types/dataSources';

interface DBSourceCardProps {
  source: DBSourceConfig;
  status?: string;
  metrics?: {
    connectionPool?: {
      active: number;
      idle: number;
      max: number;
    };
    queryStats?: {
      averageResponseTime: number;
      queriesPerMinute: number;
    };
    lastSync?: string;
  };
  className?: string;
}

export const DBSourceCard: React.FC<DBSourceCardProps> = ({
  source,
  status = 'disconnected',
  metrics,
  className = ''
}) => {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          <Database className="h-5 w-5" />
          <div>
            <Badge variant="outline">{source.config.type}</Badge>
            <h3 className="text-lg font-medium mt-2">{source.name}</h3>
          </div>
        </div>
        <Badge 
          variant={status === 'connected' ? 'success' : 'secondary'}
        >
          {status}
        </Badge>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Host: {source.config.host}:{source.config.port}</p>
            <p>Database: {source.config.database}</p>
            {source.config.schema && <p>Schema: {source.config.schema}</p>}
            {source.config.ssl && <p>SSL: Enabled</p>}
          </div>

          {metrics && (
            <>
              {metrics.connectionPool && (
                <div className="pt-2 border-t">
                  <p className="text-sm font-medium">Connection Pool</p>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    <div className="text-sm">
                      <p className="text-muted-foreground">Active</p>
                      <p className="font-medium text-green-600">
                        {metrics.connectionPool.active}
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Idle</p>
                      <p className="font-medium text-blue-600">
                        {metrics.connectionPool.idle}
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Max</p>
                      <p className="font-medium">
                        {metrics.connectionPool.max}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {metrics.queryStats && (
                <div className="pt-2 border-t">
                  <p className="text-sm font-medium">Query Stats</p>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <div className="text-sm">
                      <p className="text-muted-foreground">Avg Response</p>
                      <p className="font-medium">
                        {metrics.queryStats.averageResponseTime}ms
                      </p>
                    </div>
                    <div className="text-sm">
                      <p className="text-muted-foreground">Queries/min</p>
                      <p className="font-medium">
                        {metrics.queryStats.queriesPerMinute}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
};