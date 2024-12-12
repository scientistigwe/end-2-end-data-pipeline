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
import { useStreamSource } from "../../hooks/useStreamSource";
import type { StreamSourceConfig } from "../../types/dataSources";

interface StreamSourceFormData {
  config: StreamSourceConfig["config"];
}

interface StreamSourceFormProps {
  onSubmit: (config: StreamSourceConfig) => Promise<void>;
  onCancel: () => void;
}

export const StreamSourceForm: React.FC<StreamSourceFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const [error, setError] = React.useState<Error | null>(null);
  const { isConnecting } = useStreamSource();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StreamSourceFormData>();

  const handleFormSubmit = useCallback(
    async (data: StreamSourceFormData) => {
      try {
        setError(null);
        const streamSourceConfig: StreamSourceConfig = {
          id: uuidv4(),
          name: 'New Stream Source',
          type: 'stream',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          status: 'active',
          config: data.config,
        };
        await onSubmit(streamSourceConfig);
        reset();
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Stream connection failed'));
      }
    },
    [onSubmit, reset],
  );

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">Stream Configuration</h3>
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
              <label className="text-sm font-medium">Protocol</label>
              <select
                {...register("config.protocol", {
                  required: "Protocol is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
              >
                <option value="">Select protocol...</option>
                <option value="kafka">Kafka</option>
                <option value="rabbitmq">RabbitMQ</option>
                <option value="mqtt">MQTT</option>
                <option value="redis">Redis</option>
              </select>
              {errors.config?.protocol && (
                <p className="text-sm text-red-500">
                  {String(errors.config.protocol.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Protocol</label>
              <select
                {...register("config.protocol", {
                  required: "Protocol is required",
                })}
                className="block w-full rounded border-gray-300 shadow-sm"
              >
                <option value="">Select protocol...</option>
                <option value="kafka">Kafka</option>
                <option value="rabbitmq">RabbitMQ</option>
                <option value="mqtt">MQTT</option>
                <option value="redis">Redis</option>
              </select>
              {errors.config?.protocol && (
                <p className="text-sm text-red-500">
                  {String(errors.config.protocol.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Hosts</label>
              <input
                {...register("config.connection.hosts.0", {
                  required: "At least one host is required",
                })}
                placeholder="localhost:9092"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
              {errors.config?.connection?.hosts && (
                <p className="text-sm text-red-500">
                  {String(errors.config.connection.hosts.message)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Username (Optional)</label>
              <input
                {...register("config.auth.username")}
                placeholder="Enter username"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Password (Optional)</label>
              <input
                type="password"
                {...register("config.auth.password")}
                placeholder="Enter password"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                Consumer Group ID (Optional)
              </label>
              <input
                {...register("config.consumer.groupId")}
                placeholder="my-consumer-group"
                className="block w-full rounded border-gray-300 shadow-sm"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Topics (Optional)</label>
              <input
                {...register("config.topics.0")}
                placeholder="my-topic"
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
            {isConnecting ? "Connecting..." : "Connect Stream"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
