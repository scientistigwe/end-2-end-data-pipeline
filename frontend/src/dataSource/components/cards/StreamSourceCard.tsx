import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import { Power } from "lucide-react";
import { formatBytes } from "../../../utils/format";
import { useStreamSource } from "../../hooks/useStreamSource";
import type { StreamSourceConfig } from "../../types/dataSources";

interface StreamMetrics {
  messagesPerSecond: number;
  bytesPerSecond: number;
  totalMessages: number;
  lastMessage?: string;
  errors?: {
    count: number;
    lastError?: string;
  };
}

interface StreamSourceCardProps {
  source: StreamSourceConfig;
  metrics?: StreamMetrics;
  className?: string;
}

export const StreamSourceCard: React.FC<StreamSourceCardProps> = ({
  source,
  metrics,
  className,
}) => {
  const { connect, disconnect, messages, isConnected, isConnecting } =
    useStreamSource();

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-medium">{source.name}</h3>
            <Badge variant={isConnected ? "success" : "secondary"}>
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
          </div>
          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                isConnected ? disconnect() : connect(source.config)
              }
              className={isConnected ? "text-red-600 hover:text-red-700" : ""}
              disabled={isConnecting}
            >
              <Power className="h-4 w-4 mr-1" />
              {isConnecting
                ? "Connecting..."
                : isConnected
                ? "Disconnect"
                : "Connect"}
            </Button>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          <div className="text-sm text-gray-600 grid grid-cols-2 gap-x-8 gap-y-2">
            <div>
              <span className="font-medium">Protocol:</span>{" "}
              {source.config.protocol}
            </div>
            <div>
              <span className="font-medium">Hosts:</span>{" "}
              {source.config.connection.hosts.join(", ")}
            </div>
            {source.config.topics && (
              <div className="col-span-2">
                <span className="font-medium">Topics:</span>{" "}
                {source.config.topics.join(", ")}
              </div>
            )}
            {source.config.consumer?.groupId && (
              <div>
                <span className="font-medium">Consumer Group:</span>{" "}
                {source.config.consumer.groupId}
              </div>
            )}
          </div>

          {metrics && (
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div>
                <p className="text-sm text-gray-500">Throughput</p>
                <div className="font-medium">
                  <p>{metrics.messagesPerSecond.toFixed(1)} msg/s</p>
                  <p>{formatBytes(metrics.bytesPerSecond)}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500">Messages</p>
                <p className="font-medium">
                  {metrics.totalMessages.toLocaleString()}
                </p>
              </div>
              {metrics.errors && (
                <div>
                  <p className="text-sm text-gray-500">Errors</p>
                  <p className="font-medium text-red-600">
                    {metrics.errors.count.toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          )}

          {metrics?.lastMessage && (
            <div className="pt-4 border-t">
              <p className="text-sm text-gray-500">Last Message</p>
              <p className="font-medium">
                {new Date(metrics.lastMessage).toLocaleString()}
              </p>
            </div>
          )}

          {messages.length > 0 && (
            <div className="pt-4 border-t">
              <p className="text-sm text-gray-500 mb-2">Recent Messages</p>
              <div className="bg-gray-50 rounded-md p-2 h-32 overflow-y-auto font-mono text-sm">
                {messages.map((msg, index) => (
                  <pre key={index} className="whitespace-pre-wrap break-all">
                    {JSON.stringify(msg, null, 2)}
                  </pre>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
