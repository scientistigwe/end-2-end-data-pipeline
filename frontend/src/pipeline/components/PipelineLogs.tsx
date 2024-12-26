import React, { useEffect, useRef, useState } from "react";
import { Card } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
import { Select } from "@/common/components/ui/inputs/select";
import { Download, RefreshCw } from "lucide-react";
import { usePipelineLogs } from "../hooks/usePipelineLogs";
import { getLogLevelColor } from "../utils/formatters";
import type { LogLevel } from "../types/metrics";

interface PipelineLogsProps {
  pipelineId: string;
  className?: string;
}

export const PipelineLogs: React.FC<PipelineLogsProps> = ({
  pipelineId,
  className = "",
}) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [logLevel, setLogLevel] = useState<LogLevel>("info");
  const { logs, isLoading, refresh, download } = usePipelineLogs(pipelineId, {
    level: logLevel,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      refresh().catch(console.error);
    }, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (logs) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const handleRefresh = async () => {
    try {
      await refresh();
    } catch (error) {
      console.error("Failed to refresh logs:", error);
    }
  };

  const handleDownload = async () => {
    try {
      await download("txt");
    } catch (error) {
      console.error("Failed to download logs:", error);
    }
  };

  const handleLogLevelChange = (
    event: React.ChangeEvent<HTMLSelectElement>
  ) => {
    setLogLevel(event.target.value as LogLevel);
  };

  return (
    <Card className={className}>
      <div className="p-4 border-b flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <h3 className="font-medium">Pipeline Logs</h3>
          <Select
            value={logLevel}
            onChange={handleLogLevelChange}
            className="w-[180px]"
          >
            <option value="info">Info</option>
            <option value="warn">Warning</option>
            <option value="error">Error</option>
          </Select>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={isLoading}
          >
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>
      </div>

      <div className="h-[600px] overflow-y-auto font-mono text-sm p-4">
        {isLoading ? (
          <div className="text-center py-4">Loading logs...</div>
        ) : logs?.logs.length === 0 ? (
          <div className="text-center py-4 text-gray-500">
            No logs available
          </div>
        ) : (
          logs?.logs.map((log, index) => (
            <div key={index} className="py-1 flex items-start space-x-2">
              <span className="text-gray-500 min-w-[160px]">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <Badge className={getLogLevelColor(log.level)}>
                {log.level.toUpperCase()}
              </Badge>
              {log.step && <Badge variant="outline">{log.step}</Badge>}
              <span className="flex-1 whitespace-pre-wrap">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </Card>
  );
};
