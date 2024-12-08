// src/components/datasource/preview/StreamPreview.tsx
import type { StreamSourceConfig } from "../../types/dataSources";
import { Card, CardHeader, CardContent } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { formatBytes } from "../../../utils/format";

interface StreamPreviewProps {
  source: StreamSourceConfig;
  messages: unknown[];
  metrics: {
    messagesPerSecond: number;
    bytesPerSecond: number;
  };
  className?: string;
}

export const StreamPreview: React.FC<StreamPreviewProps> = ({
  messages,
  metrics,
  className = "",
}) => {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Stream Monitor</h3>
          <div className="flex space-x-4">
            <Badge variant="outline">
              {metrics.messagesPerSecond.toFixed(2)} msg/s
            </Badge>
            <Badge variant="outline">
              {formatBytes(metrics.bytesPerSecond)}/s
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] overflow-y-auto space-y-2 font-mono text-sm">
          {messages.map((message, index) => (
            <div
              key={index}
              className="p-2 border rounded-md whitespace-pre-wrap"
            >
              {JSON.stringify(message, null, 2)}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
