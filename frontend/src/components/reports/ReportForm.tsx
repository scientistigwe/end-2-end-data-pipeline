// src/components/reports/ReportForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type {
  ReportConfig,
  ReportType,
  ReportFormat,
} from "../../types/report";

interface ReportFormProps {
  onSubmit: (config: ReportConfig) => void;
  isLoading?: boolean;
}

export const ReportForm: React.FC<ReportFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const { register, handleSubmit, watch } = useForm<ReportConfig>();

  const reportTypes: ReportType[] = [
    "quality",
    "insight",
    "performance",
    "summary",
  ];
  const reportFormats: ReportFormat[] = ["pdf", "csv", "json"];

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <h2 className="text-2xl font-bold">Generate Report</h2>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Report Name</label>
            <Input
              {...register("name", { required: true })}
              placeholder="Enter report name"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Report Type</label>
            <Select {...register("type", { required: true })}>
              {reportTypes.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Format</label>
            <Select {...register("format", { required: true })}>
              {reportFormats.map((format) => (
                <option key={format} value={format}>
                  {format.toUpperCase()}
                </option>
              ))}
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Start Date</label>
              <Input type="datetime-local" {...register("timeRange.start")} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">End Date</label>
              <Input type="datetime-local" {...register("timeRange.end")} />
            </div>
          </div>
        </CardContent>

        <CardFooter>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Generating..." : "Generate Report"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
