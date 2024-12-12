import React, { useCallback } from "react";
import { useForm } from "react-hook-form";
import { v4 as uuidv4 } from 'uuid';
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
import { useS3Source } from "../../hooks/useS3Source";
import type { S3SourceConfig } from "../../types/dataSources";

interface S3SourceFormData {
  config: S3SourceConfig["config"];
}

interface S3SourceFormProps {
  onSubmit: (config: S3SourceConfig) => Promise<void>;
  onCancel: () => void;
}

export const S3SourceForm: React.FC<S3SourceFormProps> = ({ onSubmit, onCancel }) => {
  const [error, setError] = React.useState<Error | null>(null);
  const { isConnecting } = useS3Source();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<S3SourceFormData>();

  const handleFormSubmit = useCallback(
    async (data: S3SourceFormData) => {
      try {
        setError(null);
        const s3SourceConfig: S3SourceConfig = {
          id: uuidv4(),
          name: 'New S3 Source',
          type: 's3',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(), 
          status: 'active',
          config: data.config,
        };
        await onSubmit(s3SourceConfig);
        reset();
      } catch (err) {
        setError(err instanceof Error ? err : new Error('S3 connection failed'));
      }
    },
    [onSubmit, reset],
  );
    

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">S3 Configuration</h3>
      </CardHeader>

      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Connection Error</AlertTitle>
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            {/* Form fields */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Bucket Name</label>
              <input
                {...register("config.bucket", {
                  required: "Bucket name is required",
                  pattern: {
                    value: /^[a-z0-9][a-z0-9.-]*[a-z0-9]$/,
                    message: "Invalid bucket name format",
                  },
                })}
                placeholder="my-bucket-name"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
              {errors.config?.bucket && (
                <p className="text-sm text-red-500">
                  {String(errors.config.bucket.message)}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Bucket Name</label>
              <input
                {...register("config.bucket", {
                  required: "Bucket name is required",
                  pattern: {
                    value: /^[a-z0-9][a-z0-9.-]*[a-z0-9]$/,
                    message: "Invalid bucket name format",
                  },
                })}
                placeholder="my-bucket-name"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
              {errors.config?.bucket && (
                <p className="text-sm text-red-500">
                  {String(errors.config.bucket.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Region</label>
              <select
                {...register("config.region", { required: "Region is required" })}
                className="block w-full rounded border-gray-300 shadow-sm"
              >
                <option value="">Select region...</option>
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="us-west-2">US West (Oregon)</option>
                <option value="eu-west-1">EU (Ireland)</option>
                <option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
              </select>
              {errors.config?.region && (
                <p className="text-sm text-red-500">
                  {String(errors.config.region.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Access Key ID</label>
              <input
                {...register("config.accessKeyId", {
                  required: "Access Key ID is required",
                })}
                placeholder="AKIAXXXXXXXXXXXXXXXX"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
              {errors.config?.accessKeyId && (
                <p className="text-sm text-red-500">
                  {String(errors.config.accessKeyId.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Secret Access Key</label>
              <input
                type="password"
                {...register("config.secretAccessKey", {
                  required: "Secret Access Key is required",
                })}
                placeholder="Enter your secret access key"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
              {errors.config?.secretAccessKey && (
                <p className="text-sm text-red-500">
                  {String(errors.config.secretAccessKey.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Prefix (Optional)</label>
              <input
                {...register("config.prefix")}
                placeholder="folder/subfolder/"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
            </div>
          </div>
          </CardContent>
        
        <CardFooter className="flex justify-end space-x-4">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isConnecting}>
            {isConnecting ? "Connecting..." : "Connect S3"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};