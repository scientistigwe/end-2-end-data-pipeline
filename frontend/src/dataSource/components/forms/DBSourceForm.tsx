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
import { useDBSource } from "../../hooks/useDBSource";
import type { DBSourceConfig } from "../../types/dataSources";
import { v4 as uuidv4 } from "uuid";

interface DBSourceFormData {
  config: DBSourceConfig["config"];
}

interface DBSourceFormProps {
  onSubmit: (config: DBSourceConfig) => Promise<void>;
  onCancel: () => void;
}

export const DBSourceForm: React.FC<DBSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const [error, setError] = React.useState<Error | null>(null);
  const { isConnecting } = useDBSource();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DBSourceFormData>();

  const protocolError = errors.config?.protocol;

  const handleFormSubmit = useCallback(
    async (data: DBSourceFormData) => {
      try {
        setError(null);
        const dbSourceConfig: DBSourceConfig = {
          id: uuidv4(),
          name: "New DB Source",
          type: "database",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status: "active",
          config: data.config,
        };
        await onSubmit(dbSourceConfig);
        reset();
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error("Database connection failed")
        );
      }
    },
    [onSubmit, reset]
  );

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">Database Configuration</h3>
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
              <label className="text-sm font-medium">Database Type</label>
              <select
                {...register("config.type", {
                  required: "Database type is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
              >
                <option value="">Select database type...</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="mongodb">MongoDB</option>
                <option value="oracle">Oracle</option>
              </select>
              {protocolError && (
                <p className="text-sm text-red-500">
                  {protocolError.message as string}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Database Type</label>
              <select
                {...register("config.type", {
                  required: "Database type is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
              >
                <option value="">Select database type...</option>
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="mongodb">MongoDB</option>
                <option value="oracle">Oracle</option>
              </select>
              {protocolError?.message && (
                <p className="text-sm text-red-500">{protocolError.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Host</label>
              <input
                {...register("config.host", { required: "Host is required" })}
                className="block w-full rounded border-gray-300 shadow-sm"
                placeholder="localhost or database.example.com"
              />
              {errors.config?.host && (
                <p className="text-sm text-red-500">
                  {String(errors.config.host.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Port</label>
              <input
                type="number"
                {...register("config.port", {
                  required: "Port is required",
                  valueAsNumber: true,
                  validate: (value) =>
                    value >= 1 && value <= 65535
                      ? true
                      : "Port must be between 1 and 65535",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
                placeholder="5432"
              />
              {errors.config?.port && (
                <p className="text-sm text-red-500">
                  {String(errors.config.port.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Database Name</label>
              <input
                {...register("config.database", {
                  required: "Database name is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
                placeholder="Enter database name"
              />
              {errors.config?.database && (
                <p className="text-sm text-red-500">
                  {String(errors.config.database.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Username</label>
              <input
                {...register("config.username", {
                  required: "Username is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
                placeholder="Enter username"
              />
              {errors.config?.username && (
                <p className="text-sm text-red-500">
                  {String(errors.config.username.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <input
                type="password"
                {...register("config.password", {
                  required: "Password is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
                placeholder="Enter password"
              />
              {errors.config?.password && (
                <p className="text-sm text-red-500">
                  {String(errors.config.password.message)}
                </p>
              )}
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex justify-end space-x-4">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isConnecting}>
            {isConnecting ? "Connecting..." : "Connect Database"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
