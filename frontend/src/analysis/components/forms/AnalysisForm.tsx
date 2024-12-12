// src/components/analysis/AnalysisForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../../../../components/ui/card";
import { Button } from "../../../../../components/ui/button";
import { Input } from "../../../../../components/ui/inputs/input";
import { Switch } from "../../../../../components/ui/switch";
import type { QualityConfig, InsightConfig } from "../../types/analysis";

type AnalysisFormConfig = QualityConfig | InsightConfig;

interface AnalysisFormProps {
  type: "quality" | "insight";
  onSubmit: (config: AnalysisFormConfig) => void;
  isLoading?: boolean;
}

export const AnalysisForm: React.FC<AnalysisFormProps> = ({
  type,
  onSubmit,
  isLoading,
}) => {
  const { register, handleSubmit } = useForm<AnalysisFormConfig>();

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <h2 className="text-2xl font-bold">
          {type === "quality" ? "Quality Analysis" : "Insight Analysis"}
        </h2>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {/* Common Fields */}
          <Input
            {...register("pipelineId")}
            placeholder="Pipeline ID"
            required
          />

          {type === "quality" ? (
            // Quality Analysis Fields
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium">Rules</label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Switch {...register("rules.dataTypes")} />
                    <span>Data Types Validation</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch {...register("rules.nullChecks")} />
                    <span>Null Checks</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch {...register("rules.rangeValidation")} />
                    <span>Range Validation</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Error Threshold</label>
                  <Input
                    type="number"
                    {...register("thresholds.errorThreshold")}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Warning Threshold
                  </label>
                  <Input
                    type="number"
                    {...register("thresholds.warningThreshold")}
                  />
                </div>
              </div>
            </>
          ) : (
            // Insight Analysis Fields
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium">Analysis Types</label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Switch {...register("analysisTypes.patterns")} />
                    <span>Pattern Detection</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch {...register("analysisTypes.correlations")} />
                    <span>Correlation Analysis</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch {...register("analysisTypes.anomalies")} />
                    <span>Anomaly Detection</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch {...register("analysisTypes.trends")} />
                    <span>Trend Analysis</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Time Range</label>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    type="datetime-local"
                    {...register("dataScope.timeRange.start")}
                  />
                  <Input
                    type="datetime-local"
                    {...register("dataScope.timeRange.end")}
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
      </form>
    </Card>
  );
};
