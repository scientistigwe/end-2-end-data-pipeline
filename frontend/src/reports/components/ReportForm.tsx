// src/report/components/ReportForm.tsx
import React from "react";
import { useForm, Controller } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/common/components/ui/card";
import { Input } from "@/common/components/ui/inputs/input";
import { Button } from "@/common/components/ui/button";
import { Select } from "@/common/components/ui/inputs/select";
import { DateTimePicker } from "@/common/components/ui/dateTimePicker";
import { REPORT_CONSTANTS } from "../constants";
import type { ReportConfig } from "../types/models";

interface ReportFormProps {
  onSubmit: (data: ReportConfig) => void;
  initialData?: Partial<ReportConfig>;
  isLoading?: boolean;
}

export const ReportForm: React.FC<ReportFormProps> = ({
  onSubmit,
  initialData,
  isLoading,
}) => {
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ReportConfig>({
    defaultValues: {
      type: "quality",
      format: "pdf",
      ...initialData,
    },
  });

  const handleFormSubmit = (data: ReportConfig) => {
    // Basic validation
    if (!data.name?.trim()) {
      return;
    }

    if (!data.timeRange?.start || !data.timeRange?.end) {
      return;
    }

    if (data.timeRange.start > data.timeRange.end) {
      return;
    }

    onSubmit(data);
  };

  return (
    <Card>
      <CardHeader>
        <h2 className="text-2xl font-bold">Generate Report</h2>
      </CardHeader>

      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Report Name</label>
            <Controller
              name="name"
              control={control}
              rules={{ required: "Report name is required" }}
              render={({ field }) => (
                <Input
                  {...field}
                  placeholder="Enter report name"
                  error={errors.name?.message}
                />
              )}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Report Type</label>
            <Controller
              name="type"
              control={control}
              rules={{ required: "Report type is required" }}
              render={({ field }) => (
                <Select {...field}>
                  {Object.entries(REPORT_CONSTANTS.TYPES).map(
                    ([key, value]) => (
                      <option key={value} value={value}>
                        {key.charAt(0) + key.slice(1).toLowerCase()}
                      </option>
                    )
                  )}
                </Select>
              )}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Start Date</label>
              <Controller
                name="timeRange.start"
                control={control}
                rules={{ required: "Start date is required" }}
                render={({ field }) => (
                  <DateTimePicker
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.timeRange?.start?.message}
                    id="start-date"
                    name={field.name}
                  />
                )}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">End Date</label>
              <Controller
                name="timeRange.end"
                control={control}
                rules={{
                  required: "End date is required",
                  validate: (value, formValues) =>
                    !formValues.timeRange?.start ||
                    formValues.timeRange.start <= value ||
                    "End date must be after start date",
                }}
                render={({ field }) => (
                  <DateTimePicker
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.timeRange?.end?.message}
                    id="end-date"
                    name={field.name}
                  />
                )}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Format</label>
            <Controller
              name="format"
              control={control}
              rules={{ required: "Format is required" }}
              render={({ field }) => (
                <Select {...field}>
                  {Object.entries(REPORT_CONSTANTS.FORMATS).map(
                    ([key, value]) => (
                      <option key={value} value={value}>
                        {key.charAt(0) + key.slice(1).toLowerCase()}
                      </option>
                    )
                  )}
                </Select>
              )}
            />
          </div>
        </CardContent>

        <CardFooter className="flex justify-end space-x-2">
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Generating..." : "Generate Report"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
