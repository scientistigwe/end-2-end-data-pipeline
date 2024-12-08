import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { FolderOpen, Power } from "lucide-react";
import { useS3Source } from "../../hooks/useS3Source";
import type { S3SourceConfig } from "../../types/dataSources";

interface S3Metrics {
  objects: number;
  totalSize: number;
  lastModified: string;
  versioning?: boolean;
  encryption?: {
    enabled: boolean;
    type: string;
  };
}

interface S3SourceCardProps {
  source: S3SourceConfig;
  metrics?: S3Metrics;
  className?: string;
}

export const S3SourceCard: React.FC<S3SourceCardProps> = ({
  source,
  metrics,
  className,
}) => {
  const { connect, disconnect, objects, connectionId, isConnecting } =
    useS3Source();

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium">{source.name}</h3>
            <Badge variant={connectionId ? "success" : "secondary"}>
              {connectionId ? "Connected" : "Disconnected"}
            </Badge>
          </div>
          <div className="flex space-x-2">
            {connectionId && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => connect(source.config)}
              >
                <FolderOpen className="h-4 w-4 mr-1" />
                List Objects
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                connectionId ? disconnect() : connect(source.config)
              }
              className={connectionId ? "text-red-600 hover:text-red-700" : ""}
              disabled={isConnecting}
            >
              <Power className="h-4 w-4 mr-1" />
              {isConnecting
                ? "Connecting..."
                : connectionId
                ? "Disconnect"
                : "Connect"}
            </Button>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          <div className="text-sm text-gray-600 grid grid-cols-2 gap-x-8 gap-y-2">
            <div>
              <span className="font-medium">Bucket:</span>{" "}
              {source.config.bucket}
            </div>
            <div>
              <span className="font-medium">Region:</span>{" "}
              {source.config.region}
            </div>
            {source.config.prefix && (
              <div className="col-span-2">
                <span className="font-medium">Prefix:</span>{" "}
                {source.config.prefix}
              </div>
            )}
            {source.config.endpoint && (
              <div className="col-span-2">
                <span className="font-medium">Endpoint:</span>{" "}
                {source.config.endpoint}
              </div>
            )}
          </div>

          {metrics && (
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm text-gray-500">Objects</p>
                <p className="font-medium">
                  {metrics.objects.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Size</p>
                <p className="font-medium">{formatBytes(metrics.totalSize)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Last Modified</p>
                <p className="font-medium">
                  {new Date(metrics.lastModified).toLocaleString()}
                </p>
              </div>
              {metrics.encryption && (
                <div className="col-span-3 flex gap-4">
                  {metrics.versioning && (
                    <Badge variant="secondary">Versioning Enabled</Badge>
                  )}
                  {metrics.encryption.enabled && (
                    <Badge variant="secondary">
                      {metrics.encryption.type} Encryption
                    </Badge>
                  )}
                </div>
              )}
            </div>
          )}

          {objects && objects.length > 0 && (
            <div className="pt-4 border-t">
              <p className="text-sm text-gray-500 mb-2">Objects</p>
              <div className="bg-gray-50 rounded-md p-2 max-h-48 overflow-y-auto">
                {objects.map((obj) => (
                  <div
                    key={obj.key}
                    className="flex justify-between items-center py-1 text-sm"
                  >
                    <span className="truncate flex-1">{obj.key}</span>
                    <span className="text-gray-500 ml-4">
                      {formatBytes(obj.size)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
