import React from "react";
import type { S3SourceConfig } from "../../types/base";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Folder, File } from "lucide-react";
import { formatBytes } from "@/common";

interface S3PreviewProps {
  source: S3SourceConfig;
  objects: Array<{
    key: string;
    size: number;
    lastModified: string;
    isDirectory: boolean;
  }>;
  onNavigate: (key: string) => void;
  className?: string;
}

export const S3Preview: React.FC<S3PreviewProps> = ({
  source,
  objects,
  onNavigate,
  className = "",
}) => {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">S3 Browser</h3>
          <Badge variant="secondary">{source.config.bucket}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {objects.map((object) => (
            <div
              key={object.key}
              className="p-2 hover:bg-gray-50 rounded-md cursor-pointer flex items-center justify-between"
              onClick={() => onNavigate(object.key)}
            >
              <div className="flex items-center space-x-2">
                {object.isDirectory ? (
                  <Folder className="h-4 w-4 text-blue-500" />
                ) : (
                  <File className="h-4 w-4 text-gray-500" />
                )}
                <span>{object.key}</span>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>{formatBytes(object.size)}</span>
                <span>{new Date(object.lastModified).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
