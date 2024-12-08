import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import {
  Settings,
  Trash2,
  RefreshCw,
  Database,
  FileText,
  Cloud,
  Network,
  Radio,
} from "lucide-react";
import type {
  DataSourceMetadata,
  DataSourceStatus,
  DataSourceType,
} from "../types/dataSources";

interface DataSourceListProps {
  sources: DataSourceMetadata[];
  onSelect: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  className?: string;
}

const STATUS_STYLES: Record<DataSourceStatus, string> = {
  connected: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
  connecting: "bg-blue-100 text-blue-800",
  disconnected: "bg-gray-100 text-gray-800",
  validating: "bg-yellow-100 text-yellow-800",
};

const TYPE_ICONS: Record<DataSourceType, React.ReactNode> = {
  database: <Database className="h-5 w-5" />,
  file: <FileText className="h-5 w-5" />,
  s3: <Cloud className="h-5 w-5" />,
  api: <Network className="h-5 w-5" />,
  stream: <Radio className="h-5 w-5" />,
};

export const DataSourceList = ({
  sources,
  onSelect,
  onEdit,
  onDelete,
  onSync,
  className = "",
}: DataSourceListProps) => (
  <div className={`space-y-4 ${className}`}>
    {sources.map((source) => (
      <Card
        key={source.id}
        className="p-4 hover:bg-gray-50 cursor-pointer"
        onClick={() => onSelect(source.id)}
      >
        <div className="flex justify-between items-start">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              {TYPE_ICONS[source.type]}
              <h3 className="text-lg font-medium">{source.name}</h3>
              <Badge className={STATUS_STYLES[source.status]}>
                {source.status}
              </Badge>
            </div>

            <div className="flex flex-wrap gap-2">
              {(source.fields || []).map((field, index) => (
                <Badge key={index} variant="secondary">
                  {field.name}: {field.type}
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                onSync(source.id);
              }}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(source.id);
              }}
            >
              <Settings className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="text-red-600 hover:text-red-700"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(source.id);
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {source.error && (
          <div className="mt-2 p-2 bg-red-50 text-red-700 rounded-md text-sm">
            {source.error.message}
          </div>
        )}

        <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Last Sync</p>
            <p className="font-medium">
              {source.lastSync
                ? new Date(source.lastSync).toLocaleString()
                : "Never"}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Next Sync</p>
            <p className="font-medium">
              {source.nextSync
                ? new Date(source.nextSync).toLocaleString()
                : "Not scheduled"}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Records</p>
            <p className="font-medium">
              {source.stats?.rowCount?.toLocaleString() ?? "Unknown"}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Size</p>
            <p className="font-medium">
              {source.stats?.size ? formatBytes(source.stats.size) : "Unknown"}
            </p>
          </div>
        </div>
      </Card>
    ))}
  </div>
);

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};
