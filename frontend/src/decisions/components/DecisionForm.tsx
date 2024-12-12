// src/decisions/components/forms/DecisionForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import { Card } from "../../common/components/ui/card";
import { Input } from "../../common/components//ui/inputs/input";
import { Button } from "../../common/components/ui/button/Button";
import { Select } from "../../common/components/ui/inputs/select";
import { DECISION_TYPES, DECISION_URGENCIES } from "../constants";
import type { Decision } from "../types/decisions";
import { cn } from "../../common/utils/cn";

interface DecisionFormProps {
  onSubmit: (data: Partial<Decision>) => void;
  initialData?: Partial<Decision>;
  className?: string;
}

export const DecisionForm: React.FC<DecisionFormProps> = ({
  onSubmit,
  initialData = {},
  className = "",
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Partial<Decision>>({
    defaultValues: initialData,
  });

  return (
    <Card className={className}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Title</label>
          <Input
            {...register("title", { required: "Title is required" })}
            className={cn(errors.title && "border-red-500")}
            aria-invalid={errors.title ? "true" : "false"}
          />
          {errors.title && (
            <p className="text-sm text-red-500">{errors.title.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Type</label>
          <Select
            {...register("type", { required: "Type is required" })}
            className={cn(errors.type && "border-red-500")}
            aria-invalid={errors.type ? "true" : "false"}
          >
            {DECISION_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </Select>
          {errors.type && (
            <p className="text-sm text-red-500">{errors.type.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Urgency</label>
          <Select
            {...register("urgency", { required: "Urgency is required" })}
            className={cn(errors.urgency && "border-red-500")}
            aria-invalid={errors.urgency ? "true" : "false"}
          >
            {DECISION_URGENCIES.map((urgency) => (
              <option key={urgency} value={urgency}>
                {urgency.charAt(0).toUpperCase() + urgency.slice(1)}
              </option>
            ))}
          </Select>
          {errors.urgency && (
            <p className="text-sm text-red-500">{errors.urgency.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Description</label>
          <textarea
            {...register("description", {
              required: "Description is required",
            })}
            className={cn(
              "w-full min-h-[80px] rounded-md border bg-background px-3 py-2 text-sm ring-offset-background",
              errors.description && "border-red-500"
            )}
            rows={4}
            aria-invalid={errors.description ? "true" : "false"}
          />
          {errors.description && (
            <p className="text-sm text-red-500">{errors.description.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Deadline</label>
          <Input
            type="datetime-local"
            {...register("deadline")}
            className={cn(errors.deadline && "border-red-500")}
          />
          {errors.deadline && (
            <p className="text-sm text-red-500">{errors.deadline.message}</p>
          )}
        </div>

        <Button type="submit" className="w-full">
          Save Decision
        </Button>
      </form>
    </Card>
  );
};
