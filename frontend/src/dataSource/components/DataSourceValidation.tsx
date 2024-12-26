// src/dataSource/components/validation/DataSourceValidation.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import { Alert } from "@/common/components/ui/alert";
import type { ValidationResult } from "../types/base";

interface DataSourceValidationProps {
  validation: ValidationResult;
  className?: string;
}

export const DataSourceValidation: React.FC<DataSourceValidationProps> = ({
  validation,
  className = "",
}) => {
  return (
    <Card className={className}>
      <div className="p-4">
        <h3 className="text-lg font-medium mb-4">Validation Results</h3>
        <div className="space-y-4">
          {validation.issues.map((issue, index) => (
            <Alert
              key={index}
              variant={issue.severity === "error" ? "destructive" : "warning"}
            >
              <div className="flex flex-col">
                <span className="font-medium">
                  {issue.field ? `${issue.field}: ` : ""}
                  {issue.type}
                </span>
                <span className="text-sm">{issue.message}</span>
              </div>
            </Alert>
          ))}
          {validation.issues.length === 0 && (
            <Alert variant="success">
              All validation checks passed successfully.
            </Alert>
          )}
        </div>
      </div>
    </Card>
  );
};
