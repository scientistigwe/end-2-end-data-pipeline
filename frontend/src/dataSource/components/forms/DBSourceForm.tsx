// src/components/forms/DatabaseSourceForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import { useDBSource } from "../../dataSource/hooks/useDBSource";

interface DatabaseFormData {
  type: "postgresql" | "mysql" | "oracle" | "mongodb";
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
}

export const DBSourceForm: React.FC = () => {
  const { connect, isConnecting } = useDBSource();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DatabaseFormData>();

  const onSubmit = (data: DatabaseFormData) => {
    connect(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Database Type
        </label>
        <select
          {...register("type", { required: "Database type is required" })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="mongodb">MongoDB</option>
          <option value="oracle">Oracle</option>
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
            {...register("port", { required: "Port is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.port && (
            <p className="mt-1 text-sm text-red-600">{errors.port.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Database Name
        </label>
        <input
          type="text"
          {...register("database", { required: "Database name is required" })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
        {errors.database && (
          <p className="mt-1 text-sm text-red-600">{errors.database.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Username
          </label>
          <input
            type="text"
            {...register("username", { required: "Username is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.username && (
            <p className="mt-1 text-sm text-red-600">
              {errors.username.message}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            type="password"
            {...register("password", { required: "Password is required" })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">
              {errors.password.message}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          {...register("ssl")}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label className="ml-2 block text-sm text-gray-900">
          Use SSL connection
        </label>
      </div>

      <button
        type="submit"
        disabled={isConnecting}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
      >
        {isConnecting ? "Connecting..." : "Connect Database"}
      </button>
    </form>
  );
};
