// src/components/pipeline/PipelineLogs.tsx
import React, { useEffect, useRef } from "react";
import { Card } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { usePipeline } from "../../hooks/pipeline/usePipeline";

interface PipelineLogsProps {
  pipelineId: string;
  className?: string;
}

export const PipelineLogs: React.FC<PipelineLogsProps> = ({
  pipelineId,
  className = "",
}) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { logs, refreshLogs } = usePipeline(pipelineId);

  useEffect(() => {
    const interval = setInterval(refreshLogs, 5000);
    return () => clearInterval(interval);
  }, [refreshLogs]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case "error":
        return "bg-red-100 text-red-800";
      case "warn":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-blue-100 text-blue-800";
    }
  };

  if (!logs) return null;

  return (
    <Card className={`p-4 ${className}`}>
      <div className="h-[600px] overflow-y-auto font-mono text-sm">
        {logs.logs.map((log, index) => (
          <div key={index} className="py-1 flex items-start space-x-2">
            <span className="text-gray-500 min-w-[160px]">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <Badge className={`${getLogLevelColor(log.level)} uppercase`}>
              {log.level}
            </Badge>
            {log.step && <Badge variant="outline">{log.step}</Badge>}
            <span className="flex-1 whitespace-pre-wrap">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </Card>
  );
};
