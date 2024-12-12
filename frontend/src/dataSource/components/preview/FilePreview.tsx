import React from "react";
import type { FileSourceConfig, PreviewData } from "../../types/dataSources";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Progress } from "@/common/components/ui/progress";

interface FilePreviewProps {
  source: FileSourceConfig;
  previewData?: PreviewData & {
    processedRows: number;
  };
  className?: string;
}

export const FilePreview: React.FC<FilePreviewProps> = ({
  source,
  previewData,
  className = "",
}) => {
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return "Unknown size";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(2)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB`;
  };

  const renderValue = (value: unknown): string => {
    if (value === null || value === undefined) return "";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };

  const fileSize = source.metadata?.size as number | undefined;
  const fileName = source.metadata?.name as string | undefined;

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">File Preview</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>File: {fileName || "Unnamed file"}</span>
              <span>Size: {formatFileSize(fileSize)}</span>
            </div>
            {previewData && (
              <>
                <Progress
                  value={
                    (previewData.processedRows / previewData.totalRows) * 100
                  }
                />
                <div className="mt-4 overflow-auto">
                  {previewData.fields && (
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4 font-medium">
                      {previewData.fields.map((field, index) => (
                        <div key={`header-${index}-${field.name}`}>
                          {field.name}
                        </div>
                      ))}
                    </div>
                  )}
                  {previewData.data && (
                    <div className="mt-2 space-y-2">
                      {previewData.data.map((row, rowIdx) => (
                        <div
                          key={`row-${rowIdx}`}
                          className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4"
                        >
                          {Object.values(row).map((value, colIdx) => (
                            <div
                              key={`cell-${rowIdx}-${colIdx}`}
                              className="truncate"
                            >
                              {renderValue(value)}
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