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
import type { FileSourceConfig } from "@/dataSource/types";

interface FileMetadata {
  filename: string;
  size: number;
  rowCount?: number;
  lastModified: string;
}

interface FileSourceCardProps {
  source: FileSourceConfig;
  metadata: FileMetadata;
  uploadProgress?: number;
  className?: string;
}

export const FileSourceCard: React.FC<FileSourceCardProps> = ({
  source,
  metadata,
  uploadProgress,
  className = "",
}) => {
  const renderMetadataItem = (
    label: string,
    value: string | number | undefined
  ) => {
    if (value === undefined) return null;

    return (
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}:</span>
        <span>{value}</span>
      </div>
    );
  };

  const renderUploadProgress = () => {
    if (uploadProgress === undefined || uploadProgress >= 100) return null;

    return (
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>Upload Progress</span>
          <span>{uploadProgress}%</span>
        </div>
        <Progress value={uploadProgress} />
      </div>
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="flex items-center space-x-2">
          <FileIcon className="h-5 w-5" />
          <div>
            <Badge variant="outline">{source.config.type}</Badge>
            <h3 className="text-lg font-medium mt-2">{metadata.filename}</h3>
          </div>
        </div>
        {uploadProgress === 100 && (
          <CheckCircle2 className="h-5 w-5 text-green-500" />
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            {renderMetadataItem("Size", formatBytes(metadata.size))}
            {renderMetadataItem("Rows", metadata.rowCount?.toLocaleString())}
            {renderMetadataItem(
              "Last Modified",
              new Date(metadata.lastModified).toLocaleString()
            )}
            {source.config.hasHeader && renderMetadataItem("Has Header", "Yes")}
            {source.config.delimiter &&
              renderMetadataItem("Delimiter", source.config.delimiter)}
          </div>

          {renderUploadProgress()}
        </div>
      </CardContent>
    </Card>
  );
};
