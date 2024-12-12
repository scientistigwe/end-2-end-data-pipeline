// src/dataSource/components/cards/StreamSourceCard.tsx
import React from 'react';
import { Card, CardHeader, CardContent } from '../../../common/components/ui/card';
import { Badge } from '../../../common/components/ui/badge';
import { Activity } from 'lucide-react';
import type { StreamSourceConfig } from '../../types/dataSources';

interface StreamSourceCardProps {
  source: StreamSourceConfig;
  status?: string;
  metrics?: {
    messagesPerSecond: number;
    bytesPerSecond: number;
    lastMessage?: string;
    errors?: {
      count: number;
      lastError?: string;
    };
  };
  className?: string;
}

export const StreamSourceCard: React.FC<StreamSourceCardProps> = ({
  source,
  status = 'disconnected',
  metrics,
  className = ''
}) => {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          <Activity className="h-5 w-5" />
          <div>
            <Badge variant="outline">{source.config.protocol}</Badge>
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
            <p>Hosts: {source.config.connection.hosts.join(', ')}</p>
            {source.config.topics?.length && (
              <p>Topics: {source.config.topics.join(', ')}</p>
            )}
            {source.config.consumer?.groupId && (
              <p>Consumer Group: {source.config.consumer.groupId}</p>
            )}
          </div>

          {metrics && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                <div className="text-sm">
                  <p className="text-muted-foreground">Messages/sec</p>
                  <p className="font-medium">{metrics.messagesPerSecond.toFixed(2)}</p>
                </div>
                <div className="text-sm">
                  <p className="text-muted-foreground">Bytes/sec</p>
                  <p className="font-medium">{(metrics.bytesPerSecond / 1024).toFixed(2)} KB/s</p>
                </div>
              </div>

              {metrics.lastMessage && (
                <div className="pt-2 border-t">
                  <p className="text-sm text-muted-foreground">Last Message</p>
                  <p className="text-sm font-medium truncate">
                    {new Date(metrics.lastMessage).toLocaleString()}
                  </p>
                </div>
              )}

              {metrics.errors && metrics.errors.count > 0 && (
                <div className="pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-red-500">Errors</p>
                    <Badge variant="destructive">{metrics.errors.count}</Badge>
                  </div>
                  {metrics.errors.lastError && (
                    <p className="text-sm text-red-500 mt-1 truncate">
                      {metrics.errors.lastError}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};