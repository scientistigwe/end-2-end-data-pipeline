import React, { useCallback, useMemo, useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { Upload } from "lucide-react";
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
import { dataSourceApi } from "@/dataSource/api";
import type {
  FileSourceConfig,
  FileUploadFormData,
  FileSourceFormProps,
} from "../../types/fileSource";
import { FILE_SOURCE_CONSTANTS } from "../../constants";
import { DATASOURCE_MESSAGES } from "../../constants";

import Papa from "papaparse";
import * as chardet from "chardet";

export const FileSourceForm: React.FC<FileSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const { uploadProgress, isUploading } = useFileSource();
  const [error, setError] = React.useState<Error | null>(null);
  const [uploadedMetadata, setUploadedMetadata] =
    useState<Partial<FileSourceConfig> | null>(null);
  const [autoDetectedMetadata, setAutoDetectedMetadata] =
    useState<Partial<FileSourceConfig> | null>(null);

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

  // Automatically detect file metadata when a file is selected
  useEffect(() => {
    const detectFileMetadata = async (file: File) => {
      try {
        // Detect file encoding using chardet
        const fileBuffer = await file.arrayBuffer();
        const encoding = await new Promise<string>((resolve) => {
          const result = chardet.detect(new Uint8Array(fileBuffer));
          resolve(result || "utf-8");
        });

        const fileExtension = file.name.split(".").pop()?.toLowerCase() || "";

        // This mapping matches exactly what the backend expects
        const fileTypeMap: Record<string, string> = {
          csv: "csv",
          json: "json",
          xlsx: "excel",
          xls: "excel",
          parquet: "parquet",
          txt: "csv", // Default txt files to CSV format
        };

        // Use the extension to determine file type or default to csv
        const fileType = fileTypeMap[fileExtension] || "csv";

        let autoMetadata: Partial<FileSourceConfig> = {
          // Default values for all file types
          type: fileType,
          encoding: encoding,
          skipRows: 0,
          hasHeader: true,
          parseOptions: {
            dateFormat: "YYYY-MM-DD",
            nullValues: ["", "null", "NA", "N/A"],
          },
        };

        // Add type-specific metadata
        switch (fileType) {
          case "csv":
            // Sample the file to detect delimiter and headers
            const text = new TextDecoder(encoding).decode(
              fileBuffer.slice(0, 4096)
            );
            const parseResult = Papa.parse(text, {
              preview: 5,
              skipEmptyLines: true,
            });

            // Detection logic for delimiter
            const delimiters = [",", "\t", ";", "|"];
            let detectedDelimiter = ","; // Default

            for (const delimiter of delimiters) {
              if (text.includes(delimiter)) {
                // Check if using this delimiter creates multiple columns
                const testParse = Papa.parse(text, {
                  delimiter,
                  preview: 3,
                  skipEmptyLines: true,
                });

                // If we have rows with multiple columns, this is likely the right delimiter
                if (testParse.data.some((row) => row.length > 1)) {
                  detectedDelimiter = delimiter;
                  break;
                }
              }
            }

            // Check if first row looks like a header
            const hasHeader =
              parseResult.data.length > 0 &&
              parseResult.data[0].some(
                (cell) =>
                  typeof cell === "string" &&
                  isNaN(Number(cell)) &&
                  cell.trim().length > 0
              );

            autoMetadata = {
              ...autoMetadata,
              type: "csv",
              delimiter: detectedDelimiter,
              hasHeader: hasHeader,
            };
            break;

          case "excel":
            autoMetadata = {
              ...autoMetadata,
              type: "excel",
              sheet: "Sheet1",
            };
            break;

          case "json":
          case "parquet":
            // No additional metadata needed beyond the defaults
            break;
        }

        console.log("Detected Metadata:", {
          fileType,
          encoding,
          ...autoMetadata,
        });

        setAutoDetectedMetadata(autoMetadata);
      } catch (err) {
        console.error("Metadata detection error:", err);
      }
    };

    if (selectedFiles?.[0]) {
      detectFileMetadata(selectedFiles[0]);
    }
  }, [selectedFiles]);

  const handleFormSubmit = useCallback(
    async (data: FileUploadFormData) => {
      try {
        setError(null);
        const file = data.files[0];

        if (!file) {
          throw new Error(DATASOURCE_MESSAGES.ERRORS.VALIDATION_FAILED);
        }

        const fileExtension = file.name.split(".").pop()?.toLowerCase() || "";

        // Create a mapping that matches the backend's expected values
        const fileTypeMap: Record<string, string> = {
          csv: "csv",
          json: "json",
          xlsx: "excel",
          xls: "excel",
          parquet: "parquet",
          txt: "csv", // Default txt files to CSV format
        };

        // Use the detected file type or determine it from extension
        const fileType =
          autoDetectedMetadata?.type || fileTypeMap[fileExtension] || "csv";

        // Prepare metadata in a format that matches backend expectations
        const metadata = {
          file_type: fileType,
          encoding: autoDetectedMetadata?.encoding || "utf-8",
          skip_rows: Number(autoDetectedMetadata?.skipRows) || 0,
          tags: ["data"],
          parse_options: {
            date_format:
              autoDetectedMetadata?.parseOptions?.dateFormat || "YYYY-MM-DD",
            null_values: autoDetectedMetadata?.parseOptions?.nullValues || [
              "",
              "null",
              "NA",
              "N/A",
            ],
          },
        };

        // Add file-type specific fields
        if (fileType === "excel") {
          Object.assign(metadata, {
            sheet_name: autoDetectedMetadata?.sheet || "Sheet1",
            has_header: autoDetectedMetadata?.hasHeader ?? true,
          });
        }

        if (fileType === "csv") {
          Object.assign(metadata, {
            delimiter: autoDetectedMetadata?.delimiter || ",",
            has_header: autoDetectedMetadata?.hasHeader ?? true,
          });
        }

        console.log("File Extension:", fileExtension);
        console.log("File Type:", fileType);
        console.log("Prepared Metadata:", metadata);

        const result = await dataSourceApi.uploadFile(
          file,
          metadata,
          (progress) => {
            console.log("Upload progress:", progress);
          }
        );

        setUploadedMetadata(metadata);
        onSubmit(result.data);
        reset();
      } catch (err) {
        console.error("Error during file upload:", err);
        setError(
          err instanceof Error
            ? err
            : new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED)
        );
      }
    },
    [onSubmit, reset, autoDetectedMetadata]
  );

  // Memoized supported formats text
  const supportedFormatsText = useMemo(() => {
    return Object.values(FILE_SOURCE_CONSTANTS.supportedFormats)
      .flat()
      .map((format) => format.toUpperCase().slice(1))
      .join(", ");
  }, []);

  // Memoized file preview
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

          {/* Pre-Upload Metadata Detection Preview */}
          {autoDetectedMetadata && !uploadedMetadata && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <h4 className="text-sm font-semibold mb-2">Detected Metadata</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <p>File Type: {autoDetectedMetadata.type}</p>
                {autoDetectedMetadata.delimiter && (
                  <p>
                    Delimiter:{" "}
                    {autoDetectedMetadata.delimiter === "\t"
                      ? "Tab"
                      : autoDetectedMetadata.delimiter}
                  </p>
                )}
                <p>Encoding: {autoDetectedMetadata.encoding}</p>
                <p>
                  Has Header: {autoDetectedMetadata.hasHeader ? "Yes" : "No"}
                </p>
                {autoDetectedMetadata.sheet && (
                  <p>Sheet: {autoDetectedMetadata.sheet}</p>
                )}
              </div>
            </div>
          )}

          {/* Post-Upload Metadata Display */}
          {uploadedMetadata && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg">
              <h4 className="text-sm font-semibold mb-2">Uploaded Metadata</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <p>File Type: {uploadedMetadata.file_type}</p>
                {uploadedMetadata.delimiter && (
                  <p>
                    Delimiter:{" "}
                    {uploadedMetadata.delimiter === "\t"
                      ? "Tab"
                      : uploadedMetadata.delimiter}
                  </p>
                )}
                <p>Encoding: {uploadedMetadata.encoding}</p>
                <p>Has Header: {uploadedMetadata.has_header ? "Yes" : "No"}</p>
                <p>Skip Rows: {uploadedMetadata.skip_rows}</p>
                {uploadedMetadata.parse_options && (
                  <>
                    <p>
                      Date Format: {uploadedMetadata.parse_options.date_format}
                    </p>
                    <p>
                      Null Values:{" "}
                      {uploadedMetadata.parse_options.null_values.join(", ")}
                    </p>
                  </>
                )}
              </div>
            </div>
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
