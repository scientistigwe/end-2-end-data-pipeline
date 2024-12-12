// src/monitoring/components/config/AlertConfigForm.tsx
import React from "react";
import { useForm } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../../common/components/ui/card";
import { Input } from "../../../common/components/ui/inputs/input";
import { Select } from "../../../common/components/ui/inputs/select";
import { Button } from "../../../common/components/ui/button";
import type { AlertConfig, AlertSeverity } from "../../types/monitoring";

interface AlertConfigFormProps {
  onSubmit: (config: AlertConfig) => void;
  initialData?: AlertConfig;
  className?: string;
}

export const AlertConfigForm: React.FC<AlertConfigFormProps> = ({
  onSubmit,
  initialData,
  className = "",
}) => {
  const { register, handleSubmit } = useForm<AlertConfig>({
    defaultValues: initialData,
  });

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">Configure Alert</h3>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Metric</label>
            <Input {...register("metric", { required: true })} />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Threshold</label>
            <Input
              type="number"
              {...register("threshold", { required: true })}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Severity</label>
            <Select {...register("severity", { required: true })}>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Condition</label>
            <Select {...register("condition", { required: true })}>
              <option value="above">Above</option>
              <option value="below">Below</option>
            </Select>
          </div>
        </CardContent>

        <CardFooter>
          <Button type="submit">Save Configuration</Button>
        </CardFooter>
      </form>
    </Card>
  );
};
