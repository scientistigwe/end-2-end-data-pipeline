import { UseFormRegister, FieldErrors } from "react-hook-form";
import { Input } from "../../../../../components/ui/input";
import { Select } from "../../../../../components/ui/select";
import { Switch } from "../../../../../components/ui/switch";
import type { DBSourceConfig } from "../../types/dataSources";

interface DatabaseSourceFieldsProps {
  register: UseFormRegister<DBSourceConfig>;
  errors: FieldErrors<DBSourceConfig>;
}

export const DatabaseSourceFields = ({
  register,
  errors,
}: DatabaseSourceFieldsProps) => {
  const getErrorMessage = (error: any) => {
    if (typeof error === "string") return error;
    return error?.message || "This field is required";
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Database Type</label>
        <Select {...register("config.type", { required: true })}>
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="mongodb">MongoDB</option>
          <option value="oracle">Oracle</option>
        </Select>
        {errors.config?.type && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.type)}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Host</label>
          <Input
            {...register("config.host", { required: true })}
            placeholder="Enter host"
          />
          {errors.config?.host && (
            <p className="text-sm text-red-500">
              {getErrorMessage(errors.config.host)}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Port</label>
          <Input
            type="number"
            {...register("config.port", { required: true })}
            placeholder="Enter port"
          />
          {errors.config?.port && (
            <p className="text-sm text-red-500">
              {getErrorMessage(errors.config.port)}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Username</label>
          <Input
            {...register("config.username", { required: true })}
            placeholder="Enter username"
          />
          {errors.config?.username && (
            <p className="text-sm text-red-500">
              {getErrorMessage(errors.config.username)}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Password</label>
          <Input
            type="password"
            {...register("config.password", { required: true })}
            placeholder="Enter password"
          />
          {errors.config?.password && (
            <p className="text-sm text-red-500">
              {getErrorMessage(errors.config.password)}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Database Name</label>
        <Input
          {...register("config.database", { required: true })}
          placeholder="Enter database name"
        />
        {errors.config?.database && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.database)}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Schema</label>
        <Input
          {...register("config.schema")}
          placeholder="Enter schema (optional)"
        />
      </div>

      <div className="flex items-center space-x-2">
        <Switch {...register("config.ssl")} />
        <label className="text-sm">Enable SSL</label>
      </div>
    </div>
  );
};
