// src/components/forms/StreamSourceForm.tsx
import { useForm } from "react-hook-form";
import { useStreamSource } from "../../hooks/dataSource/useStreamSource";

interface StreamFormData {
  type: "kafka" | "rabbitmq";
  host: string;
  port: number;
  username?: string;
  password?: string;
  ssl: boolean;
  topic?: string;
  queue?: string;
  groupId?: string;
  options?: Record<string, any>;
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
      type: "kafka",
      ssl: false,
    },
  });

  const streamType = watch("type");

  const onSubmit = (data: StreamFormData) => {
    // Transform the form data to match StreamConfig
    const config = {
      type: data.type,
      connection: {
        host: data.host,
        port: data.port,
        username: data.username,
        password: data.password,
        ssl: data.ssl,
      },
      topic: data.topic,
      queue: data.queue,
      groupId: data.groupId,
      options: data.options,
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
          {...register("type", { required: "Stream type is required" })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="kafka">Apache Kafka</option>
          <option value="rabbitmq">RabbitMQ</option>
        </select>
        {errors.type && (
          <p className="mt-1 text-sm text-red-600">{errors.type.message}</p>
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
              Topic
            </label>
            <input
              type="text"
              {...register("topic", {
                required: "Topic is required for Kafka",
              })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            />
            {errors.topic && (
              <p className="mt-1 text-sm text-red-600">
                {errors.topic.message}
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
