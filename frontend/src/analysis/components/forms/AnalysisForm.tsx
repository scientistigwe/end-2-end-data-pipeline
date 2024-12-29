// src/analysis/components/forms/AnalysisForm.tsx
import React from "react";
import { useForm, UseFormReturn, FieldValues } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "@/common/components/ui/card";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import { Switch } from "@/common/components/ui/switch";
import { FormField, FormItem, FormLabel } from "@/common/components/ui/form";
import { dateUtils } from "@/common";
import type { QualityConfig, InsightConfig } from "../../types/analysis";

// Custom Form component with proper typing
interface CustomFormProps<T extends FieldValues> {
  form: UseFormReturn<T>;
  onSubmit: (values: T) => void;
  children: React.ReactNode;
  className?: string;
}

function CustomForm<T extends FieldValues>({
  form,
  onSubmit,
  children,
  className,
}: CustomFormProps<T>) {
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className={className}>
      {children}
    </form>
  );
}

// Type definitions
interface QualityFormConfig extends QualityConfig {
  pipelineId: string;
  rules: {
    dataTypes: boolean;
    nullChecks: boolean;
    rangeValidation: boolean;
  };
  thresholds: {
    errorThreshold: number;
    warningThreshold: number;
  };
}

interface InsightFormConfig extends InsightConfig {
  pipelineId: string;
  analysisTypes: {
    patterns: boolean;
    correlations: boolean;
    anomalies: boolean;
    trends: boolean;
  };
  dataScope: {
    timeRange: {
      start: string;
      end: string;
    };
  };
}

type AnalysisFormConfig = QualityFormConfig | InsightFormConfig;

const qualityFormSchema = z.object({
  pipelineId: z.string().min(1, "Pipeline ID is required"),
  rules: z.object({
    dataTypes: z.boolean(),
    nullChecks: z.boolean(),
    rangeValidation: z.boolean(),
  }),
  thresholds: z.object({
    errorThreshold: z.number().min(0).max(100),
    warningThreshold: z.number().min(0).max(100),
  }),
});

const insightFormSchema = z.object({
  pipelineId: z.string().min(1, "Pipeline ID is required"),
  analysisTypes: z.object({
    patterns: z.boolean(),
    correlations: z.boolean(),
    anomalies: z.boolean(),
    trends: z.boolean(),
  }),
  dataScope: z.object({
    timeRange: z.object({
      start: z.string(),
      end: z.string(),
    }),
  }),
});

// Props types
interface AnalysisFormProps {
  type: "quality" | "insight";
  onSubmit: (config: AnalysisFormConfig) => void;
  isLoading?: boolean;
}

interface RuleToggleProps {
  form: UseFormReturn<AnalysisFormConfig>;
  name: string;
  label: string;
}

interface ThresholdInputProps {
  form: UseFormReturn<AnalysisFormConfig>;
  name: string;
  label: string;
}

// Main Component
export const AnalysisForm: React.FC<AnalysisFormProps> = ({
  type,
  onSubmit,
  isLoading,
}) => {
  const form = useForm<AnalysisFormConfig>({
    resolver: zodResolver(
      type === "quality" ? qualityFormSchema : insightFormSchema
    ),
    defaultValues:
      type === "quality"
        ? {
            rules: {
              dataTypes: false,
              nullChecks: false,
              rangeValidation: false,
            },
            thresholds: {
              errorThreshold: 10,
              warningThreshold: 20,
            },
          }
        : {
            analysisTypes: {
              patterns: false,
              correlations: false,
              anomalies: false,
              trends: false,
            },
            dataScope: {
              timeRange: {
                start: dateUtils.formatDate(new Date(), { includeTime: true }),
                end: dateUtils.formatDate(
                  dateUtils.addTime(new Date(), { days: 7 }),
                  { includeTime: true }
                ),
              },
            },
          },
  });

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <h2 className="text-2xl font-bold">
          {type === "quality" ? "Quality Analysis" : "Insight Analysis"}
        </h2>
      </CardHeader>

      <CustomForm<AnalysisFormConfig> form={form} onSubmit={onSubmit}>
        <CardContent className="space-y-4">
          <FormField
            control={form.control}
            name="pipelineId"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Pipeline ID</FormLabel>
                <Input {...field} placeholder="Enter Pipeline ID" />
              </FormItem>
            )}
          />

          {type === "quality" ? (
            <>
              <div className="space-y-2">
                <h3 className="text-sm font-medium">Analysis Rules</h3>
                <div className="space-y-2">
                  <RuleToggle
                    form={form}
                    name="rules.dataTypes"
                    label="Data Types Validation"
                  />
                  <RuleToggle
                    form={form}
                    name="rules.nullChecks"
                    label="Null Checks"
                  />
                  <RuleToggle
                    form={form}
                    name="rules.rangeValidation"
                    label="Range Validation"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <ThresholdInput
                  form={form}
                  name="thresholds.errorThreshold"
                  label="Error Threshold"
                />
                <ThresholdInput
                  form={form}
                  name="thresholds.warningThreshold"
                  label="Warning Threshold"
                />
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <h3 className="text-sm font-medium">Analysis Types</h3>
                <div className="space-y-2">
                  <RuleToggle
                    form={form}
                    name="analysisTypes.patterns"
                    label="Pattern Detection"
                  />
                  <RuleToggle
                    form={form}
                    name="analysisTypes.correlations"
                    label="Correlation Analysis"
                  />
                  <RuleToggle
                    form={form}
                    name="analysisTypes.anomalies"
                    label="Anomaly Detection"
                  />
                  <RuleToggle
                    form={form}
                    name="analysisTypes.trends"
                    label="Trend Analysis"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium">Time Range</h3>
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="dataScope.timeRange.start"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Start Date</FormLabel>
                        <Input type="datetime-local" {...field} />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="dataScope.timeRange.end"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>End Date</FormLabel>
                        <Input type="datetime-local" {...field} />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            </>
          )}
        </CardContent>
        <CardFooter>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Starting Analysis..." : "Start Analysis"}
          </Button>
        </CardFooter>
      </CustomForm>
    </Card>
  );
};

// Helper Components
const RuleToggle: React.FC<RuleToggleProps> = ({ form, name, label }) => (
  <FormField
    control={form.control}
    name={name}
    render={({ field }) => (
      <FormItem className="flex items-center space-x-2">
        <Switch checked={field.value} onCheckedChange={field.onChange} />
        <FormLabel className="!mt-0">{label}</FormLabel>
      </FormItem>
    )}
  />
);

const ThresholdInput: React.FC<ThresholdInputProps> = ({
  form,
  name,
  label,
}) => (
  <FormField
    control={form.control}
    name={name}
    render={({ field }) => (
      <FormItem>
        <FormLabel>{label}</FormLabel>
        <Input
          type="number"
          min="0"
          max="100"
          {...field}
          onChange={(e) => field.onChange(Number(e.target.value))}
        />
      </FormItem>
    )}
  />
);
