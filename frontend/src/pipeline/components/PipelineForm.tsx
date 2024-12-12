// src/pipeline/components/PipelineForm.tsx
import React, { useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/common/components/ui/card";
import { Input } from "@/common/components/ui/inputs/input";
import { Button } from "@/common/components/ui/button";
import { Select } from "@/common/components/ui/inputs/select";
import { Plus, Trash2 } from "lucide-react";
import type { PipelineConfig } from "../types/pipeline";
import { PIPELINE_CONSTANTS } from "../constants";
import { validatePipelineConfig } from "../api/validation";

interface PipelineFormProps {
  initialData?: PipelineConfig;
  onSubmit: (data: PipelineConfig) => void;
  onCancel: () => void;
  onChange?: (isDirty: boolean) => void;
  isLoading?: boolean;
  error?: string | null;
}

// Type for the form errors
type FormErrors = z.inferFormattedError<typeof validatePipelineConfig>;

export const PipelineForm: React.FC<PipelineFormProps> = ({
  initialData,
  onSubmit,
  onCancel,
  onChange,
  isLoading = false,
  error = null,
}) => {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<PipelineConfig>({
    resolver: zodResolver(validatePipelineConfig),
    defaultValues: initialData || {
      name: "",
      mode: "development",
      steps: [],
      sourceId: "",
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "steps",
  });

  useEffect(() => {
    onChange?.(isDirty);
  }, [isDirty, onChange]);

  const getErrorMessage = (error: any) => {
    if (typeof error === 'string') return error;
    if (error?.message) return error.message;
    return '';
  };

  return (
    <Card>
      <CardHeader>
        <h2 className="text-2xl font-bold">
          {initialData ? "Edit Pipeline" : "Create Pipeline"}
        </h2>
        {error && (
          <p className="text-sm text-red-500 mt-2">{error}</p>
        )}
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              {...register("name")}
              placeholder="Enter pipeline name"
              className={errors.name ? "border-red-500" : ""}
            />
            {errors.name && (
              <p className="text-sm text-red-500">{getErrorMessage(errors.name)}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Input
              {...register("description")}
              placeholder="Enter pipeline description"
            />
            {errors.description && (
              <p className="text-sm text-red-500">{getErrorMessage(errors.description)}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Mode</label>
            <Select {...register("mode")}>
              {Object.entries(PIPELINE_CONSTANTS.MODES).map(([key, value]) => (
                <option key={key} value={value}>
                  {key.charAt(0) + key.slice(1).toLowerCase()}
                </option>
              ))}
            </Select>
            {errors.mode && (
              <p className="text-sm text-red-500">{getErrorMessage(errors.mode)}</p>
            )}
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Steps</label>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  append({
                    id: crypto.randomUUID(),
                    name: "",
                    type: "",
                    status: "idle",
                    config: {},
                    enabled: true,
                  })
                }
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Step
              </Button>
            </div>

            <div className="space-y-4">
              {fields.map((step, index) => (
                <Card key={step.id} className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-4 flex-1 mr-4">
                      <div>
                        <Input
                          {...register(`steps.${index}.name`)}
                          placeholder="Step name"
                          className={errors.steps?.[index]?.name ? "border-red-500" : ""}
                        />
                        {errors.steps?.[index]?.name && (
                          <p className="text-sm text-red-500 mt-1">
                            {getErrorMessage(errors.steps[index]?.name)}
                          </p>
                        )}
                      </div>
                      <div>
                        <Select 
                          {...register(`steps.${index}.type`)}
                          className={errors.steps?.[index]?.type ? "border-red-500" : ""}
                        >
                          <option value="">Select type</option>
                          {Object.entries(PIPELINE_CONSTANTS.STEPS.TYPES).map(
                            ([key, value]) => (
                              <option key={key} value={value}>
                                {key.charAt(0) + key.slice(1).toLowerCase()}
                              </option>
                            )
                          )}
                        </Select>
                        {errors.steps?.[index]?.type && (
                          <p className="text-sm text-red-500 mt-1">
                            {getErrorMessage(errors.steps[index]?.type)}
                          </p>
                        )}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex justify-between">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading
              ? "Saving..."
              : initialData
              ? "Update Pipeline"
              : "Create Pipeline"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};