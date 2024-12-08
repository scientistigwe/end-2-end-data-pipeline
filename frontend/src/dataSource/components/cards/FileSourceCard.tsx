// src/components/sources/FileSourceCard.tsx
import React from "react";
import { Card } from "../../../../components/ui/card";
import { Badge } from "../../../../components/ui/badge";
import { Progress } from "../../../../components/ui/progress";

interface FileMetadata {
  filename: string;
  file_size_mb: number;
  file_type: string;
  row_count?: number;
  last_modified: string;
}

interface FileSourceCardProps {
  fileId: string;
  metadata: FileMetadata;
  uploadProgress?: number;
}

export const FileSourceCard: React.FC<FileSourceCardProps> = ({
  metadata,
  uploadProgress = 0,
}) => {
  return (
    <Card className="p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{metadata.filename}</h3>
        <Badge variant="secondary">File Source</Badge>
      </div>

      <div className="mt-4">
        <div className="text-sm text-gray-600 space-y-1">
          <p>Size: {metadata.file_size_mb.toFixed(2)} MB</p>
          <p>Type: {metadata.file_type}</p>
          {metadata.row_count && (
            <p>Rows: {metadata.row_count.toLocaleString()}</p>
          )}
          <p>
            Last Modified: {new Date(metadata.last_modified).toLocaleString()}
          </p>
        </div>

        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-4">
            <Progress value={uploadProgress} className="w-full" />
            <p className="text-sm text-gray-500 mt-1">
              Uploading: {uploadProgress}%
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
