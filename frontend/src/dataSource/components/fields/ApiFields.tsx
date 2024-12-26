// src/components/datasource/types/ApiSourceFields.tsx
import React from "react";
import { UseFormRegister, FieldErrors } from "react-hook-form";
import { Input } from "@/common/components//ui/inputs/input";
import { Select } from "@/common/components/ui/inputs/select";
import { Textarea } from "@/common/components/ui/textarea";
import type { ApiSourceConfig } from "../../types/base";

interface ApiSourceFieldsProps {
  register: UseFormRegister<ApiSourceConfig>;
  errors: FieldErrors<ApiSourceConfig>;
}

export const ApiSourceFields: React.FC<ApiSourceFieldsProps> = ({
  register,
  errors,
}) => {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">URL</label>
        <Input
          {...register("config.url", { required: "URL is required" })}
          placeholder="Enter API endpoint URL"
        />
        {errors.config?.url && (
          <p className="text-sm text-red-500">{errors.config.url.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Method</label>
          <Select
            {...register("config.method", { required: "Method is required" })}
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Authentication Type</label>
          <Select {...register("config.auth.type")}>
            <option value="">None</option>
            <option value="basic">Basic Auth</option>
            <option value="bearer">Bearer Token</option>
            <option value="oauth2">OAuth 2.0</option>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Headers</label>
        <Textarea
          {...register("config.headers")}
          placeholder="Enter headers as JSON"
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Request Body</label>
        <Textarea
          {...register("config.body")}
          placeholder="Enter request body as JSON"
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Rate Limit (req/min)</label>
          <Input
            type="number"
            {...register("config.rateLimit.requests")}
            placeholder="Requests per minute"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Timeout (ms)</label>
          <Input
            type="number"
            {...register("config.rateLimit.period")}
            placeholder="Timeout in milliseconds"
          />
        </div>
      </div>
    </div>
  );
};
