// src/dataSource/components/DataSourceList.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
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
import { ValidationDisplay } from "./validation";
import { formatBytes } from "@/dataSource/utils";
import type {
  BaseMetadata,
  DataSourceStatus,
  DataSourceType,
} from "../types/base";

interface DataSourceListProps {
  sources: BaseMetadata[];
  onSelect: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  className?: string;
}

const STATUS_STYLES: Record<DataSourceStatus, string> = {
  active: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
  connecting: "bg-blue-100 text-blue-800",
  inactive: "bg-gray-100 text-gray-800",
  processing: "bg-purple-100 text-purple-800",
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

            {source.description && (
              <p className="text-sm text-gray-600">{source.description}</p>
            )}

            {source.tags && source.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {source.tags.map((tag, index) => (
                  <Badge key={index} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
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
          <div className="mt-2">
            <ValidationDisplay
              validation={{
                isValid: false,
                issues: [
                  {
                    severity: "error",
                    message: source.error.message,
                    type: source.error.code || "Error",
                    field: undefined,
                  },
                ],
                warnings: [],
              }}
              compact
            />
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
            <p className="text-gray-500">Type Details</p>
            <p className="font-medium capitalize">{source.type}</p>
          </div>
          <div>
            <p className="text-gray-500">Created</p>
            <p className="font-medium">
              {new Date(source.createdAt).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Updated</p>
            <p className="font-medium">
              {new Date(source.updatedAt).toLocaleString()}
            </p>
          </div>
        </div>
      </Card>
    ))}
  </div>
);
