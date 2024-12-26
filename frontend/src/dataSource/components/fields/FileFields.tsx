import { UseFormRegister, FieldErrors } from "react-hook-form";
import { Input } from "@/common/components//ui/inputs/input";
import { Select } from "@/common/components/ui/inputs/select";
import { Switch } from "@/common/components/ui/switch";
import type { FileSourceConfig } from "../../types/base";

interface FileSourceFieldsProps {
  register: UseFormRegister<FileSourceConfig>;
  errors: FieldErrors<FileSourceConfig>;
}

export const FileSourceFields = ({
  register,
  errors,
}: FileSourceFieldsProps) => {
  const getErrorMessage = (error: any) => {
    if (typeof error === "string") return error;
    return error?.message || "This field is required";
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">File Type</label>
        <Select {...register("config.type", { required: true })}>
          <option value="">Select type...</option>
          <option value="csv">CSV</option>
          <option value="json">JSON</option>
          <option value="parquet">Parquet</option>
          <option value="excel">Excel</option>
        </Select>
        {errors.config?.type && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.type)}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Delimiter</label>
        <Input
          {...register("config.delimiter")}
          placeholder="Enter delimiter (e.g., ',')"
          defaultValue=","
        />
        {errors.config?.delimiter && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.delimiter)}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Encoding</label>
        <Input
          {...register("config.encoding")}
          placeholder="Enter encoding"
          defaultValue="utf-8"
        />
        {errors.config?.encoding && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.encoding)}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Sheet Name</label>
        <Input
          {...register("config.sheet")}
          placeholder="For Excel files only"
        />
        {errors.config?.sheet && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.sheet)}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Skip Rows</label>
        <Input
          type="number"
          {...register("config.skipRows", {
            valueAsNumber: true,
            min: 0,
          })}
          placeholder="Number of rows to skip"
          defaultValue="0"
        />
        {errors.config?.skipRows && (
          <p className="text-sm text-red-500">
            {getErrorMessage(errors.config.skipRows)}
          </p>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <Switch {...register("config.hasHeader")} defaultChecked />
        <label className="text-sm">Has Header Row</label>
      </div>
    </div>
  );
};
