import React from "react";
import {
  Card,
  CardHeader,
  CardContent,
} from "../../../common/components/ui/card";
import { Badge } from "../../../common/components/ui/badge";
import { Progress } from "../../../common/components/ui/progress";
import { FileIcon, CheckCircle2 } from "lucide-react";
import { formatBytes } from "@/common/utils";
import type { BaseMetadata } from "@/dataSource/types/base";

interface FileMetadata {
  filename?: string;
  size?: number;
  rowCount?: number;
  lastModified?: string;
}

interface FileSourceCardProps {
  source: BaseMetadata;
  className?: string;
}

export const FileSourceCard: React.FC<FileSourceCardProps> = ({
  source,
  className = "",
}) => {
  // Safely extract metadata
  const metadata: FileMetadata = {
    filename: source.name || 'Unnamed File',
    size: source.config?.size || 0,
    lastModified: source.updatedAt || new Date().toISOString()
  };

  const renderMetadataItem = (
    label: string,
    value: string | number | undefined
  ) => {
    if (value === undefined || value === null) return null;

    return (
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}:</span>
        <span>{value}</span>
      </div>
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          <FileIcon className="h-5 w-5" />
          <div>
            <Badge variant="outline">{source.config?.type || 'Unknown'}</Badge>
            <h3 className="text-lg font-medium mt-2">{metadata.filename}</h3>
          </div>
        </div>
        {source.status === 'active' && (
          <CheckCircle2 className="h-5 w-5 text-green-500" />
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            {renderMetadataItem("Size", formatBytes(metadata.size))}
            {renderMetadataItem(
              "Last Modified",
              new Date(metadata.lastModified).toLocaleString()
            )}
            {source.config?.delimiter &&
              renderMetadataItem("Delimiter", source.config.delimiter)}
            {source.config?.encoding &&
              renderMetadataItem("Encoding", source.config.encoding)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};