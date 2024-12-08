// src/components/datasource/types/S3SourceFields.tsx
import React from "react";
import { UseFormRegister, FieldErrors } from "react-hook-form";
import { Input } from "../../../../../components/ui/input";
import { Switch } from "../../../../../components/ui/switch";
import type { S3SourceConfig } from "../../types/dataSources";

interface S3SourceFieldsProps {
  register: UseFormRegister<S3SourceConfig>;
  errors: FieldErrors<S3SourceConfig>;
}

export const S3SourceFields: React.FC<S3SourceFieldsProps> = ({ register }) => {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Bucket</label>
          <Input
            {...register("config.bucket", { required: "Bucket is required" })}
            placeholder="Enter S3 bucket name"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Region</label>
          <Input
            {...register("config.region", { required: "Region is required" })}
            placeholder="Enter AWS region"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Access Key ID</label>
          <Input
            {...register("config.accessKeyId", {
              required: "Access Key ID is required",
            })}
            placeholder="Enter AWS Access Key ID"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Secret Access Key</label>
          <Input
            type="password"
            {...register("config.secretAccessKey", {
              required: "Secret Access Key is required",
            })}
            placeholder="Enter AWS Secret Access Key"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Prefix</label>
        <Input
          {...register("config.prefix")}
          placeholder="Enter object prefix (optional)"
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Endpoint URL</label>
        <Input
          {...register("config.endpoint")}
          placeholder="Enter custom endpoint URL (optional)"
        />
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Switch {...register("config.sslEnabled")} />
          <label className="text-sm">Enable SSL</label>
        </div>

        <div className="flex items-center space-x-2">
          <Switch {...register("config.forcePathStyle")} />
          <label className="text-sm">Force Path Style</label>
        </div>
      </div>
    </div>
  );
};
