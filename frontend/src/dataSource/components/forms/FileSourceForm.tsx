// src/dataSource/components/FileSourceForm/FileSourceForm.tsx
import React, { useCallback, useMemo } from "react";
import { useForm } from "react-hook-form";
import { v4 as uuidv4 } from "uuid";
import { Upload } from "lucide-react";
import axios from "axios";
import { RouteHelper } from "../../../common/api/routes";
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
import { useFileSource } from "../../hooks/useFileSource";
import { DataSourceType } from "../../types/base";
import type {
  FileSourceConfig,
  FileUploadFormData,
  FileSourceFormProps,
} from "../../types/fileSource";
import { FILE_SOURCE_CONSTANTS } from "../../constants";
import { DATASOURCE_MESSAGES } from "../../constants";

export const FileSourceForm: React.FC<FileSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const { uploadProgress, isUploading } = useFileSource();
  const [error, setError] = React.useState<Error | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FileUploadFormData>({
    defaultValues: {
      config: FILE_SOURCE_CONSTANTS.config,
    },
  });

  const selectedFiles = watch("files");

  const handleFormSubmit = useCallback(
    async (data: FileUploadFormData) => {
      try {
        setError(null);
        const file = data.files[0];

        if (!file) {
          throw new Error(DATASOURCE_MESSAGES.ERRORS.VALIDATION_FAILED);
        }

        // File size validation
        if (file.size > FILE_SOURCE_CONSTANTS.maxFileSize) {
          throw new Error(
            `File size exceeds maximum limit of ${
              FILE_SOURCE_CONSTANTS.maxFileSize / (1024 * 1024)
            }MB`
          );
        }

        // File type validation
        const fileExtension = file.name.split(".").pop()?.toLowerCase();
        const supportedExtensions = Object.values(
          FILE_SOURCE_CONSTANTS.supportedFormats
        ).flat();

        if (
          !fileExtension ||
          !supportedExtensions.includes(`.${fileExtension}`)
        ) {
          throw new Error("Unsupported file format.");
        }

        const fileSourceConfig: FileSourceConfig = {
          id: uuidv4(),
          name: file.name,
          type: DataSourceType.FILE,
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
            parseOptions: data.config.parseOptions,
          },
        };

        const uploadUrl = RouteHelper.getNestedRoute(
          "DATA_SOURCES",
          "FILE",
          "UPLOAD",
          { file_id: fileSourceConfig.id }
        );

        await onSubmit(fileSourceConfig);
        reset();
      } catch (err) {
        console.error("Error during file upload:", err);

        if (axios.isAxiosError(err)) {
          const errorMessage = err.response?.data?.description || err.message;
          setError(
            new Error(
              `${DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED}: ${errorMessage}`
            )
          );
        } else {
          setError(
            err instanceof Error
              ? err
              : new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED)
          );
        }
      }
    },
    [onSubmit, reset]
  );

  const renderFilePreview = useMemo(() => {
    if (!selectedFiles?.length) return null;

    const file = selectedFiles[0];
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium">Selected File:</p>
        <p className="text-sm text-gray-600">{file.name}</p>
        <p className="text-sm text-gray-500">Size: {fileSizeMB} MB</p>
      </div>
    );
  }, [selectedFiles]);

  const supportedFormatsText = useMemo(() => {
    return Object.values(FILE_SOURCE_CONSTANTS.supportedFormats)
      .flat()
      .map((format) => format.toUpperCase().slice(1))
      .join(", ");
  }, []);

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
            <div className="border-2 border-dashed rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
              <input
                type="file"
                {...register("files", { required: "Please select a file" })}
                className="hidden"
                id="file-upload"
                accept={Object.values(FILE_SOURCE_CONSTANTS.supportedFormats)
                  .flat()
                  .join(",")}
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
                  Supported formats: {supportedFormatsText}
                </span>
              </label>
            </div>

            {errors.files && (
              <p className="text-sm text-red-600">{errors.files.message}</p>
            )}

            {renderFilePreview}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  File Type
                </label>
                <select
                  {...register("config.type")}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="csv">CSV</option>
                  <option value="json">JSON</option>
                  <option value="parquet">Parquet</option>
                  <option value="excel">Excel</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Delimiter
                </label>
                <input
                  type="text"
                  {...register("config.delimiter", {
                    required: "Delimiter is required",
                  })}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
                {errors.config?.delimiter && (
                  <p className="text-sm text-red-600">
                    {errors.config.delimiter.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Encoding
                </label>
                <input
                  type="text"
                  {...register("config.encoding")}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Skip Rows
                </label>
                <input
                  type="number"
                  {...register("config.skipRows")}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  min="0"
                />
              </div>
            </div>
          </div>

          {uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Upload Progress</span>
                <span>{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} />
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-end space-x-4">
          <Button
            variant="outline"
            onClick={onCancel}
            type="button"
            disabled={isSubmitting || isUploading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || isUploading}>
            {isUploading ? "Uploading..." : "Upload File"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};

export default FileSourceForm;
