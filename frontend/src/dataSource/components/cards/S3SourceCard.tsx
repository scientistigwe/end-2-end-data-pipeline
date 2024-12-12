// src/dataSource/components/cards/S3SourceCard.tsx
import React from 'react';
import { Card, CardHeader, CardContent } from '../../../common/components/ui/card';
import { Badge } from '../../../common/components/ui/badge';
import { Cloud } from 'lucide-react';
import type { S3SourceConfig } from '../../types/dataSources';

interface S3SourceCardProps {
  source: S3SourceConfig;
  status?: string;
  metrics?: {
    objectCount?: number;
    totalSize?: number;
    lastSync?: string;
    bandwidth?: {
      upload: number;
      download: number;
    };
  };
  className?: string;
}

export const S3SourceCard: React.FC<S3SourceCardProps> = ({
  source,
  status = 'disconnected',
  metrics,
  className = ''
}) => {
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          <Cloud className="h-5 w-5" />
          <div>
            <Badge variant="outline">S3</Badge>
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
            <p>Bucket: {source.config.bucket}</p>
            <p>Region: {source.config.region}</p>
            {source.config.prefix && <p>Prefix: {source.config.prefix}</p>}
            {source.config.sslEnabled && <p>SSL: Enabled</p>}
          </div>

          {metrics && (
            <div className="grid grid-cols-2 gap-4 pt-2 border-t">
              {metrics.objectCount !== undefined && (
                <div className="text-sm">
                  <p className="text-muted-foreground">Objects</p>
                  <p className="font-medium">{metrics.objectCount.toLocaleString()}</p>
                </div>
              )}
              {metrics.totalSize !== undefined && (
                <div className="text-sm">
                  <p className="text-muted-foreground">Total Size</p>
                  <p className="font-medium">{formatBytes(metrics.totalSize)}</p>
                </div>
              )}
              {metrics.bandwidth && (
                <>
                  <div className="text-sm">
                    <p className="text-muted-foreground">Upload</p>
                    <p className="font-medium">{formatBytes(metrics.bandwidth.upload)}/s</p>
                  </div>
                  <div className="text-sm">
                    <p className="text-muted-foreground">Download</p>
                    <p className="font-medium">{formatBytes(metrics.bandwidth.download)}/s</p>
                  </div>
                </>
              )}
            </div>
          )}

          {metrics?.lastSync && (
            <div className="text-sm pt-2 border-t">
              <p className="text-muted-foreground">Last Sync</p>
              <p className="font-medium">
                {new Date(metrics.lastSync).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};