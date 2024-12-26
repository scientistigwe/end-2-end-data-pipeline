import React, { useCallback } from "react";
import { useForm } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../../common/components/ui/card";
import { Button } from "../../../common/components/ui/button";
import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "../../../common/components/ui/alert";
import { Progress } from "../../../common/components/ui/progress";
import { Upload } from "lucide-react";
import { useFileSource } from "../../hooks/useFileSource";
import type { FileSourceConfig } from "../../types/base";
import { v4 as uuidv4 } from "uuid";

interface FileSourceFormData {
  files: FileList;
  config: FileSourceConfig["config"];
}

interface FileSourceFormProps {
  onSubmit: (config: FileSourceConfig) => Promise<void>;
  onCancel: () => void;
}

export const FileSourceForm: React.FC<FileSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const { uploadProgress, isUploading } = useFileSource();
  const [error, setError] = React.useState<Error | null>(null);

  const { register, handleSubmit, watch, reset } =
    useForm<FileSourceFormData>();

  const selectedFiles = watch("files");

  const handleFormSubmit = useCallback(
    async (data: FileSourceFormData) => {
      try {
        setError(null);
        const file = data.files[0];
        const fileSourceConfig: Omit<FileSourceConfig, "id"> = {
          name: file.name,
          type: "file",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status: "active",
          config: {
            type: data.config.type,
            delimiter: data.config.delimiter,
            encoding: data.config.encoding,
            hasHeader: Boolean(data.config.hasHeader),
            sheet: data.config.sheet,
            skipRows: Number(data.config.skipRows) || 0,
          },
        };
        await onSubmit({ ...fileSourceConfig, id: uuidv4() });
        reset();
      } catch (err) {
        setError(err instanceof Error ? err : new Error("File upload failed"));
      }
    },
    [onSubmit, reset]
  );

  const renderFilePreview = useCallback(() => {
    if (!selectedFiles?.length) return null;

    const file = selectedFiles[0];
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium">Selected File:</p>
        <p className="text-sm text-gray-600">{file.name}</p>
        <p className="text-sm text-gray-500">
          Size: {(file.size / 1024 / 1024).toFixed(2)} MB
        </p>
      </div>
    );
  }, [selectedFiles]);

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">File Upload Configuration</h3>
      </CardHeader>

      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Upload Error</AlertTitle>
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            {/* File Input */}
            <div className="border-2 border-dashed rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
              <input
                type="file"
                {...register("files", { required: "Please select a file" })}
                className="hidden"
                id="file-upload"
                accept=".csv,.json,.parquet,.xlsx,.xls"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center"
              >
                <Upload className="h-12 w-12 text-gray-400" />
                <span className="mt-2 text-sm text-gray-500">
                  Click to upload or drag and drop
                </span>
                <span className="mt-1 text-xs text-gray-400">
                  Supported formats: CSV, JSON, Parquet, Excel
                </span>
              </label>
            </div>

            {renderFilePreview()}

            {/* Upload Progress */}
            {uploadProgress > 0 && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Upload Progress</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} />
              </div>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex justify-end space-x-4">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload File"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
