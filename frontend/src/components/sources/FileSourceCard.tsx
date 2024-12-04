// src/components/sources/FileSourceCard.tsx
import React from "react";
import { useFileSource } from "../../hooks/dataSource/useFileSource";

interface FileSourceCardProps {
  fileId: string;
  metadata: any;
}

export const FileSourceCard: React.FC<FileSourceCardProps> = ({
  fileId,
  metadata,
}) => {
  const { uploadProgress, refreshMetadata } = useFileSource();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{metadata.filename}</h3>
        <span className="px-2 py-1 rounded-full text-sm bg-blue-100 text-blue-800">
          File Source
        </span>
      </div>

      <div className="mt-4">
        <div className="text-sm text-gray-600">
          <p>Size: {metadata.file_size_mb.toFixed(2)} MB</p>
          <p>Type: {metadata.file_type}</p>
          {metadata.row_count && (
            <p>Rows: {metadata.row_count.toLocaleString()}</p>
          )}
        </div>

        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
