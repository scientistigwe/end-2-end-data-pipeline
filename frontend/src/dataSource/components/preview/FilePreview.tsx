// src/components/dataSource/preview/FilePreview.tsx
import React from "react";
import type { FileSourceConfig } from "../../types/dataSources";
import { Card, CardHeader, CardContent } from "../../../components/ui/card";
import { Progress } from "../../../components/ui/progress";

interface FilePreviewProps {
  source: FileSourceConfig;
  previewData?: {
    headers?: string[];
    rows?: any[];
    totalRows: number;
    processedRows: number;
  };
  className?: string;
}

export const FilePreview: React.FC<FilePreviewProps> = ({
  source,
  previewData,
  className = "",
}) => {
  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">File Preview</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>File: {source.metadata.fileName}</span>
              <span>
                Size: {(source.metadata.fileSize / 1024).toFixed(2)} KB
              </span>
            </div>
            {previewData && (
              <>
                <Progress
                  value={
                    (previewData.processedRows / previewData.totalRows) * 100
                  }
                />
                <div className="mt-4 overflow-auto">
                  {previewData.headers && (
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4 font-medium">
                      {previewData.headers.map((header) => (
                        <div key={header}>{header}</div>
                      ))}
                    </div>
                  )}
                  {previewData.rows && (
                    <div className="mt-2 space-y-2">
                      {previewData.rows.map((row, idx) => (
                        <div
                          key={idx}
                          className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4"
                        >
                          {Object.values(row).map((value, i) => (
                            <div key={i} className="truncate">
                              {String(value)}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
