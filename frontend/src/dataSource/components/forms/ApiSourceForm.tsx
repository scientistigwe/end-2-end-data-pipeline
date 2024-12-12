import React from "react";
import { useForm, UseFormRegister, FieldErrors } from "react-hook-form";
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
import { Input } from "@/common/components//ui/inputs/input";
import { Select } from "@/common/components/ui/inputs/select";
import { useApiSource } from "../../hooks/useApiSource";
import type { ApiSourceConfig } from "../../types/dataSources";

interface ApiSourceFormData {
  config: {
    url: string;
    method: "GET" | "POST" | "PUT" | "DELETE";
    headers?: Record<string, string>;
    params?: Record<string, string>;
    body?: unknown;
    auth?: {
      type: "basic" | "bearer" | "oauth2";
      credentials: Record<string, string>;
    };
    rateLimit?: {
      requests: number;
      period: number;
    };
  };
}

interface ApiSourceFormProps {
  onSubmit: (config: ApiSourceConfig) => Promise<void>;
  onCancel: () => void;
}

const ApiSourceFields: React.FC<{
  register: UseFormRegister<ApiSourceFormData>;
  errors: FieldErrors<ApiSourceFormData>;
}> = ({ register, errors }) => (
  <div className="space-y-4">
    <div>
      <Input
        {...register("config.url", { required: "URL is required" })}
        placeholder="API URL"
      />
      {errors.config?.url && (
        <span className="text-sm text-red-500">
          {errors.config.url.message}
        </span>
      )}
    </div>

    <div>
      <Select
        {...register("config.method", { required: "Method is required" })}
      >
        <option value="">Select Method</option>
        <option value="GET">GET</option>
        <option value="POST">POST</option>
        <option value="PUT">PUT</option>
        <option value="DELETE">DELETE</option>
      </Select>
      {errors.config?.method && (
        <span className="text-sm text-red-500">
          {errors.config.method.message}
        </span>
      )}
    </div>

    {/* Optional headers */}
    <div>
      <Input
        {...register("config.headers.0", {
          required: "Header key is required",
        })}
        placeholder="Header Key"
      />
      <Input
        {...register("config.headers.1", {
          required: "Header value is required",
        })}
        placeholder="Header Value"
      />
      {errors.config?.headers && (
        <span className="text-sm text-red-500">
          {errors.config?.url?.message && (
            <span className="text-sm text-red-500">
              {errors.config.url.message}
            </span>
          )}
        </span>
      )}
    </div>

    {/* Optional params */}
    <div>
      <Input
        {...register("config.params.0", { required: "Param key is required" })}
        placeholder="Param Key"
      />
      <Input
        {...register("config.params.1", {
          required: "Param value is required",
        })}
        placeholder="Param Value"
      />
      {errors.config?.params && (
        <span className="text-sm text-red-500">
          {errors.config?.url?.message && (
            <span className="text-sm text-red-500">
              {errors.config.url.message}
            </span>
          )}
        </span>
      )}
    </div>

    {/* Optional authentication */}
    <div>
      <Select {...register("config.auth.type")}>
        <option value="">Select Auth Type</option>
        <option value="basic">Basic</option>
        <option value="bearer">Bearer</option>
        <option value="oauth2">OAuth2</option>
      </Select>
      <Input
        {...register("config.auth.credentials.username")}
        placeholder="Username"
      />
      <Input
        {...register("config.auth.credentials.password")}
        type="password"
        placeholder="Password"
      />
      {errors.config?.auth && (
        <span className="text-sm text-red-500">
          {errors.config.auth.message}
        </span>
      )}
    </div>

    {/* Optional rateLimit */}
    <div>
      <Input
        {...register("config.rateLimit.requests")}
        type="number"
        placeholder="Requests per period"
      />
      <Input
        {...register("config.rateLimit.period")}
        type="number"
        placeholder="Period in seconds"
      />
      {errors.config?.rateLimit && (
        <span className="text-sm text-red-500">
          {errors.config.rateLimit.message}
        </span>
      )}
    </div>
  </div>
);

export const ApiSourceForm: React.FC<ApiSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const { isConnecting } = useApiSource(); // Only keep `isConnecting` if relevant
  const [error, setError] = React.useState<Error | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ApiSourceFormData>();

  const handleFormSubmit = async (data: ApiSourceFormData) => {
    try {
      const apiSourceConfig: ApiSourceConfig = {
        type: "api",
        id: "unique-id",
        name: "API Source",
        createdAt: new Date().toISOString(), // Add createdAt with current timestamp
        updatedAt: new Date().toISOString(), // Add updatedAt with current timestamp
        status: "active", // Assuming status is a string, adjust as necessary
        config: {
          ...data.config,
        },
      };
      await onSubmit(apiSourceConfig); // Pass the config to the parent-provided `onSubmit`
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Submission failed"));
    }
  };

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">API Configuration</h3>
      </CardHeader>

      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}

          <ApiSourceFields register={register} errors={errors} />
        </CardContent>

        <CardFooter className="flex space-x-4">
          <Button type="submit" disabled={isConnecting} className="w-full">
            {isConnecting ? "Submitting..." : "Submit"}
          </Button>
          <Button
            type="button"
            onClick={onCancel}
            variant="secondary"
            className="w-full"
          >
            Cancel
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
