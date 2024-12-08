// src/components/forms/StreamSourceForm.tsx
import { useForm } from "react-hook-form";
import { useStreamSource } from "../../dataSource/hooks/useStreamSource";

interface StreamFormData {
  protocol: "kafka" | "rabbitmq" | "mqtt" | "redis"; // Changed from 'type' to 'protocol'
  host: string;
  port: number;
  username?: string;
  password?: string;
  ssl: boolean;
  topics?: string[]; // Changed from single topic to array
  queue?: string;
  groupId?: string;
  options?: Record<string, unknown>;
}

export const StreamSourceForm: React.FC = () => {
  const { connect, isConnecting } = useStreamSource();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<StreamFormData>({
    defaultValues: {
      protocol: "kafka", // Changed from 'type' to 'protocol'
      ssl: false,
    },
  });

  const streamType = watch("protocol"); // Updated to match new field name

  const onSubmit = (data: StreamFormData) => {
    // Transform the form data to match expected StreamConfig
    const config = {
      protocol: data.protocol, // Changed from 'type' to 'protocol'
      connection: {
        hosts: [`${data.host}:${data.port}`], // Combine host and port into hosts array
        options: data.options,
      },
      auth: {
        username: data.username,
        password: data.password,
        ssl: data.ssl,
      },
      topics: data.topics || (data.topics ? [data.topics] : undefined), // Handle topics array
      consumer:
        streamType === "kafka"
          ? {
              groupId: data.groupId,
            }
          : undefined,
      queue: data.queue, // For RabbitMQ
    };

    connect(config);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Stream Type
        </label>
        <select
          {...register("protocol", { required: "Stream type is required" })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="kafka">Apache Kafka</option>
          <option value="rabbitmq">RabbitMQ</option>
          <option value="mqtt">MQTT</option>
          <option value="redis">Redis</option>
        </select>
        {errors.protocol && (
          <p className="mt-1 text-sm text-red-600">{errors.protocol.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Host
          </label>
          <input
            type="text"
            {...register("host", { required: "Host is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.host && (
            <p className="mt-1 text-sm text-red-600">{errors.host.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Port
          </label>
          <input
            type="number"
            {...register("port", {
              required: "Port is required",
              min: { value: 1, message: "Port must be greater than 0" },
              max: { value: 65535, message: "Port must be less than 65536" },
            })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.port && (
            <p className="mt-1 text-sm text-red-600">{errors.port.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Username (Optional)
          </label>
          <input
            type="text"
            {...register("username")}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Password (Optional)
          </label>
          <input
            type="password"
            {...register("password")}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
      </div>

      {streamType === "kafka" && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Topics (comma-separated)
            </label>
            <input
              type="text"
              {...register("topics", {
                required: "Topics are required for Kafka",
                setValueAs: (value: string) =>
                  value.split(",").map((t) => t.trim()),
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            />
            {errors.topics && (
              <p className="mt-1 text-sm text-red-600">
                {errors.topics.message}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Consumer Group ID
            </label>
            <input
              type="text"
              {...register("groupId", {
                required: "Group ID is required for Kafka",
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            />
            {errors.groupId && (
              <p className="mt-1 text-sm text-red-600">
                {errors.groupId.message}
              </p>
            )}
          </div>
        </>
      )}

      {streamType === "rabbitmq" && (
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Queue Name
          </label>
          <input
            type="text"
            {...register("queue", {
              required: "Queue name is required for RabbitMQ",
            })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.queue && (
            <p className="mt-1 text-sm text-red-600">{errors.queue.message}</p>
          )}
        </div>
      )}

      <div className="flex items-center">
        <input
          type="checkbox"
          {...register("ssl")}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label className="ml-2 block text-sm text-gray-900">
          Enable SSL/TLS
        </label>
      </div>

      <button
        type="submit"
        disabled={isConnecting}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
      >
        {isConnecting ? "Connecting..." : "Connect to Stream"}
      </button>
    </form>
  );
};
