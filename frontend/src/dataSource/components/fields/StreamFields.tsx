// src/components/datasource/types/StreamSourceFields.tsx
import React from "react";
import { UseFormRegister, FieldErrors } from "react-hook-form";
import { Input } from "../../../../../components/ui/input";
import { Select } from "../../../../../components/ui/select";
import { Switch } from "../../../../../components/ui/switch";
import type { StreamSourceConfig } from "../../types/dataSources";

interface StreamSourceFieldsProps {
  register: UseFormRegister<StreamSourceConfig>;
  errors: FieldErrors<StreamSourceConfig>;
}

export const StreamSourceFields: React.FC<StreamSourceFieldsProps> = ({
  register,
}) => {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Protocol</label>
        <Select
          {...register("config.protocol", { required: "Protocol is required" })}
        >
          <option value="kafka">Kafka</option>
          <option value="rabbitmq">RabbitMQ</option>
          <option value="mqtt">MQTT</option>
          <option value="redis">Redis</option>
        </Select>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Hosts</label>
        <Input
          {...register("config.connection.hosts")}
          placeholder="Enter hosts (comma-separated)"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Username</label>
          <Input
            {...register("config.auth.username")}
            placeholder="Enter username"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Password</label>
          <Input
            type="password"
            {...register("config.auth.password")}
            placeholder="Enter password"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Topics/Queues</label>
        <Input
          {...register("config.topics")}
          placeholder="Enter topics/queues (comma-separated)"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Group ID</label>
          <Input
            {...register("config.consumer.groupId")}
            placeholder="Enter consumer group ID"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Max Batch Size</label>
          <Input
            type="number"
            {...register("config.consumer.maxBatchSize")}
            placeholder="Enter max batch size"
          />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <Switch {...register("config.auth.ssl")} />
          <label className="text-sm">Enable SSL</label>
        </div>

        <div className="flex items-center space-x-2">
          <Switch {...register("config.consumer.autoCommit")} />
          <label className="text-sm">Auto Commit</label>
        </div>
      </div>
    </div>
  );
};
