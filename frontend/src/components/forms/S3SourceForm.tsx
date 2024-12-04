// src/components/forms/S3SourceForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import { useS3Source } from "../../hooks/dataSource/useS3Source";

interface S3FormData {
  accessKeyId: string;
  secretAccessKey: string;
  region: string;
  bucket: string;
  prefix?: string;
  endpoint?: string;
  useCustomEndpoint: boolean;
}

export const S3SourceForm: React.FC = () => {
  const { connect, isConnecting } = useS3Source();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<S3FormData>({
    defaultValues: {
      region: "us-east-1",
      useCustomEndpoint: false,
    },
  });

  const useCustomEndpoint = watch("useCustomEndpoint");

  const onSubmit = (data: S3FormData) => {
    const config = {
      ...data,
      endpoint: data.useCustomEndpoint ? data.endpoint : undefined,
    };
    connect(config);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Access Key ID
          </label>
          <input
            type="text"
            {...register("accessKeyId", {
              required: "Access Key ID is required",
            })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.accessKeyId && (
            <p className="mt-1 text-sm text-red-600">
              {errors.accessKeyId.message}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Secret Access Key
          </label>
          <input
            type="password"
            {...register("secretAccessKey", {
              required: "Secret Access Key is required",
            })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.secretAccessKey && (
            <p className="mt-1 text-sm text-red-600">
              {errors.secretAccessKey.message}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Region
          </label>
          <select
            {...register("region", { required: "Region is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          >
            <option value="us-east-1">US East (N. Virginia)</option>
            <option value="us-east-2">US East (Ohio)</option>
            <option value="us-west-1">US West (N. California)</option>
            <option value="us-west-2">US West (Oregon)</option>
            <option value="eu-west-1">EU (Ireland)</option>
            <option value="eu-central-1">EU (Frankfurt)</option>
            <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
          </select>
          {errors.region && (
            <p className="mt-1 text-sm text-red-600">{errors.region.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Bucket Name
          </label>
          <input
            type="text"
            {...register("bucket", { required: "Bucket name is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.bucket && (
            <p className="mt-1 text-sm text-red-600">{errors.bucket.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Prefix (Optional)
        </label>
        <input
          type="text"
          {...register("prefix")}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          placeholder="folder/subfolder/"
        />
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          {...register("useCustomEndpoint")}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label className="ml-2 block text-sm text-gray-900">
          Use custom endpoint
        </label>
      </div>

      {useCustomEndpoint && (
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Custom Endpoint
          </label>
          <input
            type="text"
            {...register("endpoint", {
              required: useCustomEndpoint
                ? "Endpoint is required when using custom endpoint"
                : false,
            })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            placeholder="https://s3.custom-domain.com"
          />
          {errors.endpoint && (
            <p className="mt-1 text-sm text-red-600">
              {errors.endpoint.message}
            </p>
          )}
        </div>
      )}

      <button
        type="submit"
        disabled={isConnecting}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
      >
        {isConnecting ? "Connecting..." : "Connect to S3"}
      </button>
    </form>
  );
};
