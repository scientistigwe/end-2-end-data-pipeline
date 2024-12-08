// src/components/pipeline/PipelineForm.tsx
import React from "react";
import { useForm, useFieldArray } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Select } from "../../components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import type { PipelineConfig } from "../types/pipeline";

interface PipelineFormProps {
  pipeline?: PipelineConfig;
  onSubmit: (data: PipelineConfig) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const PipelineForm: React.FC<PipelineFormProps> = ({
  pipeline,
  onSubmit,
  onCancel,
  isLoading,
}) => {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<PipelineConfig>({
    defaultValues: pipeline || {
      mode: "development",
      steps: [],
      triggers: [],
    },
  });

  const {
    fields: steps,
    append: appendStep,
    remove: removeStep,
  } = useFieldArray({
    control,
    name: "steps",
  });

  return (
    <Card>
      <CardHeader>
        <h2 className="text-2xl font-bold">
          {pipeline ? "Edit Pipeline" : "Create Pipeline"}
        </h2>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input
              {...register("name", { required: "Name is required" })}
              placeholder="Enter pipeline name"
            />
            {errors.name && (
              <p className="text-sm text-red-500">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Input
              {...register("description")}
              placeholder="Enter pipeline description"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Mode</label>
            <Select {...register("mode", { required: "Mode is required" })}>
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </Select>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">Steps</label>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  appendStep({
                    id: crypto.randomUUID(),
                    name: "",
                    type: "",
                    config: {},
                    enabled: true,
                  })
                }
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Step
              </Button>
            </div>

            <div className="space-y-4">
              {steps.map((step, index) => (
                <Card key={step.id} className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-4 flex-1 mr-4">
                      <Input
                        {...register(`steps.${index}.name`)}
                        placeholder="Step name"
                      />
                      <Select {...register(`steps.${index}.type`)}>
                        <option value="transform">Transform</option>
                        <option value="validate">Validate</option>
                        <option value="export">Export</option>
                      </Select>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeStep(index)}
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
            {isLoading ? "Saving..." : "Save Pipeline"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
